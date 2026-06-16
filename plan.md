# SynthPop Desktop — Plan

A standalone Windows desktop application that replicates the **synthetic data
generator** from `SLS-SDC-Dashboard` (Flask web app), as a single-user,
local-file based tool. No database, authentication, SDC checks, or
multi-user/admin features — just: load a CSV, configure synthesis, generate,
review a quality report, export the synthetic CSV.

## Source functionality being ported

| Flask source | What it does |
|---|---|
| `flask/blueprints/synthetic.py` | Routes for config form, generate, progress polling, cancel, download, benchmark, report, delete |
| `flask/jobs/synthesis.py` | `_patch_synthpop` (fixes synthpop's `DataProcessor` pre/post-processing), `_sanitise_for_synthesis`, `_run_synthesis_blocking` (the actual CART / Gaussian Copula synthesis pipeline with progress callbacks) |
| `flask/services/synth_report.py` | `build_synth_report` — numeric summary, KS tests, chi-squared tests, categorical frequency comparison, correlation heatmap (matplotlib → base64 PNG) |
| `flask/blueprints/upload.py` (`_default_variable_types`, `detect_numeric_sentinels`) | Heuristics for default categorical/numeric/ignore classification and missing-value sentinel detection |
| `flask/services/utils.py` | `EXTRA_NA_VALUES`, CSV read/write helpers |
| `flask/templates/synthetic/index.html` | Defines the full set of config options/UI fields to replicate |

## Tech stack

- **Python 3.11+**
- **GUI**: PySide6 (Qt for Python) — native widgets, `QThread` + signals for
  background synthesis (replaces DB-polling job model), `QTextBrowser` for
  rendering the HTML quality report (incl. base64 correlation heatmap image).
- **Core libs** (same as dashboard): `pandas`, `numpy`, `scipy`,
  `scikit-learn`, `python-synthpop`, `matplotlib` (Agg backend for heatmap).
- **Packaging**: PyInstaller → Windows `.exe` (onedir build recommended over
  onefile, given the size of sklearn/scipy/matplotlib).

## Folder layout

```
synthpop-windows/
├── plan.md
├── README.md
├── requirements.txt
├── main.py                     # entry point — launches QApplication
├── core/
│   ├── __init__.py
│   ├── data_io.py               # CSV load, EXTRA_NA_VALUES, var-type & sentinel detection
│   ├── synthesis.py              # _patch_synthpop, _sanitise_for_synthesis,
│   │                              # run_synthesis (blocking, progress_callback + cancel_event),
│   │                              # estimate_time (benchmark)
│   └── report.py                 # build_synth_report (ported ~verbatim) + render_report_html
├── ui/
│   ├── __init__.py
│   ├── main_window.py            # QMainWindow, menu, tab container, app state
│   ├── data_tab.py                # Open CSV, dataset summary, variable-type table
│   ├── config_tab.py              # synthesis config form + "Estimate time"
│   ├── synthesis_worker.py        # QThread/QObject worker wrapping core.synthesis.run_synthesis
│   └── report_tab.py              # runs build_synth_report, renders to QTextBrowser
└── packaging/
    └── synthpop_desktop.spec       # PyInstaller spec
```

## Functional mapping (Flask → Desktop)

| Dashboard feature | Desktop equivalent |
|---|---|
| Upload CSV + variable type wizard | **Data tab**: "Open CSV…" file dialog → dataset summary (rows/cols/filename) → editable table of columns with auto-detected type (categorical / numeric / ignore), cardinality badges, and missing-value sentinel checkboxes (reuse `detect_numeric_sentinels`) |
| Synthesis configuration form | **Configure tab**: n_rows, method radio (CART / Gaussian Copula), skip-imputation switch, CART options (smoothing, proper, minibucket, random_state), GC options (enforce_min_max, enforce_rounding, default_distribution), variable-selection checkboxes (Select All / Deselect All), max_train_rows |
| `/synthetic/benchmark` time estimate | "Estimate synthesis time" button on Configure tab — runs the same scaled-benchmark logic synchronously on a small sample (fast enough not to need a thread) |
| `/synthetic/generate` + background job + progress polling | "Generate Synthetic Data" button → `QThread` worker runs `core.synthesis.run_synthesis`; `progress`/`message` Qt signals update a `QProgressBar` + scrolling log list (replaces DB `background_jobs` + HTMX polling) |
| Cancel job | "Cancel" button sets a `threading.Event`; checked inside the same `progress_callback` hook used today |
| `/synthetic/report` | **Report tab**: enabled once synthesis finishes; calls `build_synth_report(orig_df, synth_df, variable_types)` and renders numeric summary / KS / chi² tables + correlation heatmap as HTML in a `QTextBrowser` |
| `/synthetic/download` | "Save Synthetic CSV…" save-file dialog (`df.to_csv`) |
| Stored synthetic dataset card / delete | In-memory only for this session; "Clear results" button resets state. (No project persistence per user decision — CSV in/out only.) |
| Privacy notice banner | Static label/banner reproducing the same wording, always visible once a synthetic dataset exists |

## Implementation steps

1. **Scaffold project** — create folder structure above, `requirements.txt`
   (`PySide6`, `pandas`, `numpy`, `scipy`, `scikit-learn`, `python-synthpop`,
   `matplotlib`), placeholder `README.md`.

2. **`core/data_io.py`**
   - Port `EXTRA_NA_VALUES`, `detect_numeric_sentinels`, `_default_variable_types`
     (rename `default_variable_types`) from `services/utils.py` /
     `blueprints/upload.py`, with no Flask/DB dependencies.
   - `load_csv(path) -> pd.DataFrame` using `EXTRA_NA_VALUES` /
     `keep_default_na=True`.
   - `column_cardinality(df) -> dict`.

3. **`core/synthesis.py`**
   - Port `_patch_synthpop` and `_sanitise_for_synthesis` verbatim (no DB).
   - Port `_run_synthesis_blocking` → `run_synthesis(df, method, n_rows,
     method_kwargs, max_train_rows, skip_imputation, progress_callback,
     cancel_event)`. Replace the watchdog/DB-cancellation plumbing with a
     simple `threading.Event` checked at each `progress_callback` call
     (raise a local `CancelledError` if set).
   - Port the `/synthetic/benchmark` logic → `estimate_time(df, method,
     max_train_rows, n_rows_out, method_kwargs, skip_imputation) -> dict`
     (returns formatted estimate + fit/sample timings), reusing
     `_BENCHMARK_N`, `_fmt_time`, and the same scaling formulas.

4. **`core/report.py`**
   - Port `build_synth_report` from `services/synth_report.py` essentially
     unchanged (pure pandas/scipy/matplotlib, no Flask deps).
   - Add `render_report_html(report: dict) -> str` that turns the report
     dict into a self-contained HTML fragment (tables + `<img
     src="data:image/png;base64,...">` for the heatmap), translating the
     Jinja template `_report.html` into an f-string/`string.Template`
     equivalent suitable for `QTextBrowser`.

5. **`ui/main_window.py`**
   - `QMainWindow` with menu (File → Open CSV…, Save Synthetic CSV…, Exit),
     status bar, and a `QTabWidget` with **Data / Configure / Report** tabs.
   - Holds shared app state: source `DataFrame`, variable types dict,
     synthetic `DataFrame`, last report dict. Tabs read/write this state via
     simple signals or direct references.

6. **`ui/data_tab.py`**
   - "Open CSV…" button + recent-file label.
   - Summary line: filename, row count, column count.
   - `QTableWidget` listing each column with: detected dtype, cardinality
     badge, and a type selector (categorical / numeric / ignore) defaulting
     via `default_variable_types`.
   - Emits a signal when data + variable types are ready, enabling the
     Configure tab.

7. **`ui/config_tab.py`**
   - Recreate the form fields from `synthetic/index.html`:
     - `n_rows` spinbox (default = source row count)
     - Method radio buttons (CART / Gaussian Copula) toggling two stacked
       option groups (mirrors `updateMethodOptions()`)
     - `skip_imputation` checkbox (default checked)
     - CART group: smoothing, proper, minibucket (spinbox), random_state (spinbox)
     - GC group: enforce_min_max, enforce_rounding, default_distribution (combo box)
     - Column-selection checklist (Select All / Deselect All) sourced from
       Data tab's variable list
     - `max_train_rows` spinbox with a warning label above 50,000
     - "Estimate synthesis time" button → calls `core.synthesis.estimate_time`
       on the UI thread (small sample, should be quick) and shows result text
     - "Generate Synthetic Data" button → starts the worker thread

8. **`ui/synthesis_worker.py`**
   - `QObject`/`QThread` worker wrapping `core.synthesis.run_synthesis`.
   - Signals: `progress(int, str)`, `finished(pd.DataFrame, int)` (synthetic
     df + dupe count), `error(str)`, `cancelled()`.
   - Main window wires these to a progress bar + log `QListWidget` + Cancel
     button (sets the worker's `cancel_event`).

9. **`ui/report_tab.py`**
   - Disabled until a synthetic dataset exists.
   - On synthesis completion, runs `build_synth_report` (likely also off the
     UI thread, or inline if fast enough) and `render_report_html`, then sets
     it on a `QTextBrowser`.
   - Privacy notice banner shown above the report.

10. **Export**
    - "Save Synthetic CSV…" (`QFileDialog.getSaveFileName` → `df.to_csv`).
    - Optional: "Save Report as HTML…" exporting the rendered report.

11. **Error handling & polish**
    - Friendly error dialogs for: bad CSV, no columns selected, synthesis
      exceptions (mirrors the `error` job state).
    - Status bar messages for load/save/generate events.

12. **Packaging**
    - `packaging/synthpop_desktop.spec` for PyInstaller (onedir build).
    - `README.md`: dev setup (`pip install -r requirements.txt`, `python
      main.py`) and Windows build instructions (`pyinstaller
      packaging/synthpop_desktop.spec`), plus a note that the build must be
      run on Windows (or via cross-build) to produce a native `.exe`.

13. **Manual testing**
    - Test with a small sample CSV covering numeric, categorical, and
      missing-value columns: load → configure (both CART and Gaussian
      Copula) → estimate time → generate → cancel mid-run → generate again →
      view report → export CSV.

## Notes / risks

- `python-synthpop` + `scikit-learn` + `scipy` + `matplotlib` make for a
  large PyInstaller bundle (likely several hundred MB) — onedir build and
  clear README guidance recommended over onefile.
- The `_patch_synthpop` monkeypatch must be applied at startup (module import
  time), exactly as in the dashboard, since it fixes a real bug in
  `python-synthpop`'s `DataProcessor`.
- Long-running fit/sample steps must run off the Qt main thread (QThread)
  to keep the UI responsive and allow cancellation.
