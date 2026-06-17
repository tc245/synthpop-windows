"""PDF and Excel export for the synthetic data quality report."""
import base64
import io


# ── PDF ───────────────────────────────────────────────────────────────────────

def export_pdf(html: str, path: str) -> None:
    """Write the report HTML to a PDF file using Qt's built-in PDF printer.

    Uses QPrinter + QTextDocument so no native system libraries are needed
    beyond PySide6 itself (weasyprint requires GTK/Cairo on Windows).
    """
    from PySide6.QtCore import QMarginsF
    from PySide6.QtGui import QPageLayout, QPageSize, QTextDocument
    from PySide6.QtPrintSupport import QPrinter

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(path)
    printer.setPageLayout(QPageLayout(
        QPageSize(QPageSize.PageSizeId.A4),
        QPageLayout.Orientation.Portrait,
        QMarginsF(15, 15, 15, 15),
    ))

    doc = QTextDocument()
    doc.setHtml(html)
    doc.print_(printer)


# ── Excel ─────────────────────────────────────────────────────────────────────

_PURPLE   = "FF9063CD"
_PUR_DARK = "FF5A3A8E"
_PUR_LITE = "FFEDE8F8"
_GREEN    = "FF61A229"
_RED      = "FFC0392B"
_GREY_HDR = "FFF0F0F0"
_WHITE    = "FFFFFFFF"


def _hdr(ws, row, col, value, bold=True, bg=_GREY_HDR, fg="FF333333"):
    from openpyxl.styles import Font, PatternFill, Alignment
    cell = ws.cell(row=row, column=col, value=value)
    cell.font = Font(bold=bold, color=fg)
    cell.fill = PatternFill("solid", fgColor=bg)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    return cell


def _val(ws, row, col, value, align="right", bold=False, fg="FF333333"):
    from openpyxl.styles import Font, Alignment
    cell = ws.cell(row=row, column=col, value=value)
    cell.font = Font(bold=bold, color=fg)
    cell.alignment = Alignment(horizontal=align, vertical="center")
    return cell


def _pass_cell(ws, row, col, passed):
    if passed is None:
        _val(ws, row, col, "—", align="center")
    elif passed:
        _val(ws, row, col, "✓", align="center", bold=True, fg=_GREEN)
    else:
        _val(ws, row, col, "✗", align="center", bold=True, fg=_RED)


def _auto_width(ws, min_w=10, max_w=40):
    from openpyxl.utils import get_column_letter
    for col_cells in ws.columns:
        length = max(
            len(str(c.value or "")) for c in col_cells
        )
        ws.column_dimensions[get_column_letter(col_cells[0].column)].width = (
            min(max_w, max(min_w, length + 2))
        )


def export_excel(report: dict, path: str) -> None:
    """Write the quality report to a multi-sheet Excel workbook."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.drawing.image import Image as XLImage

    wb = Workbook()
    wb.remove(wb.active)   # remove default blank sheet

    thin = Side(style="thin", color="FFD0C5E8")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    def _apply_border(ws, min_row, max_row, min_col, max_col):
        for r in range(min_row, max_row + 1):
            for c in range(min_col, max_col + 1):
                ws.cell(r, c).border = border

    # ── Sheet 1: Overview ─────────────────────────────────────────────────────
    ws = wb.create_sheet("Overview")
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 20

    title = ws.cell(1, 1, "SLS SynthPop Quality Report")
    title.font = Font(bold=True, size=14, color=_WHITE)
    title.fill = PatternFill("solid", fgColor=_PUR_DARK)
    title.alignment = Alignment(horizontal="left", vertical="center")
    ws.merge_cells("A1:B1")
    ws.row_dimensions[1].height = 28

    for r, (label, value) in enumerate([
        ("Original rows", f"{report['n_orig']:,}"),
        ("Synthetic rows", f"{report['n_synth']:,}"),
        ("Mean correlation difference",
         f"{report['mean_corr_diff']:.4f}" if report.get("mean_corr_diff") is not None else "—"),
    ], start=2):
        ws.cell(r, 1, label).font = Font(bold=True, color=_PUR_DARK)
        ws.cell(r, 2, value).alignment = Alignment(horizontal="right")

    # ── Sheet 2: Numeric Statistics ───────────────────────────────────────────
    ns = report.get("numeric_summary")
    if ns and ns["rows"]:
        ws2 = wb.create_sheet("Numeric Statistics")
        num_vars = ns["num_vars"]

        # Header row 1: Stat | var var var …
        _hdr(ws2, 1, 1, "Statistic", bg=_PUR_DARK, fg=_WHITE)
        for i, col in enumerate(num_vars):
            c = 2 + i * 2
            _hdr(ws2, 1, c, col, bg=_PUR_DARK, fg=_WHITE)
            _hdr(ws2, 1, c + 1, "", bg=_PUR_DARK, fg=_WHITE)
            ws2.merge_cells(
                start_row=1, start_column=c, end_row=1, end_column=c + 1
            )

        # Header row 2: blank | Real Synth Real Synth …
        _hdr(ws2, 2, 1, "", bg=_GREY_HDR)
        for i in range(len(num_vars)):
            c = 2 + i * 2
            _hdr(ws2, 2, c, "Real")
            _hdr(ws2, 2, c + 1, "Synth")

        for r_idx, row in enumerate(ns["rows"], start=3):
            _val(ws2, r_idx, 1, row["stat"], align="left", bold=True)
            for i, col in enumerate(num_vars):
                c = 2 + i * 2
                _val(ws2, r_idx, c, row.get(f"{col}__real"))
                _val(ws2, r_idx, c + 1, row.get(f"{col}__synth"))

        _apply_border(ws2, 1, 2 + len(ns["rows"]), 1, 1 + len(num_vars) * 2)
        _auto_width(ws2)

    # ── Sheet 3: KS Tests ─────────────────────────────────────────────────────
    if report.get("ks_tests"):
        ws3 = wb.create_sheet("KS Tests")
        for c, label in enumerate(["Variable", "KS Statistic", "p-value", "Pass (p≥0.05)"], 1):
            _hdr(ws3, 1, c, label, bg=_PUR_DARK, fg=_WHITE)
        for r, row in enumerate(report["ks_tests"], start=2):
            _val(ws3, r, 1, row["variable"], align="left")
            _val(ws3, r, 2, row["statistic"])
            _val(ws3, r, 3, row["pvalue"])
            _pass_cell(ws3, r, 4, row["pass"])
        _apply_border(ws3, 1, 1 + len(report["ks_tests"]), 1, 4)
        _auto_width(ws3)

    # ── Sheet 4: Chi-squared Tests ────────────────────────────────────────────
    if report.get("chi2_tests"):
        ws4 = wb.create_sheet("Chi-squared Tests")
        for c, label in enumerate(["Variable", "χ² Statistic", "p-value", "Pass (p≥0.05)"], 1):
            _hdr(ws4, 1, c, label, bg=_PUR_DARK, fg=_WHITE)
        for r, row in enumerate(report["chi2_tests"], start=2):
            _val(ws4, r, 1, row["variable"], align="left")
            _val(ws4, r, 2, row["statistic"])
            _val(ws4, r, 3, row["pvalue"])
            _pass_cell(ws4, r, 4, row["pass"])
        _apply_border(ws4, 1, 1 + len(report["chi2_tests"]), 1, 4)
        _auto_width(ws4)

    # ── Sheet 5: Categorical Frequencies ─────────────────────────────────────
    if report.get("cat_freq"):
        ws5 = wb.create_sheet("Categorical Frequencies")
        for c, label in enumerate(["Variable", "Category", "Real %", "Synth %", "Diff"], 1):
            _hdr(ws5, 1, c, label, bg=_PUR_DARK, fg=_WHITE)
        r = 2
        for col, cats in report["cat_freq"].items():
            first = True
            for cat in cats:
                real_pct = cat["real_pct"] or 0.0
                synth_pct = cat["synth_pct"] or 0.0
                diff = round(abs(real_pct - synth_pct), 1)
                _val(ws5, r, 1, col if first else "", align="left", bold=first)
                _val(ws5, r, 2, str(cat["category"]), align="left")
                _val(ws5, r, 3, real_pct)
                _val(ws5, r, 4, synth_pct)
                fg = _RED if diff > 5 else "FF333333"
                _val(ws5, r, 5, diff, fg=fg)
                first = False
                r += 1
        _apply_border(ws5, 1, r - 1, 1, 5)
        _auto_width(ws5)

    # ── Sheet 6: Correlation Heatmap ──────────────────────────────────────────
    if report.get("corr_heatmap_b64"):
        ws6 = wb.create_sheet("Correlation Heatmap")
        img_data = base64.b64decode(report["corr_heatmap_b64"])
        img = XLImage(io.BytesIO(img_data))
        # Scale to fit reasonably within Excel (max ~1400px wide at 96dpi)
        scale = min(1.0, 1400 / (img.width or 1400))
        img.width = int(img.width * scale)
        img.height = int(img.height * scale)
        ws6.add_image(img, "A1")
        if report.get("mean_corr_diff") is not None:
            row_offset = max(40, img.height // 20 + 2)
            ws6.cell(row_offset, 1,
                     f"Mean absolute correlation difference (upper triangle): "
                     f"{report['mean_corr_diff']:.4f}")

    wb.save(path)
