import pandas as pd

EXTRA_NA_VALUES = [
    ".",
    *[f".{c}" for c in "abcdefghijklmnopqrstuvwxyz"],
    *[f".{c.upper()}" for c in "abcdefghijklmnopqrstuvwxyz"],
    "._",
    "missing", "Missing", "MISSING",
]

_SENTINEL_CODES = {
    -1, -2, -3, -6, -7, -8, -9,
    -66, -77, -88, -99,
    -666, -777, -888, -999,
    -6666, -7777, -8888, -9999,
    -66666, -77777, -88888, -99999,
}

_SENTINEL_FREQ_THRESHOLD = 0.05


def detect_numeric_sentinels(df, threshold=_SENTINEL_FREQ_THRESHOLD):
    """Return {col: [(value, freq, suggested), ...]} for negative-value sentinel candidates."""
    result = {}
    for col in df.columns:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(series) == 0:
            continue
        neg_vals = series[series < 0].unique()
        suspects = []
        for v in sorted(neg_vals):
            freq = (series == v).sum() / len(series)
            is_integer = v == int(v)
            is_sentinel = is_integer and int(v) in _SENTINEL_CODES
            suggested = bool(is_sentinel and freq <= threshold)
            suspects.append((int(v) if is_integer else v, float(freq), suggested))
        if suspects:
            result[col] = suspects
    return result


def default_variable_types(df):
    """Return (categorical_list, numeric_list) using cardinality heuristics."""
    categorical, numeric = [], []
    for c in df.columns:
        n = df[c].nunique(dropna=True)
        if df[c].dtype == "object":
            (categorical if n <= 50 else numeric).append(c)
        else:
            (categorical if n <= 20 else numeric).append(c)
    return categorical, numeric


def load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, na_values=EXTRA_NA_VALUES, keep_default_na=True)


def column_cardinality(df: pd.DataFrame) -> dict:
    return {col: int(df[col].nunique(dropna=True)) for col in df.columns}
