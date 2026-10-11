"""
Queue View for Bulk MP3 Studio.
Displays active batch queue, real-time per-item progress, overall progress bar,
and controls for start, pause, cancel, retry, and clear.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox
)
from PySide6.QtCore import Qt

from src.queue_manager import QueueManager, JobStatus, QueueItem
from src.ui.widgets.status_badge import StatusBadge
from src.utils import format_bytes, open_file_in_default_app, open_folder_and_select


class QueueView(QWidget):
    """Detailed queue view managing in-flight and scheduled conversion jobs."""

    def __init__(self, queue_mgr: QueueManager, parent=None):
        super().__init__(parent)
        self.queue_mgr = queue_mgr
        self._row_items_map = {}  # row_idx -> item_id

        self._build_ui()
        self._connect_signals()
        self.refresh_table()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # 1. Overall Batch Progress Card
        progress_card = QFrame()
        progress_card.setObjectName("cardFrame")
        prog_layout = QVBoxLayout(progress_card)
        prog_layout.setContentsMargins(18, 14, 18, 14)
        prog_layout.setSpacing(8)

        prog_top_row = QHBoxLayout()
        self.prog_title_lbl = QLabel("BATCH CONVERSION PROGRESS")
        self.prog_title_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px;")

        self.prog_status_lbl = QLabel("Queue idle (0 items)")
        self.prog_status_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #38bdf8;")

        prog_top_row.addWidget(self.prog_title_lbl)
        prog_top_row.addStretch()
        prog_top_row.addWidget(self.prog_status_lbl)
        prog_layout.addLayout(prog_top_row)

        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setFixedHeight(12)
        self.overall_progress_bar.setRange(0, 100)
        self.overall_progress_bar.setValue(0)
        self.overall_progress_bar.setTextVisible(False)
        prog_layout.addWidget(self.overall_progress_bar)

        main_layout.addWidget(progress_card)

        # 2. Control Toolbar
        toolbar_card = QFrame()
        toolbar_card.setObjectName("cardFrame")
        tb_layout = QHBoxLayout(toolbar_card)
        tb_layout.setContentsMargins(14, 10, 14, 10)
        tb_layout.setSpacing(10)

        self.btn_start = QPushButton("▶ Start Batch")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self._on_start_clicked)

        self.btn_pause = QPushButton("⏸ Pause Queue")
        self.btn_pause.setCursor(Qt.PointingHandCursor)
        self.btn_pause.clicked.connect(self._on_pause_toggle_clicked)

        self.btn_cancel_all = QPushButton("⏹ Cancel All")
        self.btn_cancel_all.setObjectName("dangerBtn")
        self.btn_cancel_all.setCursor(Qt.PointingHandCursor)
        self.btn_cancel_all.clicked.connect(self._on_cancel_all_clicked)

        self.btn_retry_failed = QPushButton("🔄 Retry Failed")
        self.btn_retry_failed.setCursor(Qt.PointingHandCursor)
        self.btn_retry_failed.clicked.connect(self.queue_mgr.retry_failed)

        self.btn_clear_completed = QPushButton("🧹 Clear Completed")
        self.btn_clear_completed.setCursor(Qt.PointingHandCursor)
        self.btn_clear_completed.clicked.connect(self.queue_mgr.clear_completed)

        self.btn_clear_all = QPushButton("Clear All")
        self.btn_clear_all.setCursor(Qt.PointingHandCursor)
        self.btn_clear_all.clicked.connect(self._on_clear_all_clicked)

        tb_layout.addWidget(self.btn_start)
        tb_layout.addWidget(self.btn_pause)
        tb_layout.addWidget(self.btn_cancel_all)
        tb_layout.addWidget(self.btn_retry_failed)
        tb_layout.addStretch()
        tb_layout.addWidget(self.btn_clear_completed)
        tb_layout.addWidget(self.btn_clear_all)

        main_layout.addWidget(toolbar_card)

        # 3. Queue Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Media Name", "Source", "Target", "Status", "Progress", "Message / Details", "Actions"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)       # Media Name
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) # Source
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Target Bitrate
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # Status
        header.setSectionResizeMode(4, QHeaderView.Fixed)            # Progress
        self.table.setColumnWidth(4, 130)
        header.setSectionResizeMode(5, QHeaderView.Stretch)       # Details
        header.setSectionResizeMode(6, QHeaderView.Fixed)            # Actions
        self.table.setColumnWidth(6, 170)

        main_layout.addWidget(self.table)

    def _connect_signals(self):
        self.queue_mgr.queue_updated.connect(self.refresh_table)
        self.queue_mgr.item_progress_changed.connect(self._on_item_progress)
        self.queue_mgr.item_status_changed.connect(self._on_item_status)
        self.queue_mgr.overall_progress_changed.connect(self._on_overall_progress)
        self.queue_mgr.queue_finished.connect(self._on_queue_finished)

    def _on_start_clicked(self):
        if not self.queue_mgr.items:
            QMessageBox.information(self, "Queue Empty", "Add media items to the queue from Dashboard first.")
            return
        self.queue_mgr.start_queue()
        self.refresh_toolbar_state()

    def _on_pause_toggle_clicked(self):
        if self.queue_mgr.is_paused:
            self.queue_mgr.resume_queue()
            self.btn_pause.setText("⏸ Pause Queue")
        else:
            self.queue_mgr.pause_queue()
            self.btn_pause.setText("▶ Resume Queue")

    def _on_cancel_all_clicked(self):
        self.queue_mgr.cancel_all()
        self.refresh_toolbar_state()

    def _on_clear_all_clicked(self):
        if self.queue_mgr.items:
            self.queue_mgr.clear_all()
        self.refresh_table()

    def _on_queue_finished(self):
        self.refresh_toolbar_state()

    def refresh_toolbar_state(self):
        is_running = self.queue_mgr.is_running
        self.btn_start.setEnabled(not is_running or self.queue_mgr.is_paused)
        if self.queue_mgr.is_paused:
            self.btn_pause.setText("▶ Resume Queue")
        else:
            self.btn_pause.setText("⏸ Pause Queue")

    def refresh_table(self):
        items = list(self.queue_mgr.items)
        self.table.setRowCount(len(items))
        self._row_items_map.clear()

        for row, item in enumerate(items):
            self._row_items_map[item.id] = row

            # Col 0: Media Name
            name_item = QTableWidgetItem(item.display_name)
            name_item.setToolTip(f"Source: {item.source_input}\nOutput: {item.output_path or 'Pending'}")
            name_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.table.setItem(row, 0, name_item)

            # Col 1: Source Type Badge
            badge_type = StatusBadge(item.source_type)
            self.table.setCellWidget(row, 1, badge_type)

            # Col 2: Bitrate
            br_item = QTableWidgetItem(f"{item.bitrate_kbps} kbps")
            br_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, br_item)

            # Col 3: Status Badge
            status_badge = StatusBadge(item.status.value)
            self.table.setCellWidget(row, 3, status_badge)

            # Col 4: Progress Bar
            pbar = QProgressBar()
            pbar.setFixedHeight(12)
            pbar.setRange(0, 100)
            pbar.setValue(int(item.progress_pct))
            pbar.setTextVisible(True)
            self.table.setCellWidget(row, 4, pbar)

            # Col 5: Message / Details
            msg_item = QTableWidgetItem(item.status_message)
            msg_item.setToolTip(item.error_message if item.error_message else item.status_message)
            msg_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.table.setItem(row, 5, msg_item)

            # Col 6: Actions widget
            action_widget = self._create_row_actions(item)
            self.table.setCellWidget(row, 6, action_widget)

        self.refresh_toolbar_state()

    def _create_row_actions(self, item: QueueItem) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(6)

        if item.status == JobStatus.COMPLETED and item.output_path and Path(item.output_path).exists():
            btn_play = QPushButton("▶ Open")
            btn_play.setToolTip("Play converted MP3 in default player")
            btn_play.setFixedWidth(54)
            btn_play.setStyleSheet("padding: 2px 4px; font-size: 11px;")
            btn_play.clicked.connect(lambda _, p=item.output_path: open_file_in_default_app(Path(p)))
            lay.addWidget(btn_play)

            btn_folder = QPushButton("📁")
            btn_folder.setToolTip("Show in Explorer")
            btn_folder.setFixedWidth(28)
            btn_folder.setStyleSheet("padding: 2px 4px; font-size: 11px;")
            btn_folder.clicked.connect(lambda _, p=item.output_path: open_folder_and_select(Path(p)))
            lay.addWidget(btn_folder)

        elif item.status in (JobStatus.PENDING, JobStatus.DOWNLOADING, JobStatus.CONVERTING):
            btn_cancel = QPushButton("✖ Cancel")
            btn_cancel.setToolTip("Cancel this job")
            btn_cancel.setFixedWidth(64)
            btn_cancel.setStyleSheet("padding: 2px 4px; font-size: 11px; background-color: #7f1d1d; color: #fca5a5; border-color: #991b1b;")
            btn_cancel.clicked.connect(lambda _, i=item.id: self.queue_mgr.cancel_item(i))
            lay.addWidget(btn_cancel)

        elif item.status in (JobStatus.FAILED, JobStatus.CANCELLED):
            btn_retry = QPushButton("🔄 Retry")
            btn_retry.setToolTip("Retry this job")
            btn_retry.setFixedWidth(54)
            btn_retry.setStyleSheet("padding: 2px 4px; font-size: 11px;")
            btn_retry.clicked.connect(lambda _, i=item.id: self._retry_single_item(i))
            lay.addWidget(btn_retry)

        # Remove button
        btn_del = QPushButton("🗑")
        btn_del.setToolTip("Remove from queue")
        btn_del.setFixedWidth(28)
        btn_del.setStyleSheet("padding: 2px 4px; font-size: 11px; color: #94a3b8;")
        btn_del.clicked.connect(lambda _, i=item.id: self.queue_mgr.remove_item(i))
        lay.addWidget(btn_del)

        return w

    def _retry_single_item(self, item_id: str):
        item = self.queue_mgr._items_by_id.get(item_id)
        if item:
            item.status = JobStatus.PENDING
            item.is_cancelled = False
            item.progress_pct = 0.0
            item.status_message = "Waiting in queue"
            item.error_message = ""
            self.queue_mgr.queue_updated.emit()
            self.queue_mgr.start_queue()

    def _on_item_progress(self, item_id: str, pct: float, msg: str):
        row = self._row_items_map.get(item_id)
        if row is not None and row < self.table.rowCount():
            pbar = self.table.cellWidget(row, 4)
            if isinstance(pbar, QProgressBar):
                pbar.setValue(int(pct))

            msg_item = self.table.item(row, 5)
            if msg_item:
                msg_item.setText(msg)

    def _on_item_status(self, item_id: str, status_name: str):
        row = self._row_items_map.get(item_id)
        if row is not None and row < self.table.rowCount():
            badge = self.table.cellWidget(row, 3)
            if isinstance(badge, StatusBadge):
                badge.set_status(status_name)
            # Recreate actions widget
            item = self.queue_mgr._items_by_id.get(item_id)
            if item:
                self.table.setCellWidget(row, 6, self._create_row_actions(item))

    def _on_overall_progress(self, completed_count: int, total_count: int, overall_pct: float):
        self.overall_progress_bar.setValue(int(overall_pct))
        if total_count == 0:
            self.prog_status_lbl.setText("Queue empty")
        else:
            self.prog_status_lbl.setText(
                f"Processed: {completed_count} / {total_count} items ({overall_pct:.1f}%)"
            )
