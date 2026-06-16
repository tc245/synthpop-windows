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

Requires Python 3.11+.

```bat
git clone https://github.com/tc245/synthpop-windows.git
cd synthpop-windows
setup.bat
```

Or with PowerShell:

```powershell
git clone https://github.com/tc245/synthpop-windows.git
cd synthpop-windows
.\setup.ps1
```

> **PowerShell note:** if you get a script execution policy error, run
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once first.

`setup.bat` / `setup.ps1` creates a `.venv`, installs all dependencies, and launches the app.

## Building a distributable Windows installer

All build steps must be run **on Windows** — PyInstaller bundles the platform's native libraries.

### Step 1 — install Inno Setup (one-time)

Download and install **Inno Setup 6** from https://jrsoftware.org/isdl.php. Default options are fine.

### Step 2 — build

```bat
build_installer.bat
```

Or with PowerShell:

```powershell
.\build_installer.ps1
```

This runs two steps automatically:

1. **PyInstaller** — bundles the app and all dependencies into `dist\SynthPop Desktop\`
2. **Inno Setup** — wraps that folder into a single installer executable

**Output:** `dist\installer\SynthPop_Desktop_Setup_1.0.0.exe`

The installer gives end users:
- A standard install wizard (directory choice, etc.)
- Start Menu shortcut
- Optional desktop shortcut
- A proper uninstaller in Add/Remove Programs

> **Note:** The bundle is several hundred MB due to scipy, scikit-learn, and matplotlib. This is
> normal — the installer compresses it significantly with LZMA.

### Customising before release

Edit these two lines in `packaging/installer.iss`:

```ini
#define AppPublisher "Your Organisation"
AppPublisherURL=https://github.com/tc245/synthpop-windows
```

To bump the version, update `#define AppVersion` in the same file.

## Project layout

```
synthpop-windows/
├── main.py                      # entry point
├── requirements.txt
├── setup.bat / setup.ps1        # dev setup scripts
├── build.bat / build.ps1        # PyInstaller-only build
├── build_installer.bat / .ps1   # full pipeline: PyInstaller + Inno Setup
├── core/
│   ├── data_io.py               # CSV loading, variable-type detection, sentinel detection
│   ├── synthesis.py             # synthpop wrapper, time estimator
│   └── report.py                # quality report builder + HTML renderer
├── ui/
│   ├── main_window.py           # QMainWindow, menu, tab container
│   ├── data_tab.py              # CSV open, column type table, sentinel checkboxes
│   ├── config_tab.py            # synthesis config form, progress, generate/cancel
│   ├── synthesis_worker.py      # QThread workers for synthesis and report
│   └── report_tab.py            # QTextBrowser report display
└── packaging/
    ├── synthpop_desktop.spec    # PyInstaller spec (onedir)
    └── installer.iss            # Inno Setup 6 script
```
