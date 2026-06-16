from PySide6.QtCore import QThread, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextBrowser, QFileDialog, QMessageBox, QProgressBar,
)

from ui.synthesis_worker import ReportWorker

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
        self._worker = None
        self._thread = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(6)

        # Privacy notice
        notice = QLabel(_PRIVACY_NOTICE)
        notice.setWordWrap(True)
        notice.setStyleSheet(
            "background: #fff3cd; border: 1px solid #ffc107; "
            "padding: 6px 10px; border-radius: 4px; font-size: 11px;"
        )
        root.addWidget(notice)

        # Top bar
        top = QHBoxLayout()
        self._status_label = QLabel("Generating report…")
        self._status_label.setStyleSheet("color: #555; font-size: 11px;")
        self._save_html_btn = QPushButton("Save Report as HTML…")
        self._save_html_btn.setEnabled(False)
        self._save_html_btn.clicked.connect(self._save_html)
        top.addWidget(self._status_label)
        top.addStretch()
        top.addWidget(self._save_html_btn)
        root.addLayout(top)

        # Progress bar (shown while generating)
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)   # indeterminate
        self._progress.setFixedHeight(6)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        # Report browser
        self._browser = QTextBrowser()
        self._browser.setOpenLinks(False)
        root.addWidget(self._browser, stretch=1)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_data(self, orig_df, synth_df, variable_types):
        """Start async report generation."""
        self._report = None
        self._html = None
        self._save_html_btn.setEnabled(False)
        self._browser.setHtml("<p style='color:#888;'>Building report…</p>")
        self._progress.setVisible(True)
        self._status_label.setText("Generating report…")

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
        self._html = html
        self._progress.setVisible(False)
        self._status_label.setText(
            f"Report ready — {report['n_orig']:,} original rows, "
            f"{report['n_synth']:,} synthetic rows"
        )
        self._browser.setHtml(html)
        self._save_html_btn.setEnabled(True)

    @Slot(str)
    def _on_report_error(self, err: str):
        self._progress.setVisible(False)
        self._status_label.setText("Report generation failed.")
        self._browser.setHtml(
            f"<p style='color:red;'>Report generation failed:<br>{err}</p>"
        )
        QMessageBox.warning(self, "Report error", err)

    @Slot()
    def _cleanup_thread(self):
        self._worker = None
        self._thread = None

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
