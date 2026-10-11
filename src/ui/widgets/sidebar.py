"""
Sidebar navigation widget with active state styling and queue badge.
"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QButtonGroup
)
from PySide6.QtCore import Qt, Signal


class SidebarButton(QPushButton):
    """Custom styled navigation button for sidebar."""

    def __init__(self, text: str, icon: str, badge_text: str = "", parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)

        self.icon_lbl = QLabel(icon)
        self.icon_lbl.setStyleSheet("font-size: 16px; background: transparent; border: none;")

        self.text_lbl = QLabel(text)
        self.text_lbl.setStyleSheet("font-size: 13px; font-weight: 600; background: transparent; border: none;")

        self.badge_lbl = QLabel(badge_text)
        self.badge_lbl.setAlignment(Qt.AlignCenter)
        self.badge_lbl.setFixedSize(22, 20)
        self.badge_lbl.setStyleSheet("""
            background-color: #0284c7;
            color: #ffffff;
            font-size: 10px;
            font-weight: 700;
            border-radius: 10px;
            border: none;
        """)
        self.badge_lbl.setVisible(bool(badge_text))

        layout.addWidget(self.icon_lbl)
        layout.addWidget(self.text_lbl)
        layout.addStretch()
        layout.addWidget(self.badge_lbl)

        self._update_style(False)

    def set_badge(self, text: str):
        self.badge_lbl.setText(text)
        self.badge_lbl.setVisible(bool(text))

    def _update_style(self, checked: bool):
        if checked:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b;
                    border: none;
                    border-left: 3px solid #06b6d4;
                    border-radius: 0px;
                    text-align: left;
                }
            """)
            self.text_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff; background: transparent;")
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #162033;
                }
            """)
            self.text_lbl.setStyleSheet("font-size: 13px; font-weight: 500; color: #94a3b8; background: transparent;")


class AppSidebar(QFrame):
    """Sidebar containing branding, navigation menu, and version footer."""

    page_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setObjectName("sidebarFrame")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 16)
        layout.setSpacing(6)

        # App Brand Header
        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(16, 0, 16, 16)
        brand_layout.setSpacing(10)

        logo_box = QLabel("⚡")
        logo_box.setAlignment(Qt.AlignCenter)
        logo_box.setFixedSize(36, 36)
        logo_box.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0284c7, stop:1 #06b6d4);
            border-radius: 8px;
            font-size: 18px;
            color: #ffffff;
        """)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title_lbl = QLabel("Bulk MP3")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px;")
        sub_lbl = QLabel("Studio Pro")
        sub_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #06b6d4; text-transform: uppercase;")
        title_col.addWidget(title_lbl)
        title_col.addWidget(sub_lbl)

        brand_layout.addWidget(logo_box)
        brand_layout.addLayout(title_col)
        brand_layout.addStretch()

        layout.addLayout(brand_layout)

        # Section Label
        section_lbl = QLabel("  MAIN MENU")
        section_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 700; letter-spacing: 1px; margin-bottom: 4px;")
        layout.addWidget(section_lbl)

        # Nav Buttons
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.btn_dashboard = SidebarButton("Dashboard", "⚡")
        self.btn_queue = SidebarButton("Batch Queue", "📋")
        self.btn_history = SidebarButton("Job History", "🕒")
        self.btn_settings = SidebarButton("Settings", "⚙️")

        buttons = [
            (self.btn_dashboard, 0),
            (self.btn_queue, 1),
            (self.btn_history, 2),
            (self.btn_settings, 3),
        ]

        for btn, page_idx in buttons:
            self.btn_group.addButton(btn, page_idx)
            layout.addWidget(btn)
            btn.clicked.connect(lambda checked, idx=page_idx: self._on_button_clicked(idx))

        self.btn_dashboard.setChecked(True)
        self.btn_dashboard._update_style(True)

        layout.addStretch()

        # Footer
        footer_layout = QVBoxLayout()
        footer_layout.setContentsMargins(16, 0, 16, 0)
        footer_layout.setSpacing(3)

        status_tag = QLabel("● Offline Ready")
        status_tag.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 600;")
        ver_lbl = QLabel("Version 1.0.0 • Local Audio")
        ver_lbl.setStyleSheet("color: #64748b; font-size: 10px;")

        footer_layout.addWidget(status_tag)
        footer_layout.addWidget(ver_lbl)
        layout.addLayout(footer_layout)

    def _on_button_clicked(self, page_idx: int):
        for btn in [self.btn_dashboard, self.btn_queue, self.btn_history, self.btn_settings]:
            btn._update_style(btn.isChecked())
        self.page_changed.emit(page_idx)

    def set_active_page(self, page_idx: int):
        btn_map = {
            0: self.btn_dashboard,
            1: self.btn_queue,
            2: self.btn_history,
            3: self.btn_settings
        }
        target_btn = btn_map.get(page_idx)
        if target_btn:
            target_btn.setChecked(True)
            self._on_button_clicked(page_idx)

    def update_queue_badge(self, count: int):
        text = str(count) if count > 0 else ""
        self.btn_queue.set_badge(text)
