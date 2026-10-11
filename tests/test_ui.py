"""
Unit and integration tests for PySide6 UI views and MainWindow.
"""

from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from src.config import ConfigManager
from src.queue_manager import QueueManager, QueueItem, JobStatus
from src.ui.main_window import MainWindow
from src.ui.views.dashboard_view import DashboardView
from src.ui.views.queue_view import QueueView
from src.ui.views.history_view import HistoryView
from src.ui.views.settings_view import SettingsView


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_main_window_creation(qapp):
    win = MainWindow()
    assert win.windowTitle().startswith("Bulk MP3 Studio")
    assert win.stack.count() == 4
    win.close()


def test_sidebar_navigation(qapp):
    win = MainWindow()
    # Initial page is Dashboard (0)
    assert win.stack.currentIndex() == 0

    # Switch to Queue (1)
    win.sidebar.set_active_page(1)
    assert win.stack.currentIndex() == 1
    assert win.header.title_lbl.text() == "Conversion Queue"

    # Switch to History (2)
    win.sidebar.set_active_page(2)
    assert win.stack.currentIndex() == 2
    assert win.header.title_lbl.text() == "Job History"

    # Switch to Settings (3)
    win.sidebar.set_active_page(3)
    assert win.stack.currentIndex() == 3
    assert win.header.title_lbl.text() == "Settings & Media Engine"

    win.close()


def test_queue_view_table_sync(qapp, tmp_path):
    qm = QueueManager(config_mgr=ConfigManager())
    qm.clear_all()

    item = QueueItem(
        source_input="sample_track.wav",
        source_type="LOCAL_FILE",
        display_name="sample_track.wav",
        bitrate_kbps=64,
        output_dir=tmp_path
    )
    qm.add_item(item)

    qv = QueueView(qm)
    assert qv.table.rowCount() == 1
    assert qv.table.item(0, 0).text() == "sample_track.wav"
    assert qv.table.item(0, 2).text() == "64 kbps"


def test_settings_view_load(qapp):
    cfg = ConfigManager()
    sv = SettingsView(cfg)
    assert sv.bitrate_combo.count() > 0
    assert sv.policy_combo.count() == 3
    assert sv.conc_spin.value() in (1, 2, 3, 4)
