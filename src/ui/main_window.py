"""
Main Window for Bulk MP3 Studio.
Integrates the navigation sidebar, top header, page stack, and queue lifecycle.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QMessageBox
)
from PySide6.QtCore import Qt

from src.config import ConfigManager
from src.ffmpeg_engine import find_ffmpeg_binary, get_ffmpeg_version_info
from src.logger import get_logger
from src.queue_manager import QueueManager, JobStatus
from src.ui.theme import DARK_STYLESHEET
from src.ui.views.dashboard_view import DashboardView
from src.ui.views.history_view import HistoryView
from src.ui.views.queue_view import QueueView
from src.ui.views.settings_view import SettingsView
from src.ui.widgets.header import AppHeader
from src.ui.widgets.sidebar import AppSidebar
from src.utils import open_folder_and_select

logger = get_logger("main_window")


class MainWindow(QMainWindow):
    """Primary application window for Bulk MP3 Studio."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bulk MP3 Studio — Local Audio Conversion & Batch Manager")
        self.resize(1120, 720)
        self.setMinimumSize(960, 600)

        self.config_mgr = ConfigManager()
        self.queue_mgr = QueueManager(config_mgr=self.config_mgr)

        self._apply_theme()
        self._build_ui()
        self._connect_signals()
        self._init_system_status()

    def _apply_theme(self):
        self.setStyleSheet(DARK_STYLESHEET)

    def _build_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Sidebar Navigation
        self.sidebar = AppSidebar()
        root_layout.addWidget(self.sidebar)

        # 2. Main Content Area
        content_wrapper = QWidget()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Header
        self.header = AppHeader()
        content_layout.addWidget(self.header)

        # Page Stack
        self.stack = QStackedWidget()

        self.view_dashboard = DashboardView(self.queue_mgr, self.config_mgr)
        self.view_queue = QueueView(self.queue_mgr)
        self.view_history = HistoryView()
        self.view_settings = SettingsView(self.config_mgr)

        self.stack.addWidget(self.view_dashboard) # Index 0
        self.stack.addWidget(self.view_queue)     # Index 1
        self.stack.addWidget(self.view_history)   # Index 2
        self.stack.addWidget(self.view_settings)  # Index 3

        content_layout.addWidget(self.stack)
        root_layout.addWidget(content_wrapper)

    def _connect_signals(self):
        # Navigation
        self.sidebar.page_changed.connect(self._on_navigate)
        self.header.settings_requested.connect(lambda: self.sidebar.set_active_page(3))
        self.header.open_output_folder_clicked.connect(self._on_open_output_folder)

        # Dashboard actions
        self.view_dashboard.start_conversion_requested.connect(lambda: self.sidebar.set_active_page(1))
        self.view_dashboard.view_queue_requested.connect(lambda: self.sidebar.set_active_page(1))

        # Settings
        self.view_settings.ffmpeg_status_changed.connect(self.header.set_ffmpeg_status)

        # Queue events
        self.queue_mgr.queue_updated.connect(self._on_queue_state_updated)
        self.queue_mgr.queue_finished.connect(self._on_queue_batch_finished)

    def _init_system_status(self):
        # Probe FFmpeg
        detected = find_ffmpeg_binary(self.config_mgr.settings.ffmpeg_custom_path)
        if detected:
            ok, info = get_ffmpeg_version_info(detected)
            self.header.set_ffmpeg_status(ok, info)
        else:
            self.header.set_ffmpeg_status(False, "")

        self._on_queue_state_updated()

    def _on_navigate(self, index: int):
        self.stack.setCurrentIndex(index)
        titles = {
            0: "Dashboard",
            1: "Conversion Queue",
            2: "Job History",
            3: "Settings & Media Engine"
        }
        self.header.set_view_title(titles.get(index, "Dashboard"))

        if index == 0:
            self.view_dashboard.refresh_stats()
        elif index == 2:
            self.view_history.refresh_history()

    def _on_queue_state_updated(self):
        total = len(self.queue_mgr.items)
        active = sum(1 for it in self.queue_mgr.items if it.status in (JobStatus.PENDING, JobStatus.DOWNLOADING, JobStatus.CONVERTING))
        self.sidebar.update_queue_badge(active)

        if total == 0:
            self.header.set_queue_status("Queue: Empty")
        else:
            self.header.set_queue_status(f"Queue: {active} Active / {total} Total")

        self.view_dashboard.refresh_stats()

    def _on_queue_batch_finished(self):
        self.view_dashboard.refresh_stats()
        self.view_history.refresh_history()

    def _on_open_output_folder(self):
        out_dir = Path(self.config_mgr.settings.output_directory)
        open_folder_and_select(out_dir)

    def closeEvent(self, event):
        has_running = any(
            it.status in (JobStatus.DOWNLOADING, JobStatus.CONVERTING)
            for it in self.queue_mgr.items
        )
        if has_running:
            reply = QMessageBox.question(
                self,
                "Conversion in Progress",
                "Conversion tasks are currently running. Do you want to cancel ongoing jobs and exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.queue_mgr.cancel_all()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
