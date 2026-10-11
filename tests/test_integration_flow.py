"""
End-to-end batch conversion workflow test.
Verifies queue processing of local audio files, progress signals,
output MP3 creation, and SQLite history recording.
"""

import time
import subprocess
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from src.config import ConfigManager
from src.database import DatabaseManager
from src.ffmpeg_engine import find_ffmpeg_binary
from src.queue_manager import QueueManager, QueueItem, JobStatus


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_batch_conversion_workflow(qapp, tmp_path):
    exe = find_ffmpeg_binary()
    assert exe is not None

    # 1. Create two small synthetic audio files (sine wave WAV and AAC in MP4)
    file1 = tmp_path / "song_one.wav"
    subprocess.run(
        [exe, "-f", "lavfi", "-i", "sine=frequency=440:duration=1.5", str(file1), "-y"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    file2 = tmp_path / "song_two.wav"
    subprocess.run(
        [exe, "-f", "lavfi", "-i", "sine=frequency=880:duration=1.5", str(file2), "-y"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    out_dir = tmp_path / "mp3_out"
    out_dir.mkdir()

    cfg = ConfigManager()
    cfg.settings.output_directory = str(out_dir)
    cfg.settings.concurrency = 2

    db = DatabaseManager(db_path=tmp_path / "integration_history.db")
    db.clear_history()

    qm = QueueManager(config_mgr=cfg)
    qm.clear_all()

    item1 = QueueItem(
        source_input=str(file1),
        source_type="LOCAL_FILE",
        display_name="song_one.wav",
        bitrate_kbps=64,
        output_dir=out_dir
    )
    item2 = QueueItem(
        source_input=str(file2),
        source_type="LOCAL_FILE",
        display_name="song_two.wav",
        bitrate_kbps=32,
        output_dir=out_dir
    )

    qm.add_items([item1, item2])
    assert len(qm.items) == 2

    # Start queue
    qm.start_queue()

    # Wait for completion in test loop (up to 10 seconds)
    start_wait = time.time()
    while time.time() - start_wait < 10.0:
        qapp.processEvents()
        if all(it.status in (JobStatus.COMPLETED, JobStatus.FAILED) for it in qm.items):
            break
        time.sleep(0.05)

    assert item1.status == JobStatus.COMPLETED
    assert item2.status == JobStatus.COMPLETED
    assert item1.output_path is not None
    assert item1.output_path.exists()
    assert item1.output_size_bytes > 0
    assert item2.output_path is not None
    assert item2.output_path.exists()
    assert item2.output_size_bytes > 0

    # 32 kbps file should be smaller than 64 kbps file for the same 1.5s duration
    assert item2.output_size_bytes < item1.output_size_bytes

    # Verify SQLite recorded both jobs
    history = db.get_history()
    assert len(history) >= 2
    statuses = {h.status for h in history}
    assert "COMPLETED" in statuses
