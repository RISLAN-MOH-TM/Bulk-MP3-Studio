"""
Unit tests for QueueManager and QueueItem states.
"""

from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from src.config import ConfigManager
from src.queue_manager import QueueManager, QueueItem, JobStatus


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_queue_item_lifecycle(qapp, tmp_path):
    qm = QueueManager(config_mgr=ConfigManager())
    qm.clear_all()

    item1 = QueueItem(
        source_input="test1.wav",
        source_type="LOCAL_FILE",
        display_name="test1.wav",
        bitrate_kbps=64,
        output_dir=tmp_path
    )
    item2 = QueueItem(
        source_input="test2.wav",
        source_type="LOCAL_FILE",
        display_name="test2.wav",
        bitrate_kbps=128,
        output_dir=tmp_path
    )

    qm.add_item(item1)
    qm.add_item(item2)

    assert len(qm.items) == 2
    assert qm.items[0].status == JobStatus.PENDING

    # Test cancel single item
    qm.cancel_item(item1.id)
    assert qm.items[0].status == JobStatus.CANCELLED

    # Test retry failed/cancelled
    qm.retry_failed()
    assert qm.items[0].status == JobStatus.PENDING

    # Test clear completed
    qm.items[0].status = JobStatus.COMPLETED
    qm.clear_completed()
    assert len(qm.items) == 1
    assert qm.items[0].id == item2.id

    # Test duplicate keys
    keys = qm.get_existing_keys()
    assert "test2.wav" in keys
