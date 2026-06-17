# SynthPop Desktop — Linux Port Plan

Target: produce a Linux build of the same PySide6 desktop app that currently
ships as a Windows `.exe` installer, distributed as an **AppImage** (single
portable file, runs on any modern Linux distro without installation).

---

## What already works without changes

All of the core logic and UI is cross-platform:

- PySide6, QPdfWriter, QTextBrowser, all Qt widgets
- pandas, scipy, scikit-learn, python-synthpop, matplotlib
- openpyxl (Excel export)
- File dialogs, tab layout, report rendering
- All Windows-specific `ctypes` calls in `main.py` are already guarded by
  `sys.platform == "win32"` and silently skip on Linux

The app can already be run from source on Linux with no code changes:
```
pip install -r requirements.txt
python main.py
```

---

## Changes required

### 1. PyInstaller spec — Linux variant

Create `packaging/synthpop_desktop_linux.spec` alongside the existing Windows
spec. Key differences from the Windows spec:

| Item | Windows spec | Linux spec |
|---|---|---|
| Icon in datas | `icon.ico` + `icon.png` | `icon.png` only |
| EXE `icon=` | `assets/icon.ico` | not set (N/A on Linux) |
| `console=False` | hides console window | keep False (spawns detached) |
| Hidden imports | same set | same set — add `fonttools` if weasyprint is ever re-added |
| Output name | `SynthPop Desktop` | `SynthPop_Desktop` (no space — easier for shell) |

The `collect_submodules` / `collect_data_files` calls for scipy, sklearn,
synthpop, openpyxl are identical on both platforms.

### 2. Desktop integration file

Create `packaging/synthpop-desktop.desktop` for GNOME/KDE/XFCE app menus:

```ini
[Desktop Entry]
Type=Application
Name=SLS SynthPop Desktop
Comment=Synthetic data generator for the Scottish Longitudinal Study
Exec=AppRun
Icon=synthpop
Categories=Science;Education;
Terminal=false
```

This file is embedded in the AppImage and registered with the system when the
user runs the AppImage with `--install` (via `appimage-installer`) or manually
copies it to `~/.local/share/applications/`.

### 3. AppImage build script

Create `build_linux.sh` (ASCII only, no fancy Unicode) to run on the build
machine or CI runner:

```bash
#!/usr/bin/env bash
set -euo pipefail

# 1. Build with PyInstaller
pyinstaller packaging/synthpop_desktop_linux.spec

# 2. Lay out the AppDir structure
APPDIR="dist/SynthPop_Desktop.AppDir"
mkdir -p "$APPDIR/usr/bin"
cp -r "dist/SynthPop_Desktop/." "$APPDIR/usr/bin/"
cp assets/icon.png "$APPDIR/synthpop.png"
cp packaging/synthpop-desktop.desktop "$APPDIR/synthpop-desktop.desktop"

# 3. AppRun entry point
cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/SynthPop_Desktop" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# 4. Package into AppImage
appimagetool "$APPDIR" "dist/SynthPop_Desktop_$(uname -m).AppImage"
```

`appimagetool` must be installed on the build machine
(download from https://github.com/AppImage/appimagetool/releases).

---

## Packaging format decision

**Recommended: AppImage**

| Format | Pros | Cons |
|---|---|---|
| **AppImage** | Single file, no install, no root, runs on any distro | No auto-update, user must make executable |
| `.deb` | Integrates with apt, package manager handles updates | Ubuntu/Debian only |
| Flatpak | Cross-distro, sandboxed, Flathub listing possible | Most setup work, sandboxing may restrict file access |
| PyInstaller onedir (zip/tar) | Simplest to produce | No desktop integration, user must unpack and run |

AppImage matches the Windows experience (single file, double-click to run)
most closely. It can be revisited in favour of Flatpak later if Flathub
distribution becomes a goal.

---

## Build environment

The PyInstaller bundle must be built **on Linux** — it cannot be
cross-compiled from Windows. Options:

### Option A: Local Linux machine / WSL2
Run `build_linux.sh` directly on a local Linux install or WSL2 Ubuntu.
WSL2 can produce a working Linux binary; test in a clean VM or Docker
container before releasing.

### Option B: GitHub Actions (recommended for repeatability)

Add a second job to `.github/workflows/build.yml` (create the file if it
does not yet exist) using an `ubuntu-latest` runner:

```yaml
jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt
      - run: pyinstaller packaging\synthpop_desktop.spec
      - run: iscc packaging\installer.iss   # if Inno Setup is available
      - uses: actions/upload-artifact@v4
        with:
          name: windows-installer
          path: dist/installer/*.exe

  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install system deps for PySide6
        run: |
          sudo apt-get update
          sudo apt-get install -y libgl1 libglib2.0-0 libxcb-cursor0 \
            libxkbcommon-x11-0 libdbus-1-3 libegl1
      - run: pip install -r requirements.txt appimagetool-installer
      - run: bash build_linux.sh
      - uses: actions/upload-artifact@v4
        with:
          name: linux-appimage
          path: dist/*.AppImage
```

The key `apt-get` packages above are shared libraries that PySide6 links
against but that are not bundled by PyInstaller on Linux.

---

## Potential issues to watch for

| Risk | Mitigation |
|---|---|
| PySide6 xcb platform plugin missing at runtime | Add `collect_data_files("PySide6")` or explicitly include `libqxcb.so` in the spec |
| `libGL` not found on headless CI runner | Install `libgl1-mesa-glx` or `libopengl0` in the CI step |
| Font rendering differences | Test on clean Ubuntu VM; matplotlib uses its own bundled fonts so report heatmap should be fine |
| synthpop / sklearn compiled extensions | `collect_submodules` handles these; test with `ldd` on the bundled binary |
| AppImage not executable after download | Add a note in the README: `chmod +x SynthPop_Desktop_x86_64.AppImage` |
| File dialog uses native GTK/KDE portal | Usually works; if not, set `QT_QPA_PLATFORMTHEME=""` in AppRun |

---

## Implementation steps (in order)

1. **Verify the app runs from source on Linux** — `pip install -r requirements.txt && python main.py` on Ubuntu 22.04.
2. **Create `packaging/synthpop_desktop_linux.spec`** — copy Windows spec, adjust icon/name.
3. **Run PyInstaller on Linux** — fix any missing hidden imports or data files until the bundle launches.
4. **Create `packaging/synthpop-desktop.desktop`** and `build_linux.sh`.
5. **Install `appimagetool`** and produce a test AppImage locally.
6. **Test the AppImage** on a clean Ubuntu VM (no Python installed) to confirm all dependencies are bundled.
7. **Add GitHub Actions workflow** for automated builds on push/tag.
8. **Update `README.md`** with Linux install instructions.

---

## Files to create

```
packaging/
    synthpop_desktop_linux.spec     # PyInstaller spec for Linux
    synthpop-desktop.desktop        # .desktop entry for app menus
build_linux.sh                      # build + AppImage packaging script
.github/
    workflows/
        build.yml                   # CI: Windows + Linux jobs
```
