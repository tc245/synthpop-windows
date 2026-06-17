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

        IMAGE_ICON      = 1
        LR_LOADFROMFILE = 0x00000010
        WM_SETICON      = 0x0080

        hicon_small = user32.LoadImageW(None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
        hicon_large = user32.LoadImageW(None, ico_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        if hicon_small:
            user32.SendMessageW(hwnd, WM_SETICON, 0, hicon_small)  # ICON_SMALL
        if hicon_large:
            user32.SendMessageW(hwnd, WM_SETICON, 1, hicon_large)  # ICON_BIG
    except Exception:
        pass


def _make_splash_pixmap():
    """Build a branded splash-screen pixmap without needing an extra asset file."""
    from PySide6.QtCore import Qt, QRect
    from PySide6.QtGui import (
        QColor, QFont, QLinearGradient, QPainter, QPixmap, QPen,
    )

    W, H = 500, 300
    pix = QPixmap(W, H)
    pix.fill(QColor("#3d2570"))

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Gradient background: dark purple -> slightly lighter at bottom
    grad = QLinearGradient(0, 0, 0, H)
    grad.setColorAt(0.0, QColor("#3d2570"))
    grad.setColorAt(1.0, QColor("#5a3a8e"))
    p.fillRect(0, 0, W, H, grad)

    # Accent bar across the top
    p.fillRect(0, 0, W, 6, QColor("#9063CD"))

    # App title
    font_title = QFont("Arial", 30, QFont.Weight.Bold)
    p.setFont(font_title)
    p.setPen(QColor("#ffffff"))
    p.drawText(QRect(0, 60, W, 60), Qt.AlignmentFlag.AlignHCenter, "SLS SynthPop")

    # Subtitle
    font_sub = QFont("Arial", 13)
    p.setFont(font_sub)
    p.setPen(QColor("#c9b8f0"))
    p.drawText(
        QRect(0, 122, W, 30),
        Qt.AlignmentFlag.AlignHCenter,
        "Synthetic Data Generator",
    )

    # Thin divider
    p.setPen(QPen(QColor("#7a55b0"), 1))
    p.drawLine(60, 165, W - 60, 165)

    # Organisation label
    font_org = QFont("Arial", 10)
    p.setFont(font_org)
    p.setPen(QColor("#a090cc"))
    p.drawText(
        QRect(0, 175, W, 24),
        Qt.AlignmentFlag.AlignHCenter,
        "Scottish Longitudinal Study Development and Support Unit",
    )

    # Status message area (bottom strip)
    p.fillRect(0, H - 40, W, 40, QColor("#2a1850"))

    p.end()
    return pix


def _splash_msg(splash, msg: str):
    """Update splash message and force a repaint before blocking work."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor
    splash.showMessage(
        msg,
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
        QColor("#c9b8f0"),
    )
    QApplication.processEvents()


def main():
    _set_windows_appid()

    app = QApplication(sys.argv)
    app.setApplicationName("SLS Synthetic Data Generator")
    app.setOrganizationName("SLS-DSU")

    # Show splash before any heavy imports so the user sees something immediately
    from PySide6.QtWidgets import QSplashScreen
    splash = QSplashScreen(_make_splash_pixmap())
    splash.show()
    _splash_msg(splash, "Starting up...")

    # Prefer .ico on Windows (contains multiple sizes); fall back to .png
    ico_path = _resource(os.path.join("assets", "icon.ico"))
    png_path = _resource(os.path.join("assets", "icon.png"))
    icon_path = ico_path if os.path.exists(ico_path) else png_path
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    _splash_msg(splash, "Loading synthesis engine...")
    from core.synthesis import _patch_synthpop
    _patch_synthpop()

    _splash_msg(splash, "Loading interface...")
    from ui.style import APP_QSS
    app.setStyleSheet(APP_QSS)

    from ui.main_window import MainWindow
    window = MainWindow()

    # splash.finish() waits for the main window to appear before closing
    window.show()
    splash.finish(window)

    if sys.platform == "win32" and os.path.exists(ico_path):
        _set_win32_icon(int(window.winId()), ico_path)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
