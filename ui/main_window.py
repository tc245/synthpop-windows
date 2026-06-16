from PySide6.QtCore import Slot
from PySide6.QtWidgets import QMainWindow, QTabWidget

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

        self._data_tab.data_ready.connect(self._on_data_ready)
        self._config_tab.synthesis_complete.connect(self._on_synthesis_complete)

    @Slot(object, object)
    def _on_data_ready(self, df, variable_types: dict):
        self.source_df = df
        self.variable_types = variable_types
        self.synth_df = None

        self._config_tab.set_data(df, variable_types)
        self._tabs.setTabEnabled(1, True)
        self._tabs.setTabEnabled(2, False)

        self.statusBar().showMessage(
            f"Loaded: {len(df):,} rows × {len(df.columns)} columns  —  "
            f"switch to Configure tab to generate synthetic data."
        )
        self._tabs.setCurrentIndex(1)

    @Slot(object, int)
    def _on_synthesis_complete(self, synth_df, n_dupes: int):
        self.synth_df = synth_df

        self._report_tab.set_data(self.source_df, synth_df, self.variable_types)
        self._tabs.setTabEnabled(2, True)
        self._tabs.setCurrentIndex(2)

        msg = f"Synthesis complete — {len(synth_df):,} rows"
        if n_dupes:
            msg += f" ({n_dupes:,} duplicates removed)"
        self.statusBar().showMessage(msg)
