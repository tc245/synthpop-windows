"""
Quality report for synthetic data — ported from flask/services/synth_report.py.

build_synth_report: pure pandas/scipy/matplotlib, no Flask dependencies.
render_report_html: converts the report dict to HTML for QTextBrowser display.
"""
import base64
import io
import math


def _safe_float(v, ndigits=4):
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, ndigits)
    except (TypeError, ValueError):
        return None


def _norm_cat(val) -> str:
    """Normalise a categorical label to a consistent string.

    Synthesis methods often convert integer category codes to floats
    (0 → 0.0, 1 → 1.0).  Without normalisation those would appear as
    separate labels when compared with the original string-cast values,
    breaking both the frequency table and the chi-square test.
    """
    try:
        f = float(val)
        if not (math.isnan(f) or math.isinf(f)) and f == int(f):
            return str(int(f))
    except (TypeError, ValueError, OverflowError):
        pass
    return str(val)


def _norm_series(series):
    """Apply _norm_cat element-wise to a pandas Series."""
    return series.map(_norm_cat)


def build_synth_report(orig_df, synth_df, variable_types):
    """Compute numeric/categorical comparisons, KS tests, chi² tests, and correlation heatmap.

    variable_types may be {col: type_str} or {type_str: [col, ...]}.
    Returns a report dict.
    """
    from scipy import stats
    import pandas as pd

    shared_cols = set(orig_df.columns) & set(synth_df.columns)

    if variable_types and isinstance(next(iter(variable_types.values())), list):
        num_vars = [c for c in variable_types.get("numeric", []) if c in shared_cols]
        cat_vars = [c for c in variable_types.get("categorical", []) if c in shared_cols]
    else:
        num_vars = [c for c, t in variable_types.items() if t == "numeric" and c in shared_cols]
        cat_vars = [c for c, t in variable_types.items() if t == "categorical" and c in shared_cols]

    num_vars = [
        c for c in num_vars
        if pd.to_numeric(orig_df[c], errors="coerce").notna().any()
    ]

    report = {
        "num_vars": num_vars,
        "cat_vars": cat_vars,
        "numeric_summary": None,
        "cat_freq": {},
        "ks_tests": [],
        "chi2_tests": [],
        "corr_heatmap_b64": None,
        "corr_heatmap_error": None,
        "mean_corr_diff": None,
        "n_orig": len(orig_df),
        "n_synth": len(synth_df),
    }

    if num_vars:
        orig_num = orig_df[num_vars].apply(pd.to_numeric, errors="coerce")
        synth_num = synth_df[num_vars].apply(pd.to_numeric, errors="coerce")
        orig_desc = orig_num.describe().drop(index=["min", "max"])
        synth_desc = synth_num.describe().drop(index=["min", "max"])
        rows = []
        for stat in orig_desc.index:
            row = {"stat": stat}
            for col in num_vars:
                row[f"{col}__real"] = _safe_float(orig_desc.loc[stat, col])
                row[f"{col}__synth"] = _safe_float(synth_desc.loc[stat, col])
            rows.append(row)
        report["numeric_summary"] = {"rows": rows, "num_vars": num_vars}

    for col in cat_vars:
        orig_freq = _norm_series(orig_df[col].dropna()).value_counts(normalize=True).mul(100).round(1)
        synth_freq = _norm_series(synth_df[col].dropna()).value_counts(normalize=True).mul(100).round(1)
        all_cats = sorted(set(orig_freq.index) | set(synth_freq.index))
        report["cat_freq"][col] = [
            {
                "category": cat,
                "real_pct": _safe_float(orig_freq.get(cat, 0.0), 1),
                "synth_pct": _safe_float(synth_freq.get(cat, 0.0), 1),
            }
            for cat in all_cats
        ]

    for col in num_vars:
        orig_vals = pd.to_numeric(orig_df[col], errors="coerce").dropna()
        synth_vals = pd.to_numeric(synth_df[col], errors="coerce").dropna()
        if len(orig_vals) > 0 and len(synth_vals) > 0:
            stat_val, pval = stats.ks_2samp(orig_vals, synth_vals)
            report["ks_tests"].append({
                "variable": col,
                "statistic": _safe_float(stat_val),
                "pvalue": _safe_float(pval),
                "pass": bool(pval >= 0.05) if pval is not None else None,
            })

    for col in cat_vars:
        orig_norm = _norm_series(orig_df[col].dropna())
        synth_norm = _norm_series(synth_df[col].dropna())
        all_cats = sorted(set(orig_norm) | set(synth_norm))
        real_counts = orig_norm.value_counts().reindex(all_cats, fill_value=0)
        synth_counts = synth_norm.value_counts().reindex(all_cats, fill_value=0)
        scale = len(orig_df) / max(len(synth_df), 1)
        expected = (synth_counts * scale).clip(lower=0.5)
        total_exp = expected.sum()
        if total_exp > 0:
            expected = expected * (real_counts.sum() / total_exp)
        try:
            stat_val, pval = stats.chisquare(f_obs=real_counts, f_exp=expected)
            report["chi2_tests"].append({
                "variable": col,
                "statistic": _safe_float(stat_val),
                "pvalue": _safe_float(pval),
                "pass": bool(pval >= 0.05) if pval is not None else None,
            })
        except Exception:
            pass

    heatmap_vars = num_vars[:30]
    if len(heatmap_vars) >= 2:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np
            import pandas as pd

            real_corr = orig_df[heatmap_vars].apply(pd.to_numeric, errors="coerce").corr()
            synth_corr = synth_df[heatmap_vars].apply(pd.to_numeric, errors="coerce").corr()
            diff = (real_corr - synth_corr).abs()

            n = len(heatmap_vars)
            cell = max(0.7, min(1.4, 10.0 / n))
            fig_w = max(18, n * cell * 3)
            fig_h = max(5, n * cell + 1)
            fig, axes = plt.subplots(1, 3, figsize=(fig_w, fig_h), constrained_layout=True)

            annot = n <= 12
            fs_tick = max(6, min(10, 80 // n))
            fs_annot = max(5, min(8, 60 // n))
            for ax, matrix, title, cmap in zip(
                axes,
                [real_corr, synth_corr, diff],
                ["Real", "Synthetic", "Absolute difference"],
                ["coolwarm", "coolwarm", "Reds"],
            ):
                is_diff = title == "Absolute difference"
                vmax = max(float(diff.values.max()), 0.01) if is_diff else 1.0
                im = ax.imshow(
                    matrix.values, cmap=cmap,
                    vmin=0 if is_diff else -1, vmax=vmax, aspect="auto",
                )
                fig.colorbar(im, ax=ax, shrink=0.8)
                ax.set_xticks(range(n))
                ax.set_yticks(range(n))
                ax.set_xticklabels(matrix.columns, rotation=45, ha="right", fontsize=fs_tick)
                ax.set_yticklabels(matrix.index, fontsize=fs_tick)
                ax.set_title(title, fontsize=11)
                if annot:
                    for i in range(n):
                        for j in range(n):
                            ax.text(
                                j, i, f"{matrix.values[i, j]:.2f}",
                                ha="center", va="center", fontsize=fs_annot,
                                color="white" if abs(matrix.values[i, j]) > 0.6 else "black",
                            )

            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            report["corr_heatmap_b64"] = base64.b64encode(buf.read()).decode("ascii")

            upper_idx = np.triu_indices(n, k=1)
            upper_vals = diff.values[upper_idx]
            if len(upper_vals) > 0:
                report["mean_corr_diff"] = _safe_float(float(upper_vals.mean()))

        except Exception as exc:
            report["corr_heatmap_error"] = str(exc)

    return report


def render_report_html(report: dict) -> str:
    """Convert a build_synth_report() result dict to self-contained HTML for QTextBrowser."""

    def _val(v):
        return "—" if v is None else str(v)

    def _pass_cell(passed):
        if passed is None:
            return "<td align='center'>—</td>"
        if passed:
            return "<td align='center' style='color:green;font-weight:bold;'>✓</td>"
        return "<td align='center' style='color:red;font-weight:bold;'>✗</td>"

    parts = [
        "<html><head><style>",
        "body{font-family:Arial,sans-serif;font-size:12px;margin:8px;}",
        "h2{font-size:13px;color:#333;border-bottom:1px solid #ccc;"
        "padding-bottom:3px;margin-top:12px;margin-bottom:4px;}",
        "h3{font-size:11px;color:#555;margin-top:8px;margin-bottom:2px;}",
        "table{border-collapse:collapse;margin-bottom:8px;font-size:11px;}",
        "th{background:#f0f0f0;padding:3px 6px;border:1px solid #ccc;text-align:left;}",
        "td{padding:3px 6px;border:1px solid #ccc;}",
        ".muted{color:#777;font-size:11px;}",
        ".warn{color:orange;}",
        ".col-divider{border-right:1px solid #e0d8f0;padding-right:12px;}",
        ".col-right{padding-left:12px;}",
        "</style></head><body>",
    ]

    parts.append(
        f"<p class='muted'>Original: <strong>{report['n_orig']:,}</strong> rows"
        f" &nbsp;·&nbsp; "
        f"Synthetic: <strong>{report['n_synth']:,}</strong> rows</p>"
    )

    # ── Build left column (numeric) ───────────────────────────────────────────
    left = []

    ns = report.get("numeric_summary")
    if ns and ns["rows"]:
        left.append("<h2>Numeric summary <span class='muted'>(min/max excluded)</span></h2>")
        left.append("<table><thead><tr><th>Stat</th>")
        for col in ns["num_vars"]:
            left.append(f"<th colspan='2' align='center'>{col}</th>")
        left.append("</tr><tr><th></th>")
        for _ in ns["num_vars"]:
            left.append(
                "<th class='muted' align='right'>Real</th>"
                "<th class='muted' align='right'>Synth</th>"
            )
        left.append("</tr></thead><tbody>")
        for row in ns["rows"]:
            left.append(f"<tr><td><code>{row['stat']}</code></td>")
            for col in ns["num_vars"]:
                left.append(
                    f"<td align='right'>{_val(row.get(col+'__real'))}</td>"
                    f"<td align='right'>{_val(row.get(col+'__synth'))}</td>"
                )
            left.append("</tr>")
        left.append("</tbody></table>")

    if report.get("ks_tests"):
        left.append("<h2>Kolmogorov–Smirnov tests</h2>")
        left.append(
            "<table><thead><tr>"
            "<th>Variable</th><th align='right'>KS</th>"
            "<th align='right'>p-value</th><th align='center'>Pass</th>"
            "</tr></thead><tbody>"
        )
        for row in report["ks_tests"]:
            left.append(
                f"<tr><td><code>{row['variable']}</code></td>"
                f"<td align='right'>{_val(row['statistic'])}</td>"
                f"<td align='right'>{_val(row['pvalue'])}</td>"
                f"{_pass_cell(row['pass'])}</tr>"
            )
        left.append("</tbody></table>")

    # ── Build right column (categorical) ──────────────────────────────────────
    right = []

    if report.get("chi2_tests"):
        right.append("<h2>Chi-squared tests</h2>")
        right.append(
            "<table><thead><tr>"
            "<th>Variable</th><th align='right'>χ²</th>"
            "<th align='right'>p-value</th><th align='center'>Pass</th>"
            "</tr></thead><tbody>"
        )
        for row in report["chi2_tests"]:
            right.append(
                f"<tr><td><code>{row['variable']}</code></td>"
                f"<td align='right'>{_val(row['statistic'])}</td>"
                f"<td align='right'>{_val(row['pvalue'])}</td>"
                f"{_pass_cell(row['pass'])}</tr>"
            )
        right.append("</tbody></table>")

    if report.get("cat_freq"):
        right.append("<h2>Categorical frequency comparison</h2>")
        for col, cats in report["cat_freq"].items():
            right.append(
                f"<h3><code>{col}</code>"
                f" <span class='muted'>({len(cats)} categories)</span></h3>"
            )
            right.append(
                "<table><thead><tr>"
                "<th>Category</th><th align='right'>Real %</th>"
                "<th align='right'>Synth %</th><th align='right'>Diff</th>"
                "</tr></thead><tbody>"
            )
            for c in cats[:50]:
                real_pct = c["real_pct"] or 0.0
                synth_pct = c["synth_pct"] or 0.0
                diff = abs(real_pct - synth_pct)
                warn = " class='warn'" if diff > 5 else ""
                right.append(
                    f"<tr><td>{c['category']}</td>"
                    f"<td align='right'>{real_pct}</td>"
                    f"<td align='right'>{synth_pct}</td>"
                    f"<td align='right'{warn}>{diff:.1f}</td></tr>"
                )
            if len(cats) > 50:
                right.append(
                    f"<tr><td colspan='4' class='muted'>"
                    f"… {len(cats) - 50} more not shown</td></tr>"
                )
            right.append("</tbody></table>")

    # ── Layout: two columns when both sides have content, else single column ──
    if left and right:
        parts.append(
            "<table width='100%' cellspacing='0' cellpadding='0'><tr>"
            "<td valign='top' width='50%' class='col-divider'>"
        )
        parts.extend(left)
        parts.append("</td><td valign='top' width='50%' class='col-right'>")
        parts.extend(right)
        parts.append("</td></tr></table>")
    elif left:
        parts.extend(left)
    elif right:
        parts.extend(right)
    else:
        parts.append(
            "<p class='muted'>No numeric or categorical variables found in common "
            "between the two datasets.</p>"
        )

    # ── Correlation heatmap (full width below columns) ────────────────────────
    if report.get("corr_heatmap_b64"):
        parts.append("<h2>Correlation structure — real vs synthetic</h2>")
        parts.append(
            f"<img src='data:image/png;base64,{report['corr_heatmap_b64']}' "
            f"width='100%' alt='Correlation heatmap'/>"
        )
        if report.get("mean_corr_diff") is not None:
            parts.append(
                f"<p class='muted' align='center'>Mean absolute correlation difference "
                f"(upper triangle): <strong>{report['mean_corr_diff']:.4f}</strong></p>"
            )
    elif report.get("corr_heatmap_error"):
        parts.append(
            f"<p class='warn'>Correlation heatmap could not be generated: "
            f"{report['corr_heatmap_error']}</p>"
        )

    parts.append("</body></html>")
    return "".join(parts)
