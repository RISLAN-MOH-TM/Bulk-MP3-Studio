"""
SQLite history database manager for Bulk MP3 Studio.
Stores details of processed jobs, timestamps, output file paths, sizes, and error messages.
"""

import os
import sqlite3
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.logger import get_logger

logger = get_logger("database")


@dataclass
class JobRecord:
    job_id: str
    source_name: str
    source_type: str         # "LOCAL_FILE" or "URL"
    source_path: str
    output_path: str
    output_size_bytes: int
    bitrate_kbps: int
    duration_seconds: float
    conversion_time_seconds: float
    timestamp: str           # ISO 8601
    status: str              # "COMPLETED", "FAILED", "CANCELLED"
    error_message: str = ""
    id: Optional[int] = None


def get_db_path() -> Path:
    """Return the database file location."""
    app_data = os.getenv("APPDATA")
    if app_data:
        db_dir = Path(app_data) / "BulkMP3Studio"
    else:
        db_dir = Path.home() / ".bulk_mp3_studio"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "history.db"


class DatabaseManager:
    """Thread-safe SQLite manager for job history."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[Path] = None):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.db_path = db_path or get_db_path()
            cls._instance._init_db()
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables and indices if they do not exist."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS job_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT UNIQUE NOT NULL,
                        source_name TEXT NOT NULL,
                        source_type TEXT NOT NULL,
                        source_path TEXT NOT NULL,
                        output_path TEXT,
                        output_size_bytes INTEGER DEFAULT 0,
                        bitrate_kbps INTEGER NOT NULL,
                        duration_seconds REAL DEFAULT 0.0,
                        conversion_time_seconds REAL DEFAULT 0.0,
                        timestamp TEXT NOT NULL,
                        status TEXT NOT NULL,
                        error_message TEXT DEFAULT ''
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON job_history (status)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON job_history (timestamp DESC)")
                conn.commit()

    def record_job(self, record: JobRecord) -> bool:
        """Insert or replace a completed/failed job record."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT INTO job_history (
                            job_id, source_name, source_type, source_path,
                            output_path, output_size_bytes, bitrate_kbps,
                            duration_seconds, conversion_time_seconds,
                            timestamp, status, error_message
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(job_id) DO UPDATE SET
                            output_path=excluded.output_path,
                            output_size_bytes=excluded.output_size_bytes,
                            duration_seconds=excluded.duration_seconds,
                            conversion_time_seconds=excluded.conversion_time_seconds,
                            timestamp=excluded.timestamp,
                            status=excluded.status,
                            error_message=excluded.error_message
                    """, (
                        record.job_id,
                        record.source_name,
                        record.source_type,
                        record.source_path,
                        record.output_path,
                        record.output_size_bytes,
                        record.bitrate_kbps,
                        record.duration_seconds,
                        record.conversion_time_seconds,
                        record.timestamp,
                        record.status,
                        record.error_message or ""
                    ))
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to record job {record.job_id}: {e}")
                return False

    def get_history(
        self,
        limit: int = 200,
        status_filter: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[JobRecord]:
        """Query historical jobs with optional status filter and text search."""
        query = "SELECT * FROM job_history WHERE 1=1"
        params: List[Any] = []

        if status_filter and status_filter.upper() != "ALL":
            query += " AND status = ?"
            params.append(status_filter.upper())

        if search_query and search_query.strip():
            query += " AND (source_name LIKE ? OR output_path LIKE ?)"
            term = f"%{search_query.strip()}%"
            params.extend([term, term])

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        results: List[JobRecord] = []
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(query, params)
                    for row in cur.fetchall():
                        results.append(JobRecord(
                            id=row["id"],
                            job_id=row["job_id"],
                            source_name=row["source_name"],
                            source_type=row["source_type"],
                            source_path=row["source_path"],
                            output_path=row["output_path"] or "",
                            output_size_bytes=row["output_size_bytes"] or 0,
                            bitrate_kbps=row["bitrate_kbps"],
                            duration_seconds=row["duration_seconds"] or 0.0,
                            conversion_time_seconds=row["conversion_time_seconds"] or 0.0,
                            timestamp=row["timestamp"],
                            status=row["status"],
                            error_message=row["error_message"] or ""
                        ))
            except Exception as e:
                logger.error(f"Failed to fetch job history: {e}")
        return results

    def get_summary_stats(self) -> Dict[str, Any]:
        """Calculate overall statistics for dashboard cards."""
        stats = {
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "total_output_bytes": 0,
            "avg_bitrate": 64
        }
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT
                            COUNT(*) as total,
                            SUM(CASE WHEN status='COMPLETED' THEN 1 ELSE 0 END) as completed,
                            SUM(CASE WHEN status='FAILED' THEN 1 ELSE 0 END) as failed,
                            SUM(CASE WHEN status='COMPLETED' THEN output_size_bytes ELSE 0 END) as total_bytes,
                            AVG(CASE WHEN status='COMPLETED' THEN bitrate_kbps ELSE NULL END) as avg_br
                        FROM job_history
                    """)
                    row = cur.fetchone()
                    if row:
                        stats["total_jobs"] = row["total"] or 0
                        stats["completed_jobs"] = row["completed"] or 0
                        stats["failed_jobs"] = row["failed"] or 0
                        stats["total_output_bytes"] = row["total_bytes"] or 0
                        stats["avg_bitrate"] = int(row["avg_br"] or 64)
            except Exception as e:
                logger.error(f"Failed to compute stats: {e}")
        return stats

    def clear_history(self) -> bool:
        """Delete all entries from the job history table."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    conn.execute("DELETE FROM job_history")
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to clear history: {e}")
                return False

    def delete_job(self, job_id: str) -> bool:
        """Delete a single job by its UUID."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    conn.execute("DELETE FROM job_history WHERE job_id = ?", (job_id,))
                    conn.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to delete job {job_id}: {e}")
                return False
