"""
Job History View for Bulk MP3 Studio.
Displays persistent SQLite records of processed conversions with search,
filtering, CSV export, and quick file/folder access.
"""

import csv
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt

from src.database import DatabaseManager, JobRecord
from src.ui.widgets.status_badge import StatusBadge
from src.utils import (
    format_bytes,
    format_duration,
    open_file_in_default_app,
    open_folder_and_select
)


class HistoryView(QWidget):
    """View displaying historical conversion runs stored in SQLite."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.current_records = []

        self._build_ui()
        self.refresh_history()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # 1. Filter and Search Bar Card
        filter_card = QFrame()
        filter_card.setObjectName("cardFrame")
        fc_layout = QHBoxLayout(filter_card)
        fc_layout.setContentsMargins(16, 12, 16, 12)
        fc_layout.setSpacing(12)

        # Search box
        search_lbl = QLabel("Search:")
        search_lbl.setStyleSheet("font-weight: 600; color: #94a3b8;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by file name or output path...")
        self.search_input.textChanged.connect(self.refresh_history)

        # Status filter
        filter_lbl = QLabel("Status:")
        filter_lbl.setStyleSheet("font-weight: 600; color: #94a3b8;")
        self.status_combo = QComboBox()
        self.status_combo.addItems(["All", "COMPLETED", "FAILED"])
        self.status_combo.currentTextChanged.connect(self.refresh_history)

        # Buttons
        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.clicked.connect(self.refresh_history)

        self.btn_export_csv = QPushButton("📊 Export CSV")
        self.btn_export_csv.clicked.connect(self._on_export_csv)

        self.btn_clear_history = QPushButton("🗑 Clear History")
        self.btn_clear_history.setObjectName("dangerBtn")
        self.btn_clear_history.clicked.connect(self._on_clear_history)

        fc_layout.addWidget(search_lbl)
        fc_layout.addWidget(self.search_input, 1)
        fc_layout.addWidget(filter_lbl)
        fc_layout.addWidget(self.status_combo)
        fc_layout.addWidget(self.btn_refresh)
        fc_layout.addWidget(self.btn_export_csv)
        fc_layout.addWidget(self.btn_clear_history)

        main_layout.addWidget(filter_card)

        # 2. History Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Timestamp", "Source Name", "Type", "Bitrate", "Size", "Duration", "Status", "Actions"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # Timestamp
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Source Name
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Type
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # Bitrate
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # Size
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents) # Duration
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents) # Status
        header.setSectionResizeMode(7, QHeaderView.Fixed)             # Actions
        self.table.setColumnWidth(7, 140)

        main_layout.addWidget(self.table)

    def refresh_history(self):
        query = self.search_input.text()
        status = self.status_combo.currentText()
        records = self.db.get_history(limit=250, status_filter=status, search_query=query)
        self.current_records = records

        self.table.setRowCount(len(records))
        for row, rec in enumerate(records):
            # Timestamp
            ts_item = QTableWidgetItem(rec.timestamp.replace("T", " "))
            ts_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, ts_item)

            # Name
            name_item = QTableWidgetItem(rec.source_name)
            name_item.setToolTip(f"Source: {rec.source_path}\nOutput: {rec.output_path}\nError: {rec.error_message}")
            self.table.setItem(row, 1, name_item)

            # Type
            badge = StatusBadge(rec.source_type)
            self.table.setCellWidget(row, 2, badge)

            # Bitrate
            br_item = QTableWidgetItem(f"{rec.bitrate_kbps} kbps")
            br_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, br_item)

            # Size
            size_str = format_bytes(rec.output_size_bytes) if rec.status == "COMPLETED" else "-"
            size_item = QTableWidgetItem(size_str)
            size_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, size_item)

            # Duration
            dur_str = format_duration(rec.duration_seconds)
            dur_item = QTableWidgetItem(dur_str)
            dur_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, dur_item)

            # Status
            status_badge = StatusBadge(rec.status)
            self.table.setCellWidget(row, 6, status_badge)

            # Actions
            action_box = self._create_row_actions(rec)
            self.table.setCellWidget(row, 7, action_box)

    def _create_row_actions(self, rec: JobRecord) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(6)

        out_path = Path(rec.output_path) if rec.output_path else None
        if rec.status == "COMPLETED" and out_path and out_path.exists():
            btn_play = QPushButton("▶ Play")
            btn_play.setFixedWidth(54)
            btn_play.setStyleSheet("padding: 2px 4px; font-size: 11px;")
            btn_play.clicked.connect(lambda _, p=out_path: open_file_in_default_app(p))
            lay.addWidget(btn_play)

            btn_folder = QPushButton("📁")
            btn_folder.setToolTip("Show in Explorer")
            btn_folder.setFixedWidth(30)
            btn_folder.setStyleSheet("padding: 2px 4px; font-size: 11px;")
            btn_folder.clicked.connect(lambda _, p=out_path: open_folder_and_select(p))
            lay.addWidget(btn_folder)
        else:
            lbl_err = QLabel("Failed" if rec.status == "FAILED" else "No file")
            lbl_err.setStyleSheet("color: #64748b; font-size: 11px;")
            lbl_err.setAlignment(Qt.AlignCenter)
            lay.addWidget(lbl_err)

        return w

    def _on_export_csv(self):
        if not self.current_records:
            QMessageBox.information(self, "Export CSV", "No history records to export.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Job History to CSV",
            "bulk_mp3_history.csv",
            "CSV Files (*.csv);;All Files (*.*)"
        )
        if not save_path:
            return

        try:
            with open(save_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Job ID", "Timestamp", "Source Name", "Source Type", "Source Path",
                    "Output Path", "Bitrate (kbps)", "Output Bytes", "Duration (sec)",
                    "Elapsed (sec)", "Status", "Error Message"
                ])
                for r in self.current_records:
                    writer.writerow([
                        r.job_id, r.timestamp, r.source_name, r.source_type, r.source_path,
                        r.output_path, r.bitrate_kbps, r.output_size_bytes, r.duration_seconds,
                        r.conversion_time_seconds, r.status, r.error_message
                    ])
            QMessageBox.information(self, "Export Successful", f"Saved history to:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not write CSV: {e}")

    def _on_clear_history(self):
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to delete all job history records from SQLite database?\n"
            "This will not delete your converted MP3 files.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.clear_history()
            self.refresh_history()
