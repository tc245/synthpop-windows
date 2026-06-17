import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication


def _resource(relative: str) -> str:
    """Resolve a path that works both in dev and inside a PyInstaller bundle."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def _set_windows_appid():
    """Tell Windows this is a distinct app, not the Python interpreter."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "SLS.SynthPop.Desktop.1"
            )
        except Exception:
            pass


def _set_win32_icon(hwnd, ico_path: str):
    """Send WM_SETICON directly to the window handle for reliable taskbar icon.

    Specifies explicit ctypes argtypes so HICON handles are not truncated
    to 32-bit on 64-bit Windows.  Loads separate handles at 16 px (taskbar)
    and 32 px (alt-tab) because Windows uses different slots for each.
    """
    try:
        import ctypes
        import ctypes.wintypes as wt

        user32 = ctypes.windll.user32
        user32.LoadImageW.restype = ctypes.c_void_p
        user32.LoadImageW.argtypes = [
            wt.HANDLE, wt.LPCWSTR, wt.UINT, ctypes.c_int, ctypes.c_int, wt.UINT,
        ]
        user32.SendMessageW.restype = ctypes.c_void_p
        user32.SendMessageW.argtypes = [
            wt.HWND, wt.UINT, wt.WPARAM, ctypes.c_void_p,
        ]

        IMAGE_ICON    = 1
        LR_LOADFROMFILE = 0x00000010
        WM_SETICON    = 0x0080

        hicon_small = user32.LoadImageW(None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
        hicon_large = user32.LoadImageW(None, ico_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        if hicon_small:
            user32.SendMessageW(hwnd, WM_SETICON, 0, hicon_small)  # ICON_SMALL
        if hicon_large:
            user32.SendMessageW(hwnd, WM_SETICON, 1, hicon_large)  # ICON_BIG
    except Exception:
        pass


def main():
    _set_windows_appid()

    from core.synthesis import _patch_synthpop
    _patch_synthpop()

    app = QApplication(sys.argv)
    app.setApplicationName("SLS Synthetic Data Generator")
    app.setOrganizationName("SLS-DSU")

    # Prefer .ico on Windows (contains multiple sizes); fall back to .png
    ico_path = _resource(os.path.join("assets", "icon.ico"))
    png_path = _resource(os.path.join("assets", "icon.png"))
    icon_path = ico_path if os.path.exists(ico_path) else png_path
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    from ui.style import APP_QSS
    app.setStyleSheet(APP_QSS)

    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    # Push icon directly to the Win32 window handle — setWindowIcon alone
    # doesn't always update the taskbar button when running under Python.
    if sys.platform == "win32" and os.path.exists(ico_path):
        _set_win32_icon(int(window.winId()), ico_path)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
