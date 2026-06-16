# SynthPop Desktop

A standalone Windows desktop application for generating synthetic data from CSV files.
Ported from the [SLS-SDC-Dashboard](../SLS-SDC-Dashboard) Flask web application.

**Workflow:** Open CSV → classify variable types → configure synthesis → generate → review quality report → export.

No database, no authentication, no network — all local.

## Features

- CART and Gaussian Copula synthesis methods (via `python-synthpop`)
- Automatic variable-type detection (categorical / numeric) with manual override
- Sentinel missing-value detection and recoding
- Time estimate before full synthesis run
- Live progress log during generation with cancel support
- Quality report: numeric summary, KS tests, chi-squared tests, correlation heatmap
- Export synthetic CSV and/or HTML report

## Dev setup

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

Requires Python 3.11+.

## Windows build (PyInstaller)

The `.exe` must be built **on Windows** (PyInstaller bundles the platform's native libraries).

```bash
pip install -r requirements.txt
pyinstaller packaging/synthpop_desktop.spec
```

Output is in `dist/SynthPop Desktop/`. The directory contains the `.exe` plus all runtime
dependencies. Distribute the entire directory (or zip it).

> **Note:** The bundle will be several hundred MB due to scipy, scikit-learn, and matplotlib.
> The onedir build is recommended over onefile for faster startup and easier antivirus compatibility.

## Project layout

```
synthpop-windows/
├── main.py                  # entry point
├── requirements.txt
├── core/
│   ├── data_io.py           # CSV loading, variable-type detection, sentinel detection
│   ├── synthesis.py         # synthpop wrapper, time estimator
│   └── report.py            # quality report builder + HTML renderer
├── ui/
│   ├── main_window.py       # QMainWindow, menu, tab container
│   ├── data_tab.py          # CSV open, column type table, sentinel checkboxes
│   ├── config_tab.py        # synthesis config form, progress, generate/cancel
│   ├── synthesis_worker.py  # QThread workers for synthesis and report
│   └── report_tab.py        # QTextBrowser report display
└── packaging/
    └── synthpop_desktop.spec  # PyInstaller spec (onedir)
```
