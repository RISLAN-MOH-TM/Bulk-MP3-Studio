"""
Dashboard View for Bulk MP3 Studio.
Features quick analytics cards, multiline URL ingestion, TXT file import,
local file drag & drop, bitrate preset selectors with output size estimation,
and batch queue submission.
"""

from pathlib import Path
from typing import List, Set
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QFrame, QFileDialog, QMessageBox, QRadioButton, QButtonGroup,
    QLineEdit, QScrollArea
)
from PySide6.QtCore import Qt, Signal

from src.config import ConfigManager, BITRATE_PRESETS
from src.database import DatabaseManager
from src.queue_manager import QueueManager, QueueItem
from src.ui.widgets.drop_zone import DropZone
from src.ui.widgets.stat_card import StatCard
from src.utils import format_bytes, open_folder_and_select
from src.validator import (
    InputValidator,
    parse_multiline_inputs,
    parse_txt_file,
    detect_duplicates,
    ValidationResult
)


class DashboardView(QWidget):
    """Main dashboard page for input aggregation, preset tuning, and job creation."""

    start_conversion_requested = Signal()
    view_queue_requested = Signal()

    def __init__(self, queue_mgr: QueueManager, config_mgr: ConfigManager, parent=None):
        super().__init__(parent)
        self.queue_mgr = queue_mgr
        self.config_mgr = config_mgr
        self.staged_local_files: List[str] = []

        self._build_ui()
        self.refresh_stats()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(20)

        # 1. Top Analytics Stats Cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        self.card_completed = StatCard("Completed Jobs", "0", "✅", "#10b981")
        self.card_storage = StatCard("Storage Converted", "0 MB", "💾", "#06b6d4")
        self.card_active = StatCard("Queue Items", "0", "📋", "#818cf8")
        self.card_failed = StatCard("Failed Jobs", "0", "⚠️", "#ef4444")

        stats_layout.addWidget(self.card_completed)
        stats_layout.addWidget(self.card_storage)
        stats_layout.addWidget(self.card_active)
        stats_layout.addWidget(self.card_failed)
        main_layout.addLayout(stats_layout)

        # 2. Split Workspace (Left: Input Sources, Right: Quality & Settings)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # LEFT COLUMN: Source Input Manager
        left_card = QFrame()
        left_card.setObjectName("cardFrame")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(20, 18, 20, 18)
        left_layout.setSpacing(14)

        # Section Header
        left_header = QVBoxLayout()
        left_header.setSpacing(2)
        lh_title = QLabel("Source Input Manager")
        lh_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        lh_sub = QLabel("Paste permitted media URLs or import authorized local media files")
        lh_sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        left_header.addWidget(lh_title)
        left_header.addWidget(lh_sub)
        left_layout.addLayout(left_header)

        # URL Input Text Area
        url_label = QLabel("Video & Media URLs (one per line):")
        url_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #cbd5e1;")
        left_layout.addWidget(url_label)

        self.url_text_edit = QTextEdit()
        self.url_text_edit.setPlaceholderText(
            "Paste video or media URLs here, one per line...\n\n"
            "Supported platforms: YouTube, Vimeo, SoundCloud, TikTok, Instagram,\n"
            "direct MP3/MP4/WAV web links, podcasts, Archive.org, and 1000+ more.\n\n"
            "Tip: For YouTube, add your cookies.txt in Settings for best results."
        )
        self.url_text_edit.setMinimumHeight(140)
        left_layout.addWidget(self.url_text_edit)

        # URL Action Buttons
        url_btn_row = QHBoxLayout()
        url_btn_row.setSpacing(10)

        self.btn_import_txt = QPushButton("📄 Import .TXT List")
        self.btn_import_txt.setCursor(Qt.PointingHandCursor)
        self.btn_import_txt.clicked.connect(self._on_import_txt_clicked)

        self.btn_clear_urls = QPushButton("Clear URLs")
        self.btn_clear_urls.setCursor(Qt.PointingHandCursor)
        self.btn_clear_urls.clicked.connect(self.url_text_edit.clear)

        url_btn_row.addWidget(self.btn_import_txt)
        url_btn_row.addWidget(self.btn_clear_urls)
        url_btn_row.addStretch()
        left_layout.addLayout(url_btn_row)

        # Local Media Drop Zone
        local_label = QLabel("Or Select Local Media Files:")
        local_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #cbd5e1; margin-top: 6px;")
        left_layout.addWidget(local_label)

        self.drop_zone = DropZone()
        self.drop_zone.files_selected.connect(self._on_local_files_added)
        left_layout.addWidget(self.drop_zone)

        # Staged Local Files Counter
        self.local_files_summary_lbl = QLabel("No local files selected.")
        self.local_files_summary_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
        left_layout.addWidget(self.local_files_summary_lbl)

        content_layout.addWidget(left_card, 6)

        # RIGHT COLUMN: Audio Quality Presets & Output Settings
        right_card = QFrame()
        right_card.setObjectName("cardFrame")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(20, 18, 20, 18)
        right_layout.setSpacing(16)

        right_header = QVBoxLayout()
        right_header.setSpacing(2)
        rh_title = QLabel("Audio Settings & Output")
        rh_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        rh_sub = QLabel("Select low-MB MP3 bitrate preset and destination folder")
        rh_sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        right_header.addWidget(rh_title)
        right_header.addWidget(rh_sub)
        right_layout.addLayout(right_header)

        # Presets Section
        presets_label = QLabel("LOW-MB BITRATE PRESETS:")
        presets_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px;")
        right_layout.addWidget(presets_label)

        self.preset_group = QButtonGroup(self)
        self.preset_radios = {}

        current_default_bitrate = self.config_mgr.settings.default_bitrate

        presets_container = QVBoxLayout()
        presets_container.setSpacing(8)

        for p in BITRATE_PRESETS:
            kbps = p["bitrate"]
            radio = QRadioButton(f"{p['label']} — {p['description']}")
            radio.setCursor(Qt.PointingHandCursor)
            radio.setStyleSheet("""
                QRadioButton {
                    color: #e2e8f0;
                    font-size: 12px;
                    spacing: 8px;
                    padding: 4px;
                }
                QRadioButton::indicator {
                    width: 16px;
                    height: 16px;
                }
                QRadioButton::indicator:checked {
                    background-color: #06b6d4;
                    border: 2px solid #ffffff;
                    border-radius: 8px;
                }
                QRadioButton::indicator:unchecked {
                    background-color: #1e293b;
                    border: 2px solid #475569;
                    border-radius: 8px;
                }
            """)
            if kbps == current_default_bitrate:
                radio.setChecked(True)
            self.preset_group.addButton(radio, kbps)
            self.preset_radios[kbps] = radio
            presets_container.addWidget(radio)

        self.preset_group.idToggled.connect(self._on_preset_toggled)
        right_layout.addLayout(presets_container)

        # Output Size Estimation Display
        self.size_estimate_box = QFrame()
        self.size_estimate_box.setStyleSheet("""
            background-color: rgba(6, 182, 212, 0.08);
            border: 1px solid rgba(6, 182, 212, 0.25);
            border-radius: 6px;
            padding: 8px;
        """)
        estimate_layout = QHBoxLayout(self.size_estimate_box)
        estimate_layout.setContentsMargins(10, 6, 10, 6)
        self.size_est_lbl = QLabel()
        self.size_est_lbl.setStyleSheet("font-size: 12px; color: #38bdf8; font-weight: 600;")
        estimate_layout.addWidget(self.size_est_lbl)
        right_layout.addWidget(self.size_estimate_box)
        self._update_estimate_label(current_default_bitrate)

        # Output Folder Section
        folder_label = QLabel("OUTPUT DESTINATION:")
        folder_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px; margin-top: 8px;")
        right_layout.addWidget(folder_label)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)

        self.output_path_input = QLineEdit(self.config_mgr.settings.output_directory)
        self.output_path_input.setReadOnly(True)
        self.output_path_input.setStyleSheet("font-size: 12px;")

        self.btn_browse_folder = QPushButton("Browse...")
        self.btn_browse_folder.setCursor(Qt.PointingHandCursor)
        self.btn_browse_folder.clicked.connect(self._on_browse_output_folder)

        self.btn_open_folder = QPushButton("Open")
        self.btn_open_folder.setToolTip("Open output directory in File Explorer")
        self.btn_open_folder.setCursor(Qt.PointingHandCursor)
        self.btn_open_folder.clicked.connect(self._on_open_output_folder)

        folder_row.addWidget(self.output_path_input)
        folder_row.addWidget(self.btn_browse_folder)
        folder_row.addWidget(self.btn_open_folder)
        right_layout.addLayout(folder_row)

        right_layout.addStretch()

        # Batch Action Buttons
        action_layout = QVBoxLayout()
        action_layout.setSpacing(10)

        self.btn_add_to_queue = QPushButton("➕ Add to Queue")
        self.btn_add_to_queue.setFixedHeight(40)
        self.btn_add_to_queue.setCursor(Qt.PointingHandCursor)
        self.btn_add_to_queue.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #38bdf8;
                color: #38bdf8;
                font-weight: 700;
                font-size: 13px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.15);
            }
        """)
        self.btn_add_to_queue.clicked.connect(lambda: self._process_and_add(start_immediately=False))

        self.btn_convert_now = QPushButton("⚡ Add & Start Conversion")
        self.btn_convert_now.setObjectName("primaryBtn")
        self.btn_convert_now.setFixedHeight(42)
        self.btn_convert_now.setCursor(Qt.PointingHandCursor)
        self.btn_convert_now.setStyleSheet("""
            font-size: 14px;
            font-weight: 700;
            border-radius: 6px;
        """)
        self.btn_convert_now.clicked.connect(lambda: self._process_and_add(start_immediately=True))

        action_layout.addWidget(self.btn_add_to_queue)
        action_layout.addWidget(self.btn_convert_now)
        right_layout.addLayout(action_layout)

        content_layout.addWidget(right_card, 5)

        main_layout.addLayout(content_layout)

    def _on_preset_toggled(self, radio_id: int, checked: bool):
        if checked:
            self.config_mgr.settings.default_bitrate = radio_id
            self.config_mgr.save()
            self._update_estimate_label(radio_id)

    def _update_estimate_label(self, bitrate_kbps: int):
        # 5 minute estimate
        mb_5min = self.config_mgr.estimate_file_size_mb(300, bitrate_kbps)
        mb_1min = self.config_mgr.estimate_file_size_mb(60, bitrate_kbps)
        self.size_est_lbl.setText(
            f"💡 Estimated Output: ~{mb_1min:.2f} MB / min (~{mb_5min:.2f} MB for a 5-minute song)"
        )

    def _on_local_files_added(self, file_paths: List[str]):
        new_count = 0
        for f in file_paths:
            if f not in self.staged_local_files:
                self.staged_local_files.append(f)
                new_count += 1
        total = len(self.staged_local_files)
        self.local_files_summary_lbl.setText(f"📁 {total} local media file(s) selected ready to convert.")
        self.local_files_summary_lbl.setStyleSheet("font-size: 11px; color: #10b981; font-weight: 600;")

    def _on_import_txt_clicked(self):
        txt_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Media URL List (.txt)",
            "",
            "Text Files (*.txt);;All Files (*.*)"
        )
        if not txt_path:
            return

        try:
            lines = parse_txt_file(Path(txt_path))
            existing_text = self.url_text_edit.toPlainText().strip()
            joined = "\n".join(lines)
            if existing_text:
                self.url_text_edit.setPlainText(f"{existing_text}\n{joined}")
            else:
                self.url_text_edit.setPlainText(joined)
            QMessageBox.information(
                self,
                "List Imported",
                f"Successfully imported {len(lines)} item lines from:\n{Path(txt_path).name}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to read file: {e}")

    def _on_browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder for Converted MP3s",
            self.config_mgr.settings.output_directory
        )
        if folder:
            self.config_mgr.settings.output_directory = folder
            self.config_mgr.save()
            self.output_path_input.setText(folder)

    def _on_open_output_folder(self):
        folder = Path(self.config_mgr.settings.output_directory)
        open_folder_and_select(folder)

    def _process_and_add(self, start_immediately: bool = False):
        raw_text = self.url_text_edit.toPlainText().strip()
        url_lines = parse_multiline_inputs(raw_text)

        all_inputs: List[ValidationResult] = []
        validation_errors: List[str] = []

        # Validate URLs
        for line in url_lines:
            res = InputValidator.validate_url(line)
            if res.is_valid:
                all_inputs.append(res)
            else:
                validation_errors.append(f"• {line}\n   → {res.error_message}")

        # Validate Local Files
        for lpath in self.staged_local_files:
            res = InputValidator.validate_local_file(lpath)
            if res.is_valid:
                all_inputs.append(res)
            else:
                validation_errors.append(f"• {Path(lpath).name}\n   → {res.error_message}")

        if not all_inputs and not validation_errors:
            QMessageBox.warning(
                self,
                "No Inputs Provided",
                "Please paste at least one media URL or select local media files to convert."
            )
            return

        # Check for errors
        if validation_errors:
            error_report = "\n".join(validation_errors[:5])
            if len(validation_errors) > 5:
                error_report += f"\n...and {len(validation_errors) - 5} more."

            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("Input Validation Notice")
            msg_box.setText(
                f"The following inputs could not be validated:\n\n{error_report}\n\n"
                "You can also drag and drop local media files below, or select them via file browser."
            )
            btn_import_local = msg_box.addButton("📁 Import Local File...", QMessageBox.ActionRole)
            btn_close = msg_box.addButton("Close", QMessageBox.RejectRole)
            msg_box.setDefaultButton(btn_import_local)
            msg_box.exec()

            if msg_box.clickedButton() == btn_import_local:
                self.drop_zone._on_browse_clicked()
                if self.staged_local_files and start_immediately:
                    self._process_and_add(start_immediately=True)
                return

        if not all_inputs and not self.staged_local_files:
            return

        # Duplicate detection
        existing_keys = self.queue_mgr.get_existing_keys()
        unique_items, dupes = detect_duplicates(all_inputs, existing_keys)

        if dupes:
            QMessageBox.information(
                self,
                "Duplicates Detected",
                f"Skipped {len(dupes)} duplicate item(s) already in queue or listed multiple times."
            )

        if not unique_items:
            QMessageBox.information(
                self,
                "Already Queued",
                "All provided items are already present in the active batch queue."
            )
            return

        # Create QueueItem objects
        out_dir = Path(self.config_mgr.settings.output_directory)
        bitrate = self.preset_group.checkedId()
        if bitrate <= 0:
            bitrate = self.config_mgr.settings.default_bitrate

        new_queue_items = []
        for val in unique_items:
            item = QueueItem(
                source_input=val.normalized_path,
                source_type=val.source_type,
                display_name=val.display_title,
                bitrate_kbps=bitrate,
                output_dir=out_dir
            )
            new_queue_items.append(item)

        self.queue_mgr.add_items(new_queue_items)

        # Clear inputs on success
        self.url_text_edit.clear()
        self.staged_local_files.clear()
        self.local_files_summary_lbl.setText("No local files selected.")
        self.local_files_summary_lbl.setStyleSheet("font-size: 11px; color: #64748b;")

        self.refresh_stats()

        if start_immediately:
            self.queue_mgr.start_queue()
            self.start_conversion_requested.emit()
        else:
            QMessageBox.information(
                self,
                "Items Added",
                f"Added {len(new_queue_items)} media items to the conversion queue."
            )
            self.view_queue_requested.emit()

    def refresh_stats(self):
        """Update stat summary cards from database and active queue."""
        db_stats = DatabaseManager().get_summary_stats()
        self.card_completed.set_value(str(db_stats["completed_jobs"]))
        self.card_storage.set_value(format_bytes(db_stats["total_output_bytes"]))
        self.card_active.set_value(str(len(self.queue_mgr.items)))
        self.card_failed.set_value(str(db_stats["failed_jobs"]))
