import time
import threading

import numpy as np
import pandas as pd


class CancelledError(Exception):
    pass


def _patch_synthpop():
    """Fix synthpop's DataProcessor to always use LabelEncoder (never OneHotEncoder).

    Bug: preprocess() / _preprocess() may switch to OHE for categorical columns
    with >=10 unique values, then KeyErrors in postprocess because original column
    names are gone.
    Fix: patch BOTH the public and private preprocess method names so the fix
    applies regardless of how synthpop's internal call chain is structured.
    Always use LabelEncoder, converting NaN to '__NA__' first.
    """
    try:
        from synthpop.processor.data_processor import DataProcessor
        from sklearn.preprocessing import LabelEncoder, StandardScaler

        def _fixed_preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
            data = data.copy()
            # Defensive initialisation — some synthpop versions set these in the
            # original preprocess() before calling _preprocess(); patching the
            # public method directly means __init__ may be the only prior call.
            if not hasattr(self, "original_columns") or self.original_columns is None:
                self.original_columns = list(data.columns)
            if not hasattr(self, "encoders") or self.encoders is None:
                self.encoders = {}
            if not hasattr(self, "scalers") or self.scalers is None:
                self.scalers = {}
            for col, dtype in self.metadata.items():
                if col not in data.columns:
                    continue
                if dtype == "categorical":
                    series = data[col].astype(object).fillna("__NA__").astype(str)
                    encoder = LabelEncoder()
                    data[col] = encoder.fit_transform(series)
                    self.encoders[col] = encoder
                elif dtype == "numerical":
                    scaler = StandardScaler(with_mean=False, with_std=False)
                    data[col] = scaler.fit_transform(data[[col]])
                    self.scalers[col] = scaler
                elif dtype == "boolean":
                    data[col] = data[col].astype(int)
                elif dtype == "datetime":
                    data[col] = data[col].apply(
                        lambda x: x.timestamp() if pd.notnull(x) else np.nan
                    )
                elif dtype == "timedelta":
                    data[col] = pd.to_timedelta(data[col]).dt.total_seconds()
            return data[list(self.original_columns)]

        def _fixed_postprocess(self, data: pd.DataFrame) -> pd.DataFrame:
            data = data.copy()
            for col, dtype in self.metadata.items():
                if col not in data.columns:
                    continue
                try:
                    if dtype == "categorical" and col in self.encoders:
                        clipped = (
                            data[col]
                            .round()
                            .clip(0, len(self.encoders[col].classes_) - 1)
                        )
                        # NaN cannot be cast to int; track null positions,
                        # fill with 0 for decode, then restore NaN afterwards.
                        null_mask = clipped.isna()
                        int_codes = clipped.fillna(0).astype(int)
                        decoded = pd.Series(
                            self.encoders[col].inverse_transform(int_codes),
                            index=data[col].index,
                            dtype=object,
                        )
                        decoded = decoded.replace("__NA__", np.nan)
                        decoded[null_mask] = np.nan
                        data[col] = decoded
                    elif dtype == "numerical" and col in self.scalers:
                        data[col] = self.scalers[col].inverse_transform(data[[col]])
                    elif dtype == "boolean":
                        data[col] = data[col].round().astype(bool)
                    elif dtype == "datetime":
                        data[col] = pd.to_datetime(data[col], unit="s", errors="coerce")
                    elif dtype == "timedelta":
                        data[col] = pd.to_timedelta(data[col], unit="s")
                except Exception:
                    pass
            out_cols = [c for c in self.original_columns if c in data.columns]
            return data[out_cols]

        # Patch both the public and private names — synthpop versions differ in
        # whether preprocess() delegates to _preprocess() or contains the logic itself.
        DataProcessor.preprocess = _fixed_preprocess
        DataProcessor._preprocess = _fixed_preprocess
        DataProcessor.postprocess = _fixed_postprocess
    except Exception:
        pass


_patch_synthpop()


def _sanitise_for_synthesis(df):
    """Drop all-NaN columns, constant columns, and replace inf with NaN.

    Returns (clean_df, list_of_dropped_column_names).
    """
    df = df.copy()
    numeric_cols = df.select_dtypes(include="number").columns
    df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan)
    all_nan = [c for c in df.columns if df[c].isna().all()]
    constant = [
        c for c in df.columns
        if c not in all_nan and df[c].dropna().nunique() <= 1
    ]
    drop = all_nan + constant
    if drop:
        df = df.drop(columns=drop)
    return df, drop


def _recover_cat_labels(synth_df: pd.DataFrame, orig_df: pd.DataFrame, variable_types: dict) -> pd.DataFrame:
    """Belt-and-suspenders: ensure categorical columns have the correct original labels.

    If synthpop's DataProcessor failed to inverse_transform (e.g. because the public
    preprocess() doesn't call _preprocess() so our patch was never applied), the
    synthetic column still holds numeric LabelEncoder codes.  This function detects
    that situation and remaps codes → original labels using the same alphabetical sort
    that LabelEncoder.fit() uses on the string-cast values.
    """
    synth_df = synth_df.copy()
    for col, vtype in (variable_types or {}).items():
        if vtype != "categorical" or col not in orig_df.columns or col not in synth_df.columns:
            continue

        # Reconstruct the label list in the same order LabelEncoder.fit() would use:
        # sort the string representations of the non-null unique values, then append
        # "__NA__" (also sorted in) if the column had any nulls.
        orig_non_null = orig_df[col].dropna()
        expected = sorted(orig_non_null.astype(str).unique())
        if orig_df[col].isna().any():
            expected = sorted(expected + ["__NA__"])

        if not expected:
            continue

        # Check whether the synthetic column already contains correct string labels.
        synth_vals = synth_df[col].dropna()
        synth_str_set = set(synth_vals.astype(str))
        if synth_str_set.issubset(set(expected)):
            # Labels are already correct; just convert any lingering __NA__ sentinel.
            if "__NA__" in synth_str_set:
                synth_df[col] = synth_df[col].replace("__NA__", np.nan)
            continue

        # The synthetic column appears to contain numeric codes — try to remap.
        codes = pd.to_numeric(synth_df[col], errors="coerce")
        if codes.isna().all():
            continue  # Cannot interpret as codes; leave unchanged.

        n = len(expected)
        null_mask = codes.isna()
        int_codes = codes.round().clip(0, n - 1).fillna(0).astype(int)
        decoded = pd.Series(
            [expected[c] for c in int_codes],
            index=synth_df.index,
            dtype=object,
        )
        decoded = decoded.replace("__NA__", np.nan)
        decoded[null_mask] = np.nan
        synth_df[col] = decoded

    return synth_df


def _apply_variable_types(metadata: dict, variable_types: dict) -> dict:
    """Override auto-detected DataProcessor metadata with user-specified types.

    Without this, integer-coded categoricals (dtype int64) are auto-detected
    as 'numerical' and go through StandardScaler instead of LabelEncoder,
    producing continuous float output whose labels never match the originals.
    """
    _map = {"categorical": "categorical", "numeric": "numerical"}
    for col, vtype in (variable_types or {}).items():
        if col in metadata and vtype in _map:
            metadata[col] = _map[vtype]
    return metadata


def run_synthesis(
    df, method, n_rows, method_kwargs, max_train_rows,
    skip_imputation, progress_callback, cancel_event=None,
    variable_types=None,
):
    """Run synthesis synchronously, calling progress_callback(pct, msg) at each step.

    Raises CancelledError if cancel_event is set between steps.
    Returns (synthetic_df, n_dupes).
    """
    from synthpop import MissingDataHandler, DataProcessor, CARTMethod, GaussianCopulaMethod

    def _cb(pct, msg):
        progress_callback(pct, msg)
        if cancel_event is not None and cancel_event.is_set():
            raise CancelledError()

    df, dropped = _sanitise_for_synthesis(df)
    if dropped:
        _cb(0, f"Note: {len(dropped)} column(s) excluded (all-missing or constant): "
               f"{', '.join(dropped)}")

    n_cols = len(df.columns)
    n_rows_full = len(df)
    handler = MissingDataHandler()

    if skip_imputation:
        _cb(5, "Step 1 of 5 — Missing data imputation skipped…")
        real_df = df
    else:
        _cb(5, "Step 1 of 5 — Detecting and imputing missing values…")
        real_df = handler.apply_imputation(df, handler.detect_missingness(df))

    if n_rows_full > max_train_rows:
        train_df = real_df.sample(
            n=max_train_rows, random_state=method_kwargs.get("random_state", 42)
        )
        _, sample_drops = _sanitise_for_synthesis(train_df)
        if sample_drops:
            _cb(10, f"Note: {len(sample_drops)} column(s) dropped — degenerate in "
                    f"training subsample: {', '.join(sample_drops)}")
            train_df = train_df.drop(columns=sample_drops)
            df = df.drop(columns=sample_drops, errors="ignore")
        n_cols = len(train_df.columns)
        _cb(
            15,
            f"Step 2 of 5 — Preprocessing {n_cols} variable(s) "
            f"(using {max_train_rows:,}-row training sample from {n_rows_full:,} total)…",
        )
    else:
        train_df = real_df
        _cb(15, f"Step 2 of 5 — Preprocessing {n_cols} variable(s)…")

    metadata = _apply_variable_types(handler.get_column_dtypes(train_df), variable_types)
    processor = DataProcessor(metadata)
    processed_data = processor.preprocess(train_df)

    # sklearn cannot handle NaN in features; fill with median/mode
    nan_mask = processed_data.isna().any()
    if nan_mask.any():
        processed_data = processed_data.copy()
        for col in processed_data.columns[nan_mask]:
            if pd.api.types.is_numeric_dtype(processed_data[col]):
                processed_data[col] = processed_data[col].fillna(
                    processed_data[col].median()
                )
            else:
                mode = processed_data[col].mode()
                processed_data[col] = processed_data[col].fillna(
                    mode.iloc[0] if len(mode) else 0
                )

    fit_msg = (
        f"Step 3 of 5 — Fitting {method} model on "
        f"{len(train_df):,} rows × {n_cols} columns"
    )
    _cb(30, fit_msg + "…")

    if method == "CART":
        model = CARTMethod(metadata, **method_kwargs)
    else:
        model = GaussianCopulaMethod(
            metadata,
            **{k: v for k, v in method_kwargs.items() if k != "random_state"},
        )

    def _watchdog(done_event, start_pct, base_msg):
        """Emit elapsed-time messages every 10s during blocking fit/sample."""
        t0 = time.monotonic()

        def _run():
            while not done_event.wait(timeout=10):
                elapsed = int(time.monotonic() - t0)
                m, s = divmod(elapsed, 60)
                elapsed_str = f"{m}m {s}s" if m else f"{s}s"
                try:
                    progress_callback(start_pct, f"{base_msg} — {elapsed_str} elapsed…")
                except Exception:
                    pass

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t

    fit_done = threading.Event()
    wt = _watchdog(fit_done, 30, fit_msg)
    try:
        model.fit(processed_data)
    finally:
        fit_done.set()
        wt.join(timeout=1)

    n_sample = int(n_rows * 1.2) + 10
    sample_msg = f"Step 4 of 5 — Sampling {n_sample:,} candidate rows"
    _cb(70, sample_msg + "…")

    sample_done = threading.Event()
    st = _watchdog(sample_done, 70, sample_msg)
    try:
        synthetic_processed = model.sample(n_sample)
    finally:
        sample_done.set()
        st.join(timeout=1)

    _cb(85, "Step 5 of 5 — Postprocessing, removing exact duplicates of real rows…")
    synthetic_df = processor.postprocess(synthetic_processed)

    # Guarantee correct string labels for categorical columns.  If synthpop's
    # DataProcessor.preprocess() didn't call our patched _preprocess() (e.g. because
    # it contains its own inline logic), the inverse_transform step was never applied
    # and the column still holds LabelEncoder integer codes.
    synthetic_df = _recover_cat_labels(synthetic_df, df, variable_types)

    common_cols = [c for c in df.columns if c in synthetic_df.columns]

    original_hashes = set(
        pd.util.hash_pandas_object(df[common_cols], index=False).values
    )
    dupe_mask = pd.util.hash_pandas_object(
        synthetic_df[common_cols], index=False
    ).isin(original_hashes)
    n_dupes = int(dupe_mask.sum())
    synthetic_df = synthetic_df[~dupe_mask].reset_index(drop=True).head(int(n_rows))

    return synthetic_df, n_dupes


# ── Time estimate (benchmark on small sample) ─────────────────────────────────

_BENCHMARK_N = 2_000


def _fmt_time(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s" if m else f"{s}s"


def estimate_time(df, method, max_train_rows, n_rows_out, method_kwargs, skip_imputation, variable_types=None):
    """Run a micro-benchmark on ≤2,000 rows and extrapolate synthesis time.

    Returns a dict with 'estimate' (human-readable string) and timing details.
    """
    from synthpop import MissingDataHandler, DataProcessor, CARTMethod, GaussianCopulaMethod

    df, _ = _sanitise_for_synthesis(df)
    n_source = len(df)
    bench_n = min(_BENCHMARK_N, n_source)
    bench_df = df.sample(n=bench_n, random_state=42) if n_source > bench_n else df.copy()

    handler = MissingDataHandler()
    if skip_imputation:
        real_df = bench_df
    else:
        real_df = handler.apply_imputation(bench_df, handler.detect_missingness(bench_df))

    metadata = _apply_variable_types(handler.get_column_dtypes(real_df), variable_types)
    processor = DataProcessor(metadata)
    processed = processor.preprocess(real_df)

    for col in processed.columns[processed.isna().any()]:
        if processed[col].dtype.kind in "iuf":
            processed[col] = processed[col].fillna(processed[col].median())
        else:
            m = processed[col].mode()
            processed[col] = processed[col].fillna(m.iloc[0] if len(m) else 0)

    if method == "CART":
        model = CARTMethod(metadata, **method_kwargs)
    else:
        model = GaussianCopulaMethod(
            metadata, **{k: v for k, v in method_kwargs.items() if k != "random_state"}
        )

    t0 = time.monotonic()
    model.fit(processed)
    t_fit = time.monotonic() - t0

    bench_sample_n = min(500, bench_n)
    t0 = time.monotonic()
    model.sample(bench_sample_n)
    t_sample = time.monotonic() - t0

    actual_train_n = min(max_train_rows, n_source)
    t_fit_est = t_fit * (actual_train_n / bench_n) ** 1.15
    t_sample_est = t_sample * (n_rows_out / bench_sample_n)
    t_total = (t_fit_est + t_sample_est) * 1.20
    if method == "CART" and method_kwargs.get("proper", False):
        t_total *= 1.9

    return {
        "estimate": _fmt_time(t_total),
        "fit_bench": _fmt_time(t_fit),
        "sample_bench": _fmt_time(t_sample),
        "bench_n": bench_n,
        "actual_train_n": actual_train_n,
        "n_rows_out": n_rows_out,
        "estimate_secs": max(1, int(t_total)),
    }
