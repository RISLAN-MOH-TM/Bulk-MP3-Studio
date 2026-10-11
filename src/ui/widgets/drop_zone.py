"""
Drag and Drop zone widget for selecting local media files.
"""

from pathlib import Path
from typing import List
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton, QFileDialog
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from src.validator import SUPPORTED_LOCAL_EXTENSIONS


class DropZone(QFrame):
    """Modern drag & drop area with dashed border and file picker."""

    files_selected = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        icon_lbl = QLabel("📂")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 26px;")

        self.main_text = QLabel("Drag & Drop Local Audio / Video Files Here")
        self.main_text.setAlignment(Qt.AlignCenter)
        self.main_text.setStyleSheet("font-weight: 700; font-size: 13px; color: #f8fafc;")

        sub_text = QLabel("Supports WAV, MP4, M4A, FLAC, OGG, AAC, WEBM, MKV, MP3 and more")
        sub_text.setAlignment(Qt.AlignCenter)
        sub_text.setStyleSheet("font-size: 11px; color: #94a3b8;")

        self.browse_btn = QPushButton("Browse Local Files")
        self.browse_btn.setFixedWidth(160)
        self.browse_btn.clicked.connect(self._on_browse_clicked)

        layout.addWidget(icon_lbl)
        layout.addWidget(self.main_text)
        layout.addWidget(sub_text)
        layout.addWidget(self.browse_btn, 0, Qt.AlignCenter)

        self._set_normal_style()

    def _set_normal_style(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #101827;
                border: 2px dashed #22314e;
                border-radius: 8px;
            }
            QFrame:hover {
                border-color: #0284c7;
                background-color: #131f35;
            }
        """)

    def _set_drag_active_style(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #162a4a;
                border: 2px dashed #38bdf8;
                border-radius: 8px;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_drag_active_style()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._set_normal_style()

    def dropEvent(self, event: QDropEvent):
        self._set_normal_style()
        urls = event.mimeData().urls()
        files = []
        for u in urls:
            local_path = u.toLocalFile()
            if local_path and Path(local_path).is_file():
                files.append(local_path)
            elif local_path and Path(local_path).is_dir():
                # Recursively add supported files if folder dropped
                for f in Path(local_path).rglob("*"):
                    if f.is_file() and f.suffix.lower() in SUPPORTED_LOCAL_EXTENSIONS:
                        files.append(str(f))

        if files:
            self.files_selected.emit(files)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_browse_clicked()

    def _on_browse_clicked(self):
        ext_filter = "Media Files (*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.wma *.mp4 *.mkv *.avi *.mov *.webm *.flv);;All Files (*.*)"
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio / Video Files for Conversion",
            "",
            ext_filter
        )
        if files:
            self.files_selected.emit(files)
