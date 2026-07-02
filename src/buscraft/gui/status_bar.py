"""Custom status bar — project info, license badge, and Generate CTA button.

Sits at the bottom of the main window, always visible.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, Signal

from buscraft.gui.theme import C, Fonts


class StatusBar(QWidget):
    """Bottom status bar with project info and Generate button."""

    generate_clicked = Signal()

    HEIGHT = 40

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("appStatusBar")
        self.setFixedHeight(self.HEIGHT)
        self.setStyleSheet(f"""
            QWidget#appStatusBar {{
                background: {C.BG_DARKEST};
                border-top: 1px solid {C.BORDER};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(16)

        # Project name
        self.lbl_project = QLabel("No Project")
        self.lbl_project.setStyleSheet(f"""
            color: {C.TEXT_MUTED};
            font-size: {Fonts.SMALL}px;
            font-weight: 500;
        """)
        layout.addWidget(self.lbl_project)

        # Agent count badge
        self.lbl_agents = QLabel("")
        self.lbl_agents.setStyleSheet(f"""
            color: {C.TEXT_DIM};
            font-size: {Fonts.TINY}px;
            background: {C.BG_SURFACE};
            border-radius: 8px;
            padding: 2px 10px;
        """)
        self.lbl_agents.setVisible(False)
        layout.addWidget(self.lbl_agents)

        layout.addStretch()

        # License badge
        self.lbl_license = QLabel("Demo")
        self.lbl_license.setStyleSheet(f"""
            color: {C.WARNING};
            font-size: {Fonts.SMALL}px;
            font-weight: 500;
        """)
        layout.addWidget(self.lbl_license)

        # Separator
        sep = QWidget()
        sep.setFixedWidth(1)
        sep.setFixedHeight(20)
        sep.setStyleSheet(f"background: {C.BORDER};")
        layout.addWidget(sep)

        # Generate CTA
        self.btn_generate = QPushButton("Generate")
        self.btn_generate.setObjectName("generateCTA")
        self.btn_generate.setCursor(Qt.PointingHandCursor)
        self.btn_generate.clicked.connect(self.generate_clicked.emit)
        layout.addWidget(self.btn_generate)

    def set_project_info(self, name: str, agent_count: int = 0):
        """Update the project name and agent count display."""
        self.lbl_project.setText(f"{name}")
        if agent_count > 0:
            self.lbl_agents.setText(f"{agent_count} agent{'s' if agent_count != 1 else ''}")
            self.lbl_agents.setVisible(True)
        else:
            self.lbl_agents.setVisible(False)

    def set_license_info(self, customer: str, is_valid: bool = True):
        """Update the license badge."""
        if customer == "DEMO_USER":
            self.lbl_license.setText("Demo License")
            self.lbl_license.setStyleSheet(f"""
                color: {C.WARNING};
                font-size: {Fonts.SMALL}px;
                font-weight: 500;
            """)
        elif is_valid:
            self.lbl_license.setText(f"{customer}")
            self.lbl_license.setStyleSheet(f"""
                color: {C.SUCCESS};
                font-size: {Fonts.SMALL}px;
                font-weight: 500;
            """)
        else:
            self.lbl_license.setText("Invalid License")
            self.lbl_license.setStyleSheet(f"""
                color: {C.ERROR};
                font-size: {Fonts.SMALL}px;
                font-weight: 500;
            """)

    def clear(self):
        """Reset to no-project state."""
        self.lbl_project.setText("No Project")
        self.lbl_agents.setVisible(False)
