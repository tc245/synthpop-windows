import os

import pandas as pd
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QComboBox, QGroupBox,
    QScrollArea, QCheckBox, QFileDialog, QMessageBox,
    QSizePolicy, QAbstractItemView,
)

from core.data_io import load_csv, default_variable_types, detect_numeric_sentinels, column_cardinality
from ui.widgets import CollapsibleBanner

_TYPE_OPTIONS = ["categorical", "numeric", "ignore"]


class DataTab(QWidget):
    """Load CSV, classify variable types, mark sentinel NA values, then confirm."""

    data_ready = Signal(object, object)   # (df: pd.DataFrame, variable_types: dict {col: type})
    data_cleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._df = None
        self._sentinels = {}
        self._sentinel_checks = {}
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # ── Welcome panel (shown until first CSV is loaded) ───────────────────
        self._welcome = self._build_welcome()
        root.addWidget(self._welcome, stretch=1)

        # ── Content area (shown after CSV is loaded) ──────────────────────────
        self._content_area = QWidget()
        self._content_area.setVisible(False)
        cl = QVBoxLayout(self._content_area)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(8)

        # Instruction banner
        cl.addWidget(CollapsibleBanner(
            "Step 1 — Review your data before synthesis",
            "<ol style='margin:4px 0 0 0; padding-left:20px;'>"
            "<li>Check each column's <b>Variable type</b> — set it to "
            "<i>categorical</i>, <i>numeric</i>, or <i>ignore</i> as appropriate.</li>"
            "<li>If sentinel codes are detected (e.g. −99 meaning &quot;missing&quot;), "
            "tick the ones that should be treated as missing values (NaN).</li>"
            "<li>Click <b>Apply sentinels &amp; confirm variable types</b> when ready.</li>"
            "</ol>",
        ))

        # File info bar
        info_bar = QHBoxLayout()
        reload_btn = QPushButton("Open different CSV…")
        reload_btn.setFixedWidth(165)
        reload_btn.clicked.connect(self._open_csv)
        clear_btn = QPushButton("Clear data")
        clear_btn.setFixedWidth(90)
        clear_btn.setProperty("role", "destructive")
        clear_btn.clicked.connect(self._clear_data)
        self._file_label = QLabel("")
        self._file_label.setStyleSheet(
            "color: #5a3a8e; font-weight: bold; padding-left: 4px;"
        )
        self._file_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet("color: #777777; font-size: 11px;")
        info_bar.addWidget(reload_btn)
        info_bar.addWidget(clear_btn)
        info_bar.addSpacing(6)
        info_bar.addWidget(self._file_label)
        info_bar.addWidget(self._summary_label)
        info_bar.addStretch()
        cl.addLayout(info_bar)

        # Column type table
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["Column", "Pandas dtype", "Unique values", "Variable type"]
        )
        hh = self._table.horizontalHeader()
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(0, hh.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, hh.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, hh.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, hh.ResizeMode.ResizeToContents)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        cl.addWidget(self._table, stretch=3)

        # Sentinel section
        self._sentinel_box = QGroupBox("Potential missing-value sentinel codes detected")
        self._sentinel_box.setVisible(False)
        sent_layout = QVBoxLayout(self._sentinel_box)
        hint = QLabel(
            "Check codes that should be treated as missing (NaN). "
            "Pre-checked codes are known sentinel patterns (e.g. -99, -999)."
        )
        hint.setStyleSheet("color: #5a3a8e; font-size: 11px;")
        hint.setWordWrap(True)
        sent_layout.addWidget(hint)

        self._sentinel_scroll = QScrollArea()
        self._sentinel_scroll.setWidgetResizable(True)
        self._sentinel_scroll.setFixedHeight(140)
        self._sentinel_inner = QWidget()
        self._sentinel_inner_layout = QVBoxLayout(self._sentinel_inner)
        self._sentinel_inner_layout.setSpacing(2)
        self._sentinel_scroll.setWidget(self._sentinel_inner)
        sent_layout.addWidget(self._sentinel_scroll)
        cl.addWidget(self._sentinel_box)

        # Confirm button
        self._confirm_btn = QPushButton("Apply sentinels & confirm variable types  →")
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.setProperty("role", "primary")
        self._confirm_btn.clicked.connect(self._confirm)
        cl.addWidget(self._confirm_btn)

        root.addWidget(self._content_area, stretch=3)

    def _build_welcome(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        logo = QLabel("SLS")
        logo.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        logo.setStyleSheet(
            "color: #9063CD; font-size: 52px; font-weight: bold;"
            " letter-spacing: 8px; background: transparent;"
        )
        layout.addWidget(logo)

        title = QLabel("Synthetic Data Generator")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title.setStyleSheet(
            "color: #5a3a8e; font-size: 16px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(title)

        layout.addSpacing(6)

        desc = QLabel(
            "Generate privacy-preserving synthetic datasets from CSV files\n"
            "using CART or Gaussian Copula synthesis methods."
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        desc.setStyleSheet("color: #888888; font-size: 12px; background: transparent;")
        layout.addWidget(desc)

        layout.addSpacing(24)

        self._open_btn = QPushButton("Open a CSV file to get started  →")
        self._open_btn.setProperty("role", "primary")
        self._open_btn.setMinimumWidth(280)
        self._open_btn.setFixedHeight(38)
        self._open_btn.clicked.connect(self._open_csv)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._open_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addSpacing(28)

        steps = QLabel(
            "Step 1: Load data   →   Step 2: Configure & Generate   →   Step 3: Review & Export"
        )
        steps.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        steps.setStyleSheet("color: #bbbbbb; font-size: 10px; background: transparent;")
        layout.addWidget(steps)

        layout.addStretch()
        return w

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _clear_data(self):
        reply = QMessageBox.question(
            self, "Clear data",
            "Clear the loaded dataset and return to the start screen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._df = None
        self._sentinels = {}
        self._sentinel_checks = {}
        self._table.setRowCount(0)
        self._file_label.setText("")
        self._summary_label.setText("")
        self._confirm_btn.setEnabled(False)
        self._content_area.setVisible(False)
        self._welcome.setVisible(True)
        self.data_cleared.emit()

    def _open_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV", "", "CSV files (*.csv);;All files (*)"
        )
        if not path:
            return
        try:
            df = load_csv(path)
        except Exception as exc:
            QMessageBox.critical(self, "Load error", f"Could not read CSV:\n{exc}")
            return

        self._df = df
        self._file_label.setText(os.path.basename(path))
        self._summary_label.setText(f"  {len(df):,} rows × {len(df.columns)} columns")
        self._populate_table(df)
        self._populate_sentinels(df)
        self._confirm_btn.setEnabled(True)

        self._welcome.setVisible(False)
        self._content_area.setVisible(True)

    def _populate_table(self, df: pd.DataFrame):
        cat_cols, num_cols = default_variable_types(df)
        cat_set = set(cat_cols)
        num_set = set(num_cols)
        cardinality = column_cardinality(df)

        self._table.setRowCount(len(df.columns))
        for row, col in enumerate(df.columns):
            self._table.setItem(row, 0, QTableWidgetItem(col))
            self._table.setItem(row, 1, QTableWidgetItem(str(df[col].dtype)))
            self._table.setItem(row, 2, QTableWidgetItem(str(cardinality[col])))
            combo = QComboBox()
            combo.addItems(_TYPE_OPTIONS)
            if col in cat_set:
                combo.setCurrentText("categorical")
            elif col in num_set:
                combo.setCurrentText("numeric")
            else:
                combo.setCurrentText("ignore")
            self._table.setCellWidget(row, 3, combo)

        self._table.resizeRowsToContents()

    def _populate_sentinels(self, df: pd.DataFrame):
        while self._sentinel_inner_layout.count():
            item = self._sentinel_inner_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._sentinel_checks.clear()

        self._sentinels = detect_numeric_sentinels(df)
        if not self._sentinels:
            self._sentinel_box.setVisible(False)
            return

        for col, suspects in self._sentinels.items():
            for val, freq, suggested in suspects:
                label = f"{col}: {val}  ({freq:.1%} of non-null values)"
                cb = QCheckBox(label)
                cb.setChecked(suggested)
                self._sentinel_inner_layout.addWidget(cb)
                self._sentinel_checks[(col, val)] = cb

        self._sentinel_inner_layout.addStretch()
        self._sentinel_box.setVisible(True)

    def _confirm(self):
        if self._df is None:
            return

        df = self._df.copy()

        for (col, val), cb in self._sentinel_checks.items():
            if cb.isChecked() and col in df.columns:
                df[col] = df[col].replace({val: float("nan"), str(val): float("nan")})

        variable_types = {}
        for row in range(self._table.rowCount()):
            col = self._table.item(row, 0).text()
            combo = self._table.cellWidget(row, 3)
            variable_types[col] = combo.currentText()

        self.data_ready.emit(df, variable_types)
