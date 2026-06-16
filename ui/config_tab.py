from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QSplitter,
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
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left: config form ─────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(10)

        # ── Synthesis settings group ──────────────────────────────────────────
        synth_box = QGroupBox("Synthesis settings")
        synth_form = QFormLayout(synth_box)
        synth_form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        synth_form.setSpacing(8)

        self._n_rows = QSpinBox()
        self._n_rows.setRange(1, 10_000_000)
        self._n_rows.setValue(1000)
        self._n_rows.setFixedWidth(120)
        synth_form.addRow("Output rows:", self._n_rows)

        method_widget = QWidget()
        method_widget.setStyleSheet("background: transparent;")
        method_layout = QHBoxLayout(method_widget)
        method_layout.setContentsMargins(0, 0, 0, 0)
        method_layout.setSpacing(12)
        self._cart_radio = QRadioButton("CART")
        self._gc_radio = QRadioButton("Gaussian Copula")
        self._cart_radio.setChecked(True)
        self._method_group = QButtonGroup(self)
        self._method_group.addButton(self._cart_radio, 0)
        self._method_group.addButton(self._gc_radio, 1)
        method_layout.addWidget(self._cart_radio)
        method_layout.addWidget(self._gc_radio)
        method_layout.addStretch()
        synth_form.addRow("Method:", method_widget)

        # CART options (nested group)
        self._cart_box = QGroupBox("CART options")
        cart_form = QFormLayout(self._cart_box)
        cart_form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        cart_form.setSpacing(6)
        self._smoothing = QCheckBox("Smoothing")
        self._proper = QCheckBox("Proper synthesis")
        cart_form.addRow(self._smoothing)
        cart_form.addRow(self._proper)
        self._minibucket = QSpinBox()
        self._minibucket.setRange(1, 1000)
        self._minibucket.setValue(5)
        self._minibucket.setFixedWidth(80)
        cart_form.addRow("Minibucket:", self._minibucket)
        self._random_state = QSpinBox()
        self._random_state.setRange(0, 99999)
        self._random_state.setValue(42)
        self._random_state.setFixedWidth(80)
        cart_form.addRow("Random state:", self._random_state)
        synth_form.addRow(self._cart_box)

        # GC options (nested group)
        self._gc_box = QGroupBox("Gaussian Copula options")
        gc_form = QFormLayout(self._gc_box)
        gc_form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        gc_form.setSpacing(6)
        self._enforce_min_max = QCheckBox("Enforce min/max values")
        self._enforce_min_max.setChecked(True)
        self._enforce_rounding = QCheckBox("Enforce rounding")
        self._enforce_rounding.setChecked(True)
        gc_form.addRow(self._enforce_min_max)
        gc_form.addRow(self._enforce_rounding)
        self._default_dist = QComboBox()
        self._default_dist.addItems(_GC_DISTRIBUTIONS)
        gc_form.addRow("Default distribution:", self._default_dist)
        self._gc_box.setVisible(False)
        synth_form.addRow(self._gc_box)

        self._skip_imputation = QCheckBox("Skip missing-data imputation")
        self._skip_imputation.setChecked(True)
        synth_form.addRow(self._skip_imputation)

        self._max_train_rows = QSpinBox()
        self._max_train_rows.setRange(100, 10_000_000)
        self._max_train_rows.setValue(20000)
        self._max_train_rows.setFixedWidth(120)
        synth_form.addRow("Max training rows:", self._max_train_rows)

        self._mtr_warning = QLabel(
            "Warning: training on >50,000 rows may take a very long time."
        )
        self._mtr_warning.setStyleSheet("color: #e65100; font-size: 11px;")
        self._mtr_warning.setVisible(False)
        synth_form.addRow(self._mtr_warning)

        form_layout.addWidget(synth_box)

        # ── Column selection group ────────────────────────────────────────────
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
        self._col_hint.setStyleSheet(
            "color: #777777; font-size: 11px; font-style: italic;"
        )
        col_layout.addWidget(self._col_hint)
        form_layout.addWidget(col_box)

        form_layout.addStretch()
        scroll.setWidget(form_widget)
        splitter.addWidget(scroll)

        # ── Right: progress panel ─────────────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
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
        self._log_list.setStyleSheet(
            "font-size: 11px; font-family: Consolas, monospace;"
        )
        right_layout.addWidget(self._log_list, stretch=1)
        splitter.addWidget(right)

        splitter.setSizes([480, 320])
        root.addWidget(splitter, stretch=1)

        # ── Bottom: action buttons ────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #d0c5e8; max-height: 1px;")
        root.addWidget(sep)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
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

        # ── Tooltips ─────────────────────────────────────────────────────────
        self._n_rows.setToolTip(
            "<p><b>Output rows</b></p>"
            "<p>Number of rows in the synthetic dataset. Defaults to the "
            "same number as the original data. You can request more or fewer "
            "rows than the original — the model is trained once and sampled "
            "as many times as needed.</p>"
        )
        self._cart_radio.setToolTip(
            "<p><b>CART (Classification and Regression Trees)</b></p>"
            "<p>Synthesises each column sequentially using a decision tree "
            "fitted on all previously synthesised columns. Handles mixed "
            "numeric and categorical data naturally and preserves complex "
            "non-linear relationships. Recommended default.</p>"
        )
        self._gc_radio.setToolTip(
            "<p><b>Gaussian Copula</b></p>"
            "<p>Models the joint distribution of numeric variables using a "
            "multivariate Gaussian copula, then fits separate marginal "
            "distributions per column. Faster than CART on large datasets "
            "but assumes the dependency structure is approximately Gaussian. "
            "Less suited to highly non-linear or mixed data.</p>"
        )
        self._smoothing.setToolTip(
            "<p><b>Smoothing</b></p>"
            "<p>Adds small random noise drawn from within each leaf node of "
            "the CART tree, making the synthetic distribution less discretely "
            "blocky. Useful for continuous numeric variables where you want "
            "a smoother output distribution.</p>"
        )
        self._proper.setToolTip(
            "<p><b>Proper synthesis</b></p>"
            "<p>Re-fits the CART model on a bootstrap resample of the data "
            "before each synthesis step, adding model uncertainty to the "
            "synthetic values. Produces more statistically rigorous "
            "inference-safe synthetic data at the cost of slightly lower "
            "fidelity and longer runtime.</p>"
        )
        self._minibucket.setToolTip(
            "<p><b>Minibucket</b></p>"
            "<p>Minimum number of observations required in a leaf node "
            "before the CART tree stops splitting. Higher values produce "
            "simpler, smoother models that are less likely to memorise "
            "individual records. Lower values capture finer detail but "
            "increase disclosure risk. Default 5; increase to 10–25 for "
            "higher privacy assurance.</p>"
        )
        self._random_state.setToolTip(
            "<p><b>Random state (seed)</b></p>"
            "<p>Seed for the random number generator. Using the same seed "
            "with the same data and settings produces identical synthetic "
            "data, enabling reproducibility. Change the value to get a "
            "different synthetic sample from the same model.</p>"
        )
        self._enforce_min_max.setToolTip(
            "<p><b>Enforce min/max values</b></p>"
            "<p>Clips synthetic values to the observed minimum and maximum "
            "of each column. Prevents the Gaussian copula from generating "
            "impossible values such as negative ages or incomes above the "
            "observed ceiling. Recommended.</p>"
        )
        self._enforce_rounding.setToolTip(
            "<p><b>Enforce rounding</b></p>"
            "<p>Rounds synthetic values to match the decimal precision of "
            "the original column. For example, if all original values are "
            "whole numbers, synthetic values will also be whole numbers. "
            "Helps maintain data type consistency.</p>"
        )
        self._default_dist.setToolTip(
            "<p><b>Default distribution</b></p>"
            "<p>Marginal distribution fitted to each numeric column before "
            "the copula transformation is applied:</p>"
            "<ul>"
            "<li><b>norm</b> — standard normal (Gaussian)</li>"
            "<li><b>beta</b> — bounded distribution rescaled to 0–1 "
            "(recommended default)</li>"
            "<li><b>truncnorm</b> — normal distribution clipped at the "
            "observed min/max</li>"
            "<li><b>uniform</b> — flat distribution between min and max</li>"
            "</ul>"
        )
        self._skip_imputation.setToolTip(
            "<p><b>Skip missing-data imputation</b></p>"
            "<p>When checked (recommended), missing values (NaN) are left "
            "as-is and handled natively by synthpop during model fitting. "
            "When unchecked, a separate imputation step fills in missing "
            "values before fitting, which can sometimes improve fidelity "
            "but adds processing time and may introduce artefacts.</p>"
        )
        self._max_train_rows.setToolTip(
            "<p><b>Max training rows</b></p>"
            "<p>Maximum number of rows used to <i>train</i> the synthesis "
            "model. If the dataset is larger, a random subsample is drawn "
            "for fitting. The output can still contain as many rows as "
            "specified in <i>Output rows</i>. Reducing this value "
            "dramatically speeds up synthesis on large datasets with "
            "minimal quality loss. Values above 50,000 may take a very "
            "long time.</p>"
        )
        self._col_list.setToolTip(
            "<p><b>Column selection</b></p>"
            "<p>Tick columns to include in the synthetic dataset. "
            "Columns marked <i>ignore</i> on the Load Data tab are "
            "excluded automatically and do not appear here. Untick "
            "columns you want to omit even if they were classified as "
            "categorical or numeric.</p>"
        )

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
        if not msg:
            return
        item = QListWidgetItem(msg)
        lower = msg.lower()
        if lower.startswith("done") or lower.startswith("complete") or "generated" in lower:
            item.setForeground(QColor("#2e7d32"))   # green
        elif lower.startswith("error") or "failed" in lower:
            item.setForeground(QColor("#c0392b"))   # red
        elif lower.startswith("cancel") or lower.startswith("warning") or "warning:" in lower:
            item.setForeground(QColor("#e65100"))   # orange
        else:
            item.setForeground(QColor("#444444"))
        self._log_list.addItem(item)
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
                variable_types=self._variable_types,
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
            variable_types=self._variable_types,
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
