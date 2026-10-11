"""
Modern status badge / chip widget for job status and source types.
"""

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt


class StatusBadge(QLabel):
    """Sleek colored badge for displaying item status."""

    STYLES = {
        "PENDING": ("#94a3b8", "rgba(148, 163, 184, 0.15)", "Waiting"),
        "DOWNLOADING": ("#38bdf8", "rgba(56, 189, 248, 0.15)", "Downloading"),
        "CONVERTING": ("#06b6d4", "rgba(6, 182, 212, 0.20)", "Converting"),
        "COMPLETED": ("#10b981", "rgba(16, 185, 129, 0.20)", "Completed"),
        "FAILED": ("#ef4444", "rgba(239, 68, 68, 0.20)", "Failed"),
        "CANCELLED": ("#64748b", "rgba(100, 116, 139, 0.20)", "Cancelled"),
        # Source Types
        "URL": ("#a855f7", "rgba(168, 85, 247, 0.15)", "Web URL"),
        "LOCAL_FILE": ("#3b82f6", "rgba(59, 130, 246, 0.15)", "Local File"),
    }

    def __init__(self, status_key: str = "PENDING", custom_text: str = None, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(24)
        self.set_status(status_key, custom_text)

    def set_status(self, status_key: str, custom_text: str = None):
        key = status_key.upper()
        fg, bg, label = self.STYLES.get(key, ("#94a3b8", "rgba(148, 163, 184, 0.15)", key))
        text = custom_text or label

        self.setText(text)
        self.setStyleSheet(f"""
            QLabel {{
                color: {fg};
                background-color: {bg};
                border: 1px solid {fg};
                border-radius: 12px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)
