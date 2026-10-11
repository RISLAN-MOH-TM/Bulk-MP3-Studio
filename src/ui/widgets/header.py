"""
Top application header with view title, system status pills, and quick directory access.
"""

from pathlib import Path
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal

from src.utils import open_folder_and_select


class AppHeader(QFrame):
    """Header bar with active view title and dynamic status pills."""

    open_output_folder_clicked = Signal()
    settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setStyleSheet("""
            QFrame {
                background-color: #0d1322;
                border-bottom: 1px solid #1e293b;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(14)

        # Title / Breadcrumb
        self.title_lbl = QLabel("Dashboard")
        self.title_lbl.setStyleSheet("""
            font-size: 17px;
            font-weight: 700;
            color: #ffffff;
        """)
        layout.addWidget(self.title_lbl)

        layout.addStretch()

        # Queue Status Pill
        self.queue_pill = QLabel("Queue: Empty")
        self.queue_pill.setStyleSheet("""
            background-color: rgba(99, 102, 241, 0.15);
            color: #818cf8;
            border: 1px solid #4f46e5;
            border-radius: 12px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 600;
        """)
        layout.addWidget(self.queue_pill)

        # FFmpeg Status Pill (clickable to jump to settings)
        self.ffmpeg_btn = QPushButton("Checking FFmpeg...")
        self.ffmpeg_btn.setCursor(Qt.PointingHandCursor)
        self.ffmpeg_btn.clicked.connect(self.settings_requested.emit)
        layout.addWidget(self.ffmpeg_btn)

        # Output Folder Quick Button
        self.output_btn = QPushButton("📁 Output Folder")
        self.output_btn.setToolTip("Open destination output folder in File Explorer")
        self.output_btn.setCursor(Qt.PointingHandCursor)
        self.output_btn.clicked.connect(self.open_output_folder_clicked.emit)
        self.output_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #27354f;
                color: #f8fafc;
                border-color: #06b6d4;
            }
        """)
        layout.addWidget(self.output_btn)

    def set_view_title(self, title: str):
        self.title_lbl.setText(title)

    def set_queue_status(self, text: str):
        self.queue_pill.setText(text)

    def set_ffmpeg_status(self, is_available: bool, version_info: str = ""):
        if is_available:
            self.ffmpeg_btn.setText("⚡ FFmpeg Ready")
            self.ffmpeg_btn.setToolTip(f"FFmpeg is configured and active:\n{version_info}")
            self.ffmpeg_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(16, 185, 129, 0.15);
                    color: #34d399;
                    border: 1px solid #059669;
                    border-radius: 12px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(16, 185, 129, 0.3);
                }
            """)
        else:
            self.ffmpeg_btn.setText("⚠️ FFmpeg Missing")
            self.ffmpeg_btn.setToolTip("Click to configure FFmpeg in Settings")
            self.ffmpeg_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(239, 68, 68, 0.15);
                    color: #f87171;
                    border: 1px solid #dc2626;
                    border-radius: 12px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(239, 68, 68, 0.3);
                }
            """)
