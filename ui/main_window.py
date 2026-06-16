from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QFileDialog, QMessageBox, QApplication,
)

from ui.data_tab import DataTab
from ui.config_tab import ConfigTab
from ui.report_tab import ReportTab


class MainWindow(QMainWindow):
    """Top-level window — owns shared state and wires the three tabs together."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SynthPop Desktop")
        self.resize(1100, 750)

        self.source_df = None
        self.variable_types = {}
        self.synth_df = None

        self._build_ui()
        self._build_menu()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self._tabs = QTabWidget()
        self._data_tab = DataTab()
        self._config_tab = ConfigTab()
        self._report_tab = ReportTab()

        self._tabs.addTab(self._data_tab, "Data")
        self._tabs.addTab(self._config_tab, "Configure")
        self._tabs.addTab(self._report_tab, "Report")
        self._tabs.setTabEnabled(1, False)
        self._tabs.setTabEnabled(2, False)

        self.setCentralWidget(self._tabs)
        self.statusBar().showMessage("Open a CSV file to begin.")

        # Signal wiring
        self._data_tab.data_ready.connect(self._on_data_ready)
        self._config_tab.synthesis_complete.connect(self._on_synthesis_complete)

    def _build_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")

        open_act = file_menu.addAction("&Open CSV…")
        open_act.setShortcut("Ctrl+O")
        open_act.triggered.connect(self._open_csv)

        self._save_csv_act = file_menu.addAction("&Save Synthetic CSV…")
        self._save_csv_act.setShortcut("Ctrl+S")
        self._save_csv_act.setEnabled(False)
        self._save_csv_act.triggered.connect(self._save_synth_csv)

        file_menu.addSeparator()

        exit_act = file_menu.addAction("E&xit")
        exit_act.setShortcut("Ctrl+Q")
        exit_act.triggered.connect(QApplication.quit)

    # ── Menu actions ──────────────────────────────────────────────────────────

    def _open_csv(self):
        """Trigger the file-open dialog on the data tab."""
        self._data_tab._open_csv()

    def _save_synth_csv(self):
        if self.synth_df is None:
            QMessageBox.warning(self, "No data", "No synthetic dataset available.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Synthetic CSV", "synthetic_data.csv", "CSV files (*.csv)"
        )
        if path:
            try:
                self.synth_df.to_csv(path, index=False)
                self.statusBar().showMessage(f"Saved: {path}")
            except Exception as exc:
                QMessageBox.critical(self, "Save error", str(exc))

    # ── Tab signal handlers ───────────────────────────────────────────────────

    @Slot(object, object)
    def _on_data_ready(self, df, variable_types: dict):
        self.source_df = df
        self.variable_types = variable_types
        self.synth_df = None

        self._config_tab.set_data(df, variable_types)
        self._tabs.setTabEnabled(1, True)
        self._tabs.setTabEnabled(2, False)
        self._save_csv_act.setEnabled(False)

        self.statusBar().showMessage(
            f"Loaded: {len(df):,} rows × {len(df.columns)} columns  —  "
            f"switch to Configure tab to generate synthetic data."
        )
        self._tabs.setCurrentIndex(1)

    @Slot(object, int)
    def _on_synthesis_complete(self, synth_df, n_dupes: int):
        self.synth_df = synth_df
        self._save_csv_act.setEnabled(True)

        self._report_tab.set_data(self.source_df, synth_df, self.variable_types)
        self._tabs.setTabEnabled(2, True)
        self._tabs.setCurrentIndex(2)

        msg = f"Synthesis complete — {len(synth_df):,} rows"
        if n_dupes:
            msg += f" ({n_dupes:,} duplicates removed)"
        self.statusBar().showMessage(msg)
