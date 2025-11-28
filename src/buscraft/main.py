import sys
from PySide6.QtWidgets import QApplication
from buscraft.gui.main_window import MainWindow
from buscraft.gui.theme import apply_dark_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("BusCraft")
    app.setOrganizationName("BusCraft")
    app.setOrganizationDomain("buscraft.local")

    apply_dark_theme(app)

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
