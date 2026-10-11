"""
Dashboard metric card widget displaying key stats with icons and values.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Qt


class StatCard(QFrame):
    """Modern summary card for displaying application analytics."""

    def __init__(self, title: str, value: str = "0", icon: str = "📊", accent_color: str = "#06b6d4", parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.accent_color = accent_color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)

        # Header with icon and title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.icon_lbl = QLabel(icon)
        self.icon_lbl.setStyleSheet("font-size: 18px;")

        self.title_lbl = QLabel(title.upper())
        self.title_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;")

        header_layout.addWidget(self.icon_lbl)
        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch()

        # Value label
        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(f"""
            color: #ffffff;
            font-size: 24px;
            font-weight: 700;
        """)

        layout.addLayout(header_layout)
        layout.addWidget(self.value_lbl)

        self.setStyleSheet(f"""
            QFrame#cardFrame {{
                background-color: #141d2e;
                border: 1px solid #22314e;
                border-left: 3px solid {accent_color};
                border-radius: 8px;
            }}
        """)

    def set_value(self, value: str):
        self.value_lbl.setText(value)
