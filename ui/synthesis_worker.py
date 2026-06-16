import threading

from PySide6.QtCore import QObject, Signal, Slot


class SynthesisWorker(QObject):
    """Runs core.synthesis.run_synthesis in a QThread.

    Usage:
        worker = SynthesisWorker()
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(...)
        worker.finished.connect(...)
        worker.setup(df, method, n_rows, method_kwargs, max_train_rows, skip_imputation)
        thread.start()
    """

    progress = Signal(int, str)
    finished = Signal(object, int)   # (synthetic_df, n_dupes)
    error = Signal(str)
    cancelled = Signal()

    def setup(self, df, method, n_rows, method_kwargs, max_train_rows, skip_imputation,
              variable_types=None):
        self._df = df
        self._method = method
        self._n_rows = n_rows
        self._method_kwargs = method_kwargs
        self._max_train_rows = max_train_rows
        self._skip_imputation = skip_imputation
        self._variable_types = variable_types
        self.cancel_event = threading.Event()

    @Slot()
    def run(self):
        from core.synthesis import run_synthesis, CancelledError
        try:
            synth_df, n_dupes = run_synthesis(
                self._df,
                self._method,
                self._n_rows,
                self._method_kwargs,
                self._max_train_rows,
                self._skip_imputation,
                self._emit_progress,
                self.cancel_event,
                variable_types=self._variable_types,
            )
            self.finished.emit(synth_df, n_dupes)
        except CancelledError:
            self.cancelled.emit()
        except Exception as exc:
            self.error.emit(str(exc))

    def _emit_progress(self, pct: int, msg: str):
        self.progress.emit(pct, msg)


class ReportWorker(QObject):
    """Runs build_synth_report + render_report_html in a QThread."""

    finished = Signal(dict, str)   # (report_dict, html_str)
    error = Signal(str)

    def setup(self, orig_df, synth_df, variable_types):
        self._orig_df = orig_df
        self._synth_df = synth_df
        self._variable_types = variable_types

    @Slot()
    def run(self):
        from core.report import build_synth_report, render_report_html
        try:
            report = build_synth_report(self._orig_df, self._synth_df, self._variable_types)
            html = render_report_html(report)
            self.finished.emit(report, html)
        except Exception as exc:
            self.error.emit(str(exc))
