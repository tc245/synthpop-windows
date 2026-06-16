# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for SynthPop Desktop — Windows onedir build.
#
# Run from the project root:
#   pyinstaller packaging\synthpop_desktop.spec

from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

ROOT = Path(SPECPATH).parent   # synthpop-windows\

# Collect all submodules so PyInstaller doesn't miss compiled .pyd extensions
hidden = (
    collect_submodules("scipy")
    + collect_submodules("sklearn")
    + collect_submodules("synthpop")
    + [
        "matplotlib.backends.backend_agg",
        "pandas._libs.tslibs.base",
    ]
)

# Collect data files (matplotlib fonts, scipy data, etc.)
datas = (
    collect_data_files("matplotlib")
    + collect_data_files("scipy")
    + [(str(ROOT / "assets" / "icon.png"), "assets")]
)

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PyQt5", "PyQt6"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SynthPop Desktop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX off — causes false-positive AV alerts on Windows
    console=False,      # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SynthPop Desktop",
)
