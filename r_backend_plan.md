# R Synthesis Backend Plan

Replace `python-synthpop` with the R `synthpop` package called via subprocess.
Targeted at TRE deployment where R is already installed; the Python fallback
remains available for non-TRE use.

---

## Motivation

- The R `synthpop` package is the authoritative implementation — more mature,
  actively maintained, and more thoroughly validated in research contexts.
- In the TRE, R and `synthpop` are already installed, so no bundling is needed.
- Removes `python-synthpop` from the installer, reducing bundle size.

---

## Architecture

### Current

```
ConfigTab --> run_synthesis() [Python, python-synthpop] --> progress signals --> ReportTab
```

### Proposed

```
ConfigTab --> run_synthesis_r() [Python subprocess] --> Rscript synth_worker.R
                     |                                        |
              stdout progress lines <-------------------------|
                     |
              progress signals --> ReportTab
```

Python writes a temp input CSV + JSON config, spawns Rscript, reads stdout
line-by-line for progress, then reads the output CSV when the process exits.

---

## The R script: `core/synth_worker.R`

Accepts four command-line arguments:
```
Rscript core/synth_worker.R \
  --input  /tmp/synthpop_xyz/input.csv  \
  --config /tmp/synthpop_xyz/config.json \
  --output /tmp/synthpop_xyz/output.csv
```

### Config JSON structure (written by Python)

```json
{
  "method":       "cart",
  "n_rows":       1000,
  "seed":         42,
  "variables":    ["age", "sex", "income"],
  "visit_sequence": null,
  "cart": {
    "minbucket":  5,
    "smooth":     true,
    "proper":     false
  },
  "na_strings":   ["", "NA", "N/A", "-9", "-8", "-99"]
}
```

Note: Gaussian Copula is a python-synthpop-specific method with no direct
R equivalent (see Method Mapping section below). The UI will be updated to
offer CART only when the R backend is active, or to map GC to ctree.

### R script logic

```r
library(synthpop)   # must be installed in TRE
library(jsonlite)

# 1. Parse args
args  <- commandArgs(trailingOnly = TRUE)
# ... parse --input, --config, --output ...

# 2. Load data + config
data   <- read.csv(input_path, na.strings = config$na_strings,
                   stringsAsFactors = FALSE)
data   <- data[, config$variables, drop = FALSE]

# 3. Build method vector (one per variable)
methods <- rep(config$method, ncol(data))

# 4. Run synthesis -- synthpop prints "Synthesis\n 1. varname\n 2. ..." to stdout
cat("PROGRESS:start\n"); flush(stdout())
result <- syn(
  data         = data,
  k            = config$n_rows,
  method       = methods,
  seed         = config$seed,
  minbucket    = config$cart$minbucket,
  smoothing    = if (config$cart$smooth) "density" else "",
  proper       = config$cart$proper,
  print.flag   = TRUE    # enables per-variable stdout progress
)
cat("PROGRESS:done\n"); flush(stdout())

# 5. Write output
write.csv(result$syn, output_path, row.names = FALSE, na = "")
```

---

## Progress reporting

R `synthpop` with `print.flag = TRUE` prints lines like:

```
Synthesis
 1. age
 2. sex
 3. income
...
```

Python reads subprocess stdout line-by-line in a thread and emits Qt signals:

| Stdout line | Python action |
|---|---|
| `PROGRESS:start` | Set progress bar to 5%, "Running R synthesis engine..." |
| ` 1. varname` | Increment progress: `(n / total_vars) * 90 + 5`% |
| `PROGRESS:done` | Set progress bar to 95%, "Reading results..." |
| Any other line | Log to synthesis log widget (currently hidden, could show in a details panel) |

Total variable count is known before the subprocess starts (it's in the config),
so percentage progress is accurate.

### Indeterminate fallback

If stdout parsing fails or R produces unexpected output, the progress bar falls
back to indeterminate (pulsing) mode until the process exits. This is safe and
already supported by `QProgressBar.setRange(0, 0)`.

---

## Cancellation

Replace `threading.Event` check with `process.terminate()`:

```python
def cancel(self):
    if self._proc and self._proc.poll() is None:
        self._proc.terminate()
```

On Windows, `terminate()` sends `SIGTERM`; if that doesn't stop R within 2
seconds, escalate to `kill()`. Clean up temp files in a `finally` block.

---

## Method mapping: Python options -> R synthpop

| Python config | R `syn()` parameter | Notes |
|---|---|---|
| `method = "CART"` | `method = "cart"` | Direct equivalent |
| `method = "GaussianCopula"` | `method = "ctree"` | See note below |
| `n_rows` | `k` | Direct equivalent |
| `random_state` | `seed` | Direct equivalent |
| `smoothing = True` | `smoothing = "density"` | R uses string, not bool |
| `proper = True` | `proper = TRUE` | Direct equivalent |
| `minibucket` | `minbucket` | R drops the 'i' |
| `skip_imputation` | No direct equivalent | R synthpop handles missing values internally via its own imputation; this option can be dropped |
| `enforce_min_max` | `cont.na` / post-processing | No direct R param; apply as post-processing in Python after reading output |
| `enforce_rounding` | No direct R param | Apply as post-processing in Python |
| `default_distribution` (GC only) | N/A | GC-specific, dropped if using ctree |

**Gaussian Copula note:** R `synthpop` does not include a Gaussian Copula
method. The closest R equivalent is `method = "ctree"` (conditional inference
trees), which is generally more robust than CART for mixed data types. The UI
will show a note explaining the substitution when the R backend is selected,
or the GC option can simply be hidden when R mode is active.

---

## Error handling

| Failure | Detection | User-facing message |
|---|---|---|
| R not found in PATH | `FileNotFoundError` on subprocess spawn | "R is not installed or not on PATH. Check with your TRE administrator." |
| synthpop package missing | R script exits with error containing "there is no package called 'synthpop'" | "The R synthpop package is not installed. Ask your TRE administrator to install it." |
| R script runtime error | Non-zero exit code + stderr content | Show stderr in an expandable error dialog |
| Temp file permission error | `OSError` writing input CSV | "Could not write temporary files. Check available disk space." |
| Output CSV not produced | File missing after process exits | "R synthesis completed but produced no output. Check the error log." |

All errors are caught in the worker thread and emitted as the existing
`error(str)` signal — no changes needed to the error display logic in the UI.

---

## Backend selection

Add a **Backend** radio group to the Configure tab (or a setting in a
preferences dialog), defaulting to R when R is detectable on PATH:

```python
def _detect_r() -> bool:
    import shutil
    return shutil.which("Rscript") is not None
```

| Backend | When to use |
|---|---|
| **R (recommended)** | TRE or any machine with R + synthpop installed |
| **Python** | Machines without R; development; testing |

The selected backend is stored per-session (not persisted to disk for now).
When R is selected, the Gaussian Copula method option is replaced with ctree,
and the `skip_imputation` / `enforce_min_max` / `enforce_rounding` options
are hidden or greyed out with a tooltip explaining they are Python-only.

---

## Time estimation

The current `estimate_time()` function runs a small benchmark synthesis
in Python. With the R backend this approach changes:

- **Option A (simple):** Remove the estimate button when R backend is active.
  R startup + synthpop loading alone takes ~5-10 seconds, making micro-benchmarks
  unreliable.
- **Option B:** Keep a Python-based CART estimate as a rough proxy, with a
  note that actual R time may differ.
- **Option C:** Run a small `Rscript -e "..."` inline benchmark command.

Option A is recommended initially.

---

## Files to create / modify

```
core/
    synth_worker.R          NEW  R synthesis script
    synthesis.py            MOD  add run_synthesis_r(); keep run_synthesis() as Python fallback
    synthesis_worker.py     MOD  (ui/) select backend; parse stdout progress; terminate process

ui/
    config_tab.py           MOD  add backend selector; hide Python-only options when R active;
                                 remove/disable estimate button in R mode

requirements.txt            MOD  mark python-synthpop as optional (comment it out or use extras)
packaging/
    synthpop_desktop.spec   MOD  python-synthpop submodules no longer needed if R is default
```

---

## Implementation order

1. Write and test `core/synth_worker.R` standalone (in RStudio or terminal)
   against a sample CSV — confirm it produces output and prints expected
   progress lines.

2. Write `run_synthesis_r()` in `core/synthesis.py`:
   - Write temp files
   - Spawn subprocess with stdout=PIPE
   - Read stdout in a loop, parse progress lines, call `progress_callback`
   - On process exit, read output CSV or raise error from stderr

3. Add backend detection (`_detect_r()`) and wire it into the synthesis
   worker so it calls `run_synthesis_r` or `run_synthesis` based on selection.

4. Update `ui/config_tab.py`:
   - Add backend radio buttons
   - Conditionally show/hide Python-only options
   - Handle GC -> ctree substitution

5. Test end-to-end in the TRE environment:
   - Confirm R path is found
   - Confirm synthpop package is available
   - Test with a real dataset: CART method, cancel mid-run, error cases

6. Update `requirements.txt` and PyInstaller spec to make python-synthpop
   optional (keep it for the Python fallback path).

---

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| TRE blocks subprocess spawning | Medium | Test early; if blocked, rpy2 becomes the only in-process option |
| R PATH not set in TRE desktop app context | Medium | Allow user to manually specify Rscript path in a settings dialog |
| synthpop R version differs between TREs | Low | Pin a minimum synthpop version check in the R script |
| R startup time (5-10s) frustrates users | Low | Show "Starting R..." in the progress bar immediately on click |
| Windows temp path with spaces breaks Rscript | Low | Quote all paths in subprocess call; use `tempfile.mkdtemp()` |
