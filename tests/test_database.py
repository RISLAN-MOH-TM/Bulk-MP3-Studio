"""
Unit tests for SQLite database manager.
"""

from pathlib import Path
import pytest

from src.database import DatabaseManager, JobRecord


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_history.db"
    db_mgr = DatabaseManager(db_path=db_file)
    db_mgr.clear_history()
    return db_mgr


def test_database_record_and_query(test_db):
    rec = JobRecord(
        job_id="job-101",
        source_name="episode.wav",
        source_type="LOCAL_FILE",
        source_path="C:/media/episode.wav",
        output_path="C:/out/episode.mp3",
        output_size_bytes=1048576,
        bitrate_kbps=64,
        duration_seconds=120.0,
        conversion_time_seconds=2.4,
        timestamp="2026-10-12T00:00:00",
        status="COMPLETED"
    )
    ok = test_db.record_job(rec)
    assert ok is True

    history = test_db.get_history(limit=10)
    assert len(history) == 1
    assert history[0].job_id == "job-101"
    assert history[0].output_size_bytes == 1048576
    assert history[0].status == "COMPLETED"


def test_database_stats_summary(test_db):
    test_db.record_job(JobRecord(
        job_id="job-1",
        source_name="s1.wav",
        source_type="LOCAL_FILE",
        source_path="s1.wav",
        output_path="s1.mp3",
        output_size_bytes=500000,
        bitrate_kbps=64,
        duration_seconds=60.0,
        conversion_time_seconds=1.0,
        timestamp="2026-10-12T00:01:00",
        status="COMPLETED"
    ))
    test_db.record_job(JobRecord(
        job_id="job-2",
        source_name="s2.wav",
        source_type="LOCAL_FILE",
        source_path="s2.wav",
        output_path="",
        output_size_bytes=0,
        bitrate_kbps=96,
        duration_seconds=0.0,
        conversion_time_seconds=0.5,
        timestamp="2026-10-12T00:02:00",
        status="FAILED",
        error_message="Corrupted source file"
    ))

    stats = test_db.get_summary_stats()
    assert stats["total_jobs"] == 2
    assert stats["completed_jobs"] == 1
    assert stats["failed_jobs"] == 1
    assert stats["total_output_bytes"] == 500000


def test_database_delete_and_clear(test_db):
    test_db.record_job(JobRecord(
        job_id="job-del",
        source_name="del.wav",
        source_type="LOCAL_FILE",
        source_path="del.wav",
        output_path="del.mp3",
        output_size_bytes=1000,
        bitrate_kbps=64,
        duration_seconds=10.0,
        conversion_time_seconds=0.5,
        timestamp="2026-10-12T00:03:00",
        status="COMPLETED"
    ))
    assert len(test_db.get_history()) == 1

    test_db.delete_job("job-del")
    assert len(test_db.get_history()) == 0
