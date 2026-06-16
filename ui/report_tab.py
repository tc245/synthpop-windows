import base64

from PySide6.QtCore import QByteArray, QThread, Slot
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextBrowser, QFileDialog, QMessageBox, QProgressBar,
)

from ui.synthesis_worker import ReportWorker

# Unique text marker; replaces the <img> tag in the display HTML so we can
# locate the insertion point via QTextCursor.find() after setHtml().
_HEATMAP_MARKER = "CORR_HEATMAP_IMAGE_PLACEHOLDER_xk7q"

_PRIVACY_NOTICE = (
    "<b>Privacy notice:</b> The synthetic dataset preserves statistical properties "
    "of the original data while reducing re-identification risk. "
    "It must not be treated as real data or used to make inferences about individuals."
)


class ReportTab(QWidget):
    """Display the synthetic data quality report in a QTextBrowser."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._report = None
        self._html = None
        self._synth_df = None
        self._worker = None
        self._thread = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(8)

        # Privacy notice
        notice = QLabel(_PRIVACY_NOTICE)
        notice.setWordWrap(True)
        notice.setStyleSheet(
            "background: #ede8f8; border: 1px solid #9063CD;"
            " border-left: 4px solid #5a3a8e;"
            " padding: 6px 10px; border-radius: 4px; font-size: 11px;"
            " color: #3d2570;"
        )
        root.addWidget(notice)

        # Top bar: status badge + export buttons
        top = QHBoxLayout()
        self._status_label = QLabel("")
        self._status_label.setFixedHeight(26)
        self._set_status("loading", "Generating report…")
        self._save_csv_btn = QPushButton("Save Synthetic CSV…")
        self._save_csv_btn.setProperty("role", "export")
        self._save_csv_btn.setEnabled(False)
        self._save_csv_btn.clicked.connect(self._save_csv)
        self._save_html_btn = QPushButton("Save Report as HTML…")
        self._save_html_btn.setProperty("role", "export")
        self._save_html_btn.setEnabled(False)
        self._save_html_btn.clicked.connect(self._save_html)
        top.addWidget(self._status_label)
        top.addStretch()
        top.addWidget(self._save_csv_btn)
        top.addWidget(self._save_html_btn)
        root.addLayout(top)

        # Indeterminate progress bar shown while report is being generated
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedHeight(6)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        # Report browser
        self._browser = QTextBrowser()
        self._browser.setOpenLinks(False)
        root.addWidget(self._browser, stretch=1)

    # ── Status badge ─────────────────────────────────────────────────────────

    def _set_status(self, state: str, text: str):
        _styles = {
            "loading": ("background:#ede8f8; color:#5a3a8e; border:1px solid #9063CD;", "●  "),
            "ready":   ("background:#e8f5e9; color:#2e7d32; border:1px solid #61a229;", "✓  "),
            "error":   ("background:#fdecea; color:#c0392b; border:1px solid #c0392b;", "✗  "),
        }
        style, prefix = _styles.get(state, _styles["loading"])
        self._status_label.setText(prefix + text)
        self._status_label.setStyleSheet(
            f"{style} font-size: 11px; font-weight: bold;"
            " padding: 3px 10px; border-radius: 10px;"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def set_data(self, orig_df, synth_df, variable_types):
        """Store synth_df and start async report generation."""
        self._synth_df = synth_df
        self._report = None
        self._html = None
        self._save_csv_btn.setEnabled(True)
        self._save_html_btn.setEnabled(False)
        self._browser.setHtml("<p style='color:#888;'>Building report…</p>")
        self._progress.setVisible(True)
        self._set_status("loading", "Generating report…")

        self._worker = ReportWorker()
        self._worker.setup(orig_df, synth_df, variable_types)

        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_report_ready)
        self._worker.error.connect(self._on_report_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)

        self._thread.start()

    # ── Slots ─────────────────────────────────────────────────────────────────

    @Slot(dict, str)
    def _on_report_ready(self, report: dict, html: str):
        self._report = report
        self._html = html  # keep original (with data: URI) for Save HTML export
        self._progress.setVisible(False)
        self._set_status(
            "ready",
            f"Report ready — {report['n_orig']:,} original rows, "
            f"{report['n_synth']:,} synthetic rows",
        )

        # QTextBrowser cannot render data: URI images — Qt's URL handling
        # truncates the base64 payload before it reaches loadResource().
        # All URL/cache-based workarounds also fail because setHtml() calls
        # document.clear() which wipes any pre-registered resources.
        #
        # Solution: replace the <img> tag with a plain-text marker, call
        # setHtml(), then use QTextCursor.insertImage(QImage) to embed the
        # decoded image directly into the document.  No URL lookup involved.
        heatmap_img: QImage | None = None
        display_html = html
        b64 = report.get("corr_heatmap_b64")
        if b64:
            try:
                img = QImage()
                img.loadFromData(QByteArray(base64.b64decode(b64)))
                if not img.isNull():
                    heatmap_img = img
                    # Exact tag text produced by core/report.py
                    img_tag = (
                        f"<img src='data:image/png;base64,{b64}' "
                        f"width='100%' alt='Correlation heatmap'/>"
                    )
                    display_html = html.replace(img_tag, _HEATMAP_MARKER)
            except Exception as exc:
                print(f"[report] heatmap decode failed: {exc}", flush=True)

        self._browser.setHtml(display_html)

        # Locate the marker in the rendered document and swap it for the image.
        if heatmap_img is not None:
            cursor = self._browser.document().find(_HEATMAP_MARKER)
            if not cursor.isNull():
                cursor.removeSelectedText()
                cursor.insertImage(heatmap_img)
            else:
                print("[report] heatmap marker not found in document", flush=True)

        self._save_html_btn.setEnabled(True)

    @Slot(str)
    def _on_report_error(self, err: str):
        self._progress.setVisible(False)
        self._set_status("error", "Report generation failed.")
        self._browser.setHtml(
            f"<p style='color:red;'>Report generation failed:<br>{err}</p>"
        )
        QMessageBox.warning(self, "Report error", err)

    @Slot()
    def _cleanup_thread(self):
        self._worker = None
        self._thread = None

    def _save_csv(self):
        if self._synth_df is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Synthetic CSV", "synthetic_data.csv", "CSV files (*.csv)"
        )
        if path:
            try:
                self._synth_df.to_csv(path, index=False)
            except Exception as exc:
                QMessageBox.critical(self, "Save error", str(exc))

    def _save_html(self):
        if not self._html:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Report", "synth_report.html", "HTML files (*.html)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self._html)
            except Exception as exc:
                QMessageBox.critical(self, "Save error", str(exc))
