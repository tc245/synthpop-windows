import sys

from PySide6.QtWidgets import QApplication


def main():
    from core.synthesis import _patch_synthpop
    _patch_synthpop()

    app = QApplication(sys.argv)
    app.setApplicationName("SLS Synthetic Data Generator")
    app.setOrganizationName("SLS-DSU")

    from ui.style import APP_QSS
    app.setStyleSheet(APP_QSS)

    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
