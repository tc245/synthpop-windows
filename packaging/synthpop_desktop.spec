# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for SynthPop Desktop — onedir build (recommended over onefile
# due to large scipy/sklearn/matplotlib bundle size).
#
# Build (must run on Windows):
#   pyinstaller packaging/synthpop_desktop.spec

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent   # synthpop-windows/

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # scipy internals
        "scipy._lib.array_api_compat.numpy",
        "scipy.special._cdflib",
        "scipy.stats._stats",
        # sklearn internals
        "sklearn.utils._typedefs",
        "sklearn.utils._heap",
        "sklearn.utils._sorting",
        "sklearn.utils._vector_sentinel",
        "sklearn.neighbors.typedefs",
        "sklearn.neighbors._partition_nodes",
        "sklearn.tree._classes",
        "sklearn.tree._criterion",
        "sklearn.tree._splitter",
        "sklearn.tree._utils",
        # matplotlib
        "matplotlib.backends.backend_agg",
        # synthpop
        "synthpop",
        "synthpop.processor.data_processor",
        "synthpop.method.cart",
        "synthpop.method.gaussian_copula",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "PyQt5",
        "PyQt6",
    ],
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
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SynthPop Desktop",
)
