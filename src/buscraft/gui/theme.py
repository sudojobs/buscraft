from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


def apply_dark_theme(app: QApplication) -> None:
    palette = QPalette()

    base = QColor(30, 32, 40)
    alt_base = QColor(40, 44, 52)
    text = QColor(220, 220, 220)
    highlight = QColor(0, 188, 212)
    accent = QColor(255, 171, 64)

    palette.setColor(QPalette.Window, base)
    palette.setColor(QPalette.WindowText, text)
    palette.setColor(QPalette.Base, QColor(20, 22, 30))
    palette.setColor(QPalette.AlternateBase, alt_base)
    palette.setColor(QPalette.Text, text)
    palette.setColor(QPalette.Button, alt_base)
    palette.setColor(QPalette.ButtonText, text)
    palette.setColor(QPalette.Highlight, highlight)
    palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    palette.setColor(QPalette.Link, highlight)
    palette.setColor(QPalette.BrightText, accent)

    app.setPalette(palette)
    app.setStyle("Fusion")
