import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication


def _resource(relative: str) -> str:
    """Resolve a path that works both in dev and inside a PyInstaller bundle."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def _set_windows_appid():
    """Tell Windows this is a distinct app so it uses our icon in the taskbar.

    Without this, Windows groups the window under the Python interpreter and
    shows Python's icon regardless of setWindowIcon().
    """
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "SLS.SynthPop.Desktop.1"
            )
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
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
