from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QSpinBox, QCheckBox, QComboBox,
    QGroupBox, QRadioButton, QButtonGroup, QListWidget,
    QListWidgetItem, QProgressBar, QScrollArea, QMessageBox,
    QSizePolicy, QFrame,
)
from PySide6.QtCore import QThread

from ui.synthesis_worker import SynthesisWorker

_GC_DISTRIBUTIONS = ["beta", "norm", "truncnorm", "uniform"]


class ConfigTab(QWidget):
    """Synthesis configuration form plus progress display."""

    synthesis_complete = Signal(object, int)   # (synthetic_df, n_dupes)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._df = None
        self._variable_types = {}
        self._worker = None
        self._thread = None
        self._build_ui()
        self._set_enabled(False)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(6)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left: config form ─────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(8)

        # Synthesis settings group
        synth_box = QGroupBox("Synthesis settings")
        synth_form = QVBoxLayout(synth_box)

        # n_rows
        row = QHBoxLayout()
        row.addWidget(QLabel("Output rows:"))
        self._n_rows = QSpinBox()
        self._n_rows.setRange(1, 10_000_000)
        self._n_rows.setValue(1000)
        self._n_rows.setFixedWidth(110)
        row.addWidget(self._n_rows)
        row.addStretch()
        synth_form.addLayout(row)

        # Method
        method_row = QHBoxLayout()
        method_row.addWidget(QLabel("Method:"))
        self._cart_radio = QRadioButton("CART")
        self._gc_radio = QRadioButton("Gaussian Copula")
        self._cart_radio.setChecked(True)
        self._method_group = QButtonGroup(self)
        self._method_group.addButton(self._cart_radio, 0)
        self._method_group.addButton(self._gc_radio, 1)
        method_row.addWidget(self._cart_radio)
        method_row.addWidget(self._gc_radio)
        method_row.addStretch()
        synth_form.addLayout(method_row)

        # CART options
        self._cart_box = QGroupBox("CART options")
        cart_layout = QVBoxLayout(self._cart_box)
        self._smoothing = QCheckBox("Smoothing")
        self._proper = QCheckBox("Proper synthesis")
        cart_layout.addWidget(self._smoothing)
        cart_layout.addWidget(self._proper)
        mb_row = QHBoxLayout()
        mb_row.addWidget(QLabel("Minibucket:"))
        self._minibucket = QSpinBox()
        self._minibucket.setRange(1, 1000)
        self._minibucket.setValue(5)
        self._minibucket.setFixedWidth(80)
        mb_row.addWidget(self._minibucket)
        mb_row.addStretch()
        cart_layout.addLayout(mb_row)
        rs_row = QHBoxLayout()
        rs_row.addWidget(QLabel("Random state:"))
        self._random_state = QSpinBox()
        self._random_state.setRange(0, 99999)
        self._random_state.setValue(42)
        self._random_state.setFixedWidth(80)
        rs_row.addWidget(self._random_state)
        rs_row.addStretch()
        cart_layout.addLayout(rs_row)
        synth_form.addWidget(self._cart_box)

        # GC options
        self._gc_box = QGroupBox("Gaussian Copula options")
        gc_layout = QVBoxLayout(self._gc_box)
        self._enforce_min_max = QCheckBox("Enforce min/max values")
        self._enforce_min_max.setChecked(True)
        self._enforce_rounding = QCheckBox("Enforce rounding")
        self._enforce_rounding.setChecked(True)
        gc_layout.addWidget(self._enforce_min_max)
        gc_layout.addWidget(self._enforce_rounding)
        dist_row = QHBoxLayout()
        dist_row.addWidget(QLabel("Default distribution:"))
        self._default_dist = QComboBox()
        self._default_dist.addItems(_GC_DISTRIBUTIONS)
        dist_row.addWidget(self._default_dist)
        dist_row.addStretch()
        gc_layout.addLayout(dist_row)
        self._gc_box.setVisible(False)
        synth_form.addWidget(self._gc_box)

        # skip_imputation
        self._skip_imputation = QCheckBox("Skip missing-data imputation")
        self._skip_imputation.setChecked(True)
        synth_form.addWidget(self._skip_imputation)

        # max_train_rows
        mtr_row = QHBoxLayout()
        mtr_row.addWidget(QLabel("Max training rows:"))
        self._max_train_rows = QSpinBox()
        self._max_train_rows.setRange(100, 10_000_000)
        self._max_train_rows.setValue(20000)
        self._max_train_rows.setFixedWidth(110)
        mtr_row.addWidget(self._max_train_rows)
        mtr_row.addStretch()
        synth_form.addLayout(mtr_row)
        self._mtr_warning = QLabel(
            "Warning: training on >50,000 rows may take a very long time."
        )
        self._mtr_warning.setStyleSheet("color: orange; font-size: 11px;")
        self._mtr_warning.setVisible(False)
        synth_form.addWidget(self._mtr_warning)
        form_layout.addWidget(synth_box)

        # Column selection group
        col_box = QGroupBox("Column selection")
        col_layout = QVBoxLayout(col_box)
        sel_btns = QHBoxLayout()
        self._select_all_btn = QPushButton("Select All")
        self._deselect_all_btn = QPushButton("Deselect All")
        self._select_all_btn.setFixedWidth(90)
        self._deselect_all_btn.setFixedWidth(90)
        sel_btns.addWidget(self._select_all_btn)
        sel_btns.addWidget(self._deselect_all_btn)
        sel_btns.addStretch()
        col_layout.addLayout(sel_btns)
        self._col_list = QListWidget()
        self._col_list.setFixedHeight(180)
        col_layout.addWidget(self._col_list)
        self._col_hint = QLabel("Ignored-type columns are excluded automatically.")
        self._col_hint.setStyleSheet("color: #777777; font-size: 11px; font-style: italic;")
        col_layout.addWidget(self._col_hint)
        form_layout.addWidget(col_box)

        form_layout.addStretch()
        scroll.setWidget(form_widget)
        splitter.addWidget(scroll)

        # ── Right: progress panel ─────────────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(6)
        progress_heading = QLabel("Progress")
        progress_heading.setStyleSheet(
            "font-weight: bold; font-size: 12px; color: #5a3a8e;"
            " padding-left: 8px; border-left: 3px solid #9063CD;"
        )
        right_layout.addWidget(progress_heading)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        right_layout.addWidget(self._progress_bar)

        self._log_list = QListWidget()
        self._log_list.setStyleSheet("font-size: 11px; font-family: Consolas, monospace;")
        right_layout.addWidget(self._log_list, stretch=1)
        splitter.addWidget(right)

        splitter.setSizes([480, 320])
        root.addWidget(splitter, stretch=1)

        # ── Bottom: action buttons ────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #ccc;")
        root.addWidget(sep)

        btn_row = QHBoxLayout()
        self._estimate_btn = QPushButton("Estimate synthesis time")
        self._estimate_btn.setFixedWidth(180)
        self._estimate_label = QLabel("")
        self._estimate_label.setStyleSheet("font-size: 11px; color: #5a3a8e;")
        self._estimate_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._generate_btn = QPushButton("Generate Synthetic Data  →")
        self._generate_btn.setProperty("role", "primary")
        self._generate_btn.setFixedWidth(210)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setProperty("role", "cancel")
        self._cancel_btn.setFixedWidth(80)
        self._cancel_btn.setVisible(False)
        btn_row.addWidget(self._estimate_btn)
        btn_row.addWidget(self._estimate_label)
        btn_row.addStretch()
        btn_row.addWidget(self._generate_btn)
        btn_row.addWidget(self._cancel_btn)
        root.addLayout(btn_row)

        # ── Signal wiring ─────────────────────────────────────────────────────
        self._cart_radio.toggled.connect(self._on_method_changed)
        self._max_train_rows.valueChanged.connect(self._on_mtr_changed)
        self._select_all_btn.clicked.connect(self._select_all)
        self._deselect_all_btn.clicked.connect(self._deselect_all)
        self._estimate_btn.clicked.connect(self._estimate_time)
        self._generate_btn.clicked.connect(self._generate)
        self._cancel_btn.clicked.connect(self._cancel)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_data(self, df, variable_types: dict):
        self._df = df
        self._variable_types = variable_types
        self._n_rows.setValue(len(df))
        self._max_train_rows.setValue(min(len(df), 20000))
        self._populate_columns(variable_types)
        self._set_enabled(True)
        self._clear_progress()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _set_enabled(self, enabled: bool):
        for w in [
            self._n_rows, self._cart_radio, self._gc_radio,
            self._smoothing, self._proper, self._minibucket, self._random_state,
            self._enforce_min_max, self._enforce_rounding, self._default_dist,
            self._skip_imputation, self._max_train_rows,
            self._select_all_btn, self._deselect_all_btn, self._col_list,
            self._estimate_btn, self._generate_btn,
        ]:
            w.setEnabled(enabled)

    def _populate_columns(self, variable_types: dict):
        self._col_list.clear()
        for col, vtype in variable_types.items():
            if vtype == "ignore":
                continue
            item = QListWidgetItem(f"{col}  [{vtype}]")
            item.setData(Qt.ItemDataRole.UserRole, col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self._col_list.addItem(item)

    def _selected_columns(self) -> list:
        cols = []
        for i in range(self._col_list.count()):
            item = self._col_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                cols.append(item.data(Qt.ItemDataRole.UserRole))
        return cols

    def _select_all(self):
        for i in range(self._col_list.count()):
            self._col_list.item(i).setCheckState(Qt.CheckState.Checked)

    def _deselect_all(self):
        for i in range(self._col_list.count()):
            self._col_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    @Slot(bool)
    def _on_method_changed(self, cart_checked: bool):
        self._cart_box.setVisible(cart_checked)
        self._gc_box.setVisible(not cart_checked)

    @Slot(int)
    def _on_mtr_changed(self, value: int):
        self._mtr_warning.setVisible(value > 50_000)

    def _build_method_kwargs(self) -> dict:
        if self._cart_radio.isChecked():
            return {
                "smoothing": self._smoothing.isChecked(),
                "proper": self._proper.isChecked(),
                "minibucket": self._minibucket.value(),
                "random_state": self._random_state.value(),
            }
        return {
            "enforce_min_max_values": self._enforce_min_max.isChecked(),
            "enforce_rounding": self._enforce_rounding.isChecked(),
            "default_distribution": self._default_dist.currentText(),
        }

    def _prepare_df(self):
        if self._df is None:
            return None
        selected = self._selected_columns()
        if not selected:
            QMessageBox.warning(self, "No columns", "Select at least one column.")
            return None
        available = [c for c in selected if c in self._df.columns]
        return self._df[available]

    def _clear_progress(self):
        self._progress_bar.setValue(0)
        self._log_list.clear()

    def _add_log(self, msg: str):
        if msg:
            self._log_list.addItem(msg)
            self._log_list.scrollToBottom()

    # ── Estimate time ─────────────────────────────────────────────────────────

    def _estimate_time(self):
        df = self._prepare_df()
        if df is None:
            return
        from core.synthesis import estimate_time
        method = "CART" if self._cart_radio.isChecked() else "GaussianCopula"
        self._estimate_label.setText("Estimating…")
        try:
            result = estimate_time(
                df,
                method,
                self._max_train_rows.value(),
                self._n_rows.value(),
                self._build_method_kwargs(),
                self._skip_imputation.isChecked(),
            )
            self._estimate_label.setText(
                f"Estimated: ~{result['estimate']}  "
                f"(fit {result['fit_bench']} · sample {result['sample_bench']} "
                f"on {result['bench_n']:,} rows → scaled to "
                f"{result['actual_train_n']:,} train, {result['n_rows_out']:,} output)"
            )
        except Exception as exc:
            self._estimate_label.setText(f"Benchmark failed: {exc}")

    # ── Generate ──────────────────────────────────────────────────────────────

    def _generate(self):
        df = self._prepare_df()
        if df is None:
            return

        self._clear_progress()
        self._generate_btn.setEnabled(False)
        self._estimate_btn.setEnabled(False)
        self._cancel_btn.setVisible(True)

        method = "CART" if self._cart_radio.isChecked() else "GaussianCopula"

        self._worker = SynthesisWorker()
        self._worker.setup(
            df,
            method,
            self._n_rows.value(),
            self._build_method_kwargs(),
            self._max_train_rows.value(),
            self._skip_imputation.isChecked(),
        )

        self._thread = QThread()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.cancelled.connect(self._on_cancelled)

        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._worker.cancelled.connect(self._thread.quit)

        # Drop references only after the OS thread has fully unwound
        self._thread.finished.connect(self._cleanup_thread)

        self._thread.start()

    def _cancel(self):
        if self._worker is not None:
            self._worker.cancel_event.set()
            self._cancel_btn.setEnabled(False)
            self._add_log("Cancellation requested — waiting for current step to finish…")

    @Slot(int, str)
    def _on_progress(self, pct: int, msg: str):
        self._progress_bar.setValue(pct)
        self._add_log(msg)

    @Slot(object, int)
    def _on_finished(self, synth_df, n_dupes: int):
        self._progress_bar.setValue(100)
        msg = f"Done: {len(synth_df):,} rows generated"
        if n_dupes:
            msg += f" ({n_dupes:,} exact duplicates removed)"
        self._add_log(msg)
        self._reset_buttons()
        self.synthesis_complete.emit(synth_df, n_dupes)

    @Slot(str)
    def _on_error(self, err: str):
        self._add_log(f"Error: {err}")
        QMessageBox.critical(self, "Synthesis failed", err)
        self._reset_buttons()

    @Slot()
    def _on_cancelled(self):
        self._add_log("Synthesis cancelled.")
        self._progress_bar.setValue(0)
        self._reset_buttons()

    def _reset_buttons(self):
        self._generate_btn.setEnabled(True)
        self._estimate_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)
        self._cancel_btn.setEnabled(True)

    @Slot()
    def _cleanup_thread(self):
        self._worker = None
        self._thread = None
