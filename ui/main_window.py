from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget,
)

from ui.data_tab import DataTab
from ui.config_tab import ConfigTab
from ui.report_tab import ReportTab


class MainWindow(QMainWindow):
    """Top-level window — owns shared state and wires the three tabs together."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SLS Synthetic Data Generator")
        self.resize(1100, 760)

        self.source_df = None
        self.variable_types = {}
        self.synth_df = None

        self._build_ui()

    # ── Header banner ─────────────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("appHeader")
        header.setStyleSheet(
            "#appHeader {"
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            "    stop:0 #5a3a8e, stop:1 #9063CD);"
            "  min-height: 52px;"
            "}"
        )
        h = QHBoxLayout(header)
        h.setContentsMargins(18, 0, 18, 0)
        h.setSpacing(10)

        brand = QLabel("SLS")
        brand.setStyleSheet(
            "color: white; font-size: 24px; font-weight: bold;"
            " letter-spacing: 3px; background: transparent;"
        )
        divider = QLabel("|")
        divider.setStyleSheet("color: #b89ee0; font-size: 20px; background: transparent;")
        subtitle = QLabel("Synthetic Data Generator")
        subtitle.setStyleSheet(
            "color: #e8dcff; font-size: 14px; font-weight: bold; background: transparent;"
        )

        h.addWidget(brand)
        h.addWidget(divider)
        h.addWidget(subtitle)
        h.addStretch()

        org = QLabel("Scottish Longitudinal Study Development & Support Unit")
        org.setStyleSheet("color: #c0a8e8; font-size: 10px; background: transparent;")
        h.addWidget(org)

        return header

    # ── Main layout ───────────────────────────────────────────────────────────

    def _build_ui(self):
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)

        wrapper_layout.addWidget(self._build_header())

        self._tabs = QTabWidget()
        self._data_tab = DataTab()
        self._config_tab = ConfigTab()
        self._report_tab = ReportTab()

        self._tabs.addTab(self._data_tab,   "1 · Load Data")
        self._tabs.addTab(self._config_tab, "2 · Configure & Generate")
        self._tabs.addTab(self._report_tab, "3 · Report & Export")
        self._tabs.setTabEnabled(1, False)
        self._tabs.setTabEnabled(2, False)

        wrapper_layout.addWidget(self._tabs)
        self.setCentralWidget(wrapper)
        self.statusBar().showMessage("Open a CSV file to begin.")

        self._data_tab.data_ready.connect(self._on_data_ready)
        self._config_tab.synthesis_complete.connect(self._on_synthesis_complete)

    # ── Slots ─────────────────────────────────────────────────────────────────

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
            f"configure synthesis in the next tab."
        )
        self._tabs.setCurrentIndex(1)

    @Slot(object, int)
    def _on_synthesis_complete(self, synth_df, n_dupes: int):
        self.synth_df = synth_df

        self._report_tab.set_data(self.source_df, synth_df, self.variable_types)
        self._tabs.setTabEnabled(2, True)
        self._tabs.setCurrentIndex(2)

        msg = f"Synthesis complete — {len(synth_df):,} rows generated"
        if n_dupes:
            msg += f" ({n_dupes:,} duplicates removed)"
        self.statusBar().showMessage(msg)
