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

_TYPE_OPTIONS = ["categorical", "numeric", "ignore"]


class DataTab(QWidget):
    """Load CSV, classify variable types, mark sentinel NA values, then confirm."""

    data_ready = Signal(object, object)   # (df: pd.DataFrame, variable_types: dict {col: type})

    def __init__(self, parent=None):
        super().__init__(parent)
        self._df = None
        self._sentinels = {}
        self._sentinel_checks = {}   # {(col, val): QCheckBox}
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)

        # Top bar
        top = QHBoxLayout()
        self._open_btn = QPushButton("Open CSV…")
        self._open_btn.setProperty("role", "export")
        self._open_btn.setFixedWidth(130)
        self._open_btn.clicked.connect(self._open_csv)
        self._file_label = QLabel("No file loaded")
        self._file_label.setStyleSheet("color: #777; font-style: italic;")
        self._file_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        top.addWidget(self._open_btn)
        top.addWidget(self._file_label)
        root.addLayout(top)

        # Summary
        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet("color: #5a3a8e; font-weight: bold;")
        root.addWidget(self._summary_label)

        # Column type table
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Column", "Pandas dtype", "Unique values", "Variable type"])
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionResizeMode(0, self._table.horizontalHeader().ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, self._table.horizontalHeader().ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, self._table.horizontalHeader().ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, self._table.horizontalHeader().ResizeMode.ResizeToContents)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        root.addWidget(self._table, stretch=3)

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
        root.addWidget(self._sentinel_box)

        # Confirm button
        self._confirm_btn = QPushButton("Apply sentinels & confirm variable types  →")
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.setProperty("role", "primary")
        self._confirm_btn.clicked.connect(self._confirm)
        root.addWidget(self._confirm_btn)

    # ── Slots ─────────────────────────────────────────────────────────────────

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
        filename = os.path.basename(path)
        self._file_label.setText(filename)
        self._summary_label.setText(
            f"{len(df):,} rows × {len(df.columns)} columns"
        )
        self._populate_table(df)
        self._populate_sentinels(df)
        self._confirm_btn.setEnabled(True)

    def _populate_table(self, df: pd.DataFrame):
        cat_cols, num_cols = default_variable_types(df)
        cat_set = set(cat_cols)
        num_set = set(num_cols)
        cardinality = column_cardinality(df)

        self._table.setRowCount(len(df.columns))
        for row, col in enumerate(df.columns):
            # Column name
            self._table.setItem(row, 0, QTableWidgetItem(col))
            # Dtype
            self._table.setItem(row, 1, QTableWidgetItem(str(df[col].dtype)))
            # Cardinality
            self._table.setItem(row, 2, QTableWidgetItem(str(cardinality[col])))
            # Type selector
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
        # Clear old checkboxes
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

        # Apply checked sentinels
        for (col, val), cb in self._sentinel_checks.items():
            if cb.isChecked() and col in df.columns:
                df[col] = df[col].replace({val: float("nan"), str(val): float("nan")})

        # Build variable_types dict {col: type}
        variable_types = {}
        for row in range(self._table.rowCount()):
            col = self._table.item(row, 0).text()
            combo = self._table.cellWidget(row, 3)
            variable_types[col] = combo.currentText()

        self.data_ready.emit(df, variable_types)
