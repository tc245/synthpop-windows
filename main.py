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
    """Send WM_SETICON directly to the window handle for reliable taskbar icon."""
    try:
        import ctypes
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        LR_DEFAULTSIZE = 0x00000040
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1

        hicon = ctypes.windll.user32.LoadImageW(
            None, ico_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE
        )
        if hicon:
            send = ctypes.windll.user32.SendMessageW
            send(hwnd, WM_SETICON, ICON_SMALL, hicon)
            send(hwnd, WM_SETICON, ICON_BIG, hicon)
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
