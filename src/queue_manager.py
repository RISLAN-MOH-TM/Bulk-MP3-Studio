"""
Batch queue manager for Bulk MP3 Studio.
Orchestrates worker threads via QThreadPool and QRunnable, safe cancellation,
status transitions, and real-time progress aggregation.
"""

import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Set

from PySide6.QtCore import QObject, Signal, QThreadPool, QRunnable

from src.config import ConfigManager
from src.database import DatabaseManager, JobRecord
from src.downloader import download_media_url
from src.ffmpeg_engine import (
    convert_audio_file,
    probe_media_duration,
    find_ffmpeg_binary,
    FFmpegNotFoundError
)
from src.logger import get_logger
from src.utils import resolve_output_path, extract_filename_from_url, format_bytes

logger = get_logger("queue_manager")


class JobStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    CONVERTING = "CONVERTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class QueueItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_input: str = ""       # Original URL or file path
    source_type: str = "LOCAL_FILE"  # "LOCAL_FILE" or "URL"
    display_name: str = ""
    bitrate_kbps: int = 64
    output_dir: Path = field(default_factory=Path.cwd)
    output_path: Optional[Path] = None
    status: JobStatus = JobStatus.PENDING
    progress_pct: float = 0.0
    status_message: str = "Waiting in queue"
    duration_seconds: float = 0.0
    output_size_bytes: int = 0
    error_message: str = ""
    is_cancelled: bool = False
    temp_file: Optional[Path] = None
    created_at: float = field(default_factory=time.time)
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class WorkerSignals(QObject):
    """Signals emitted by background conversion worker."""
    started = Signal(str)                                # item_id
    progress = Signal(str, float, str)                   # item_id, pct, message
    completed = Signal(str, str, int, float, float)      # item_id, output_path, bytes, duration, elapsed
    failed = Signal(str, str)                            # item_id, error_message
    cancelled = Signal(str)                              # item_id


class ConversionTask(QRunnable):
    """Background task executed in QThreadPool."""

    def __init__(self, item: QueueItem, signals: WorkerSignals, config_mgr: ConfigManager):
        super().__init__()
        self.item = item
        self.signals = signals
        self.config_mgr = config_mgr
        self.setAutoDelete(True)

    def run(self):
        if self.item.is_cancelled:
            self.item.status = JobStatus.CANCELLED
            self.item.status_message = "Cancelled"
            self.signals.cancelled.emit(self.item.id)
            return

        self.item.start_time = time.time()
        self.signals.started.emit(self.item.id)
        settings = self.config_mgr.settings

        # 1. Resolve FFmpeg executable
        ffmpeg_exe = find_ffmpeg_binary(settings.ffmpeg_custom_path)
        if not ffmpeg_exe:
            err_msg = "FFmpeg executable could not be found. Please check Settings."
            self.item.status = JobStatus.FAILED
            self.item.status_message = err_msg
            self.item.error_message = err_msg
            self._record_database(status="FAILED", error=err_msg)
            self.signals.failed.emit(self.item.id, err_msg)
            return

        local_media_path: Optional[Path] = None

        # 2. If URL, download to temporary file first
        if self.item.source_type == "URL":
            self.item.status = JobStatus.DOWNLOADING
            self.item.status_message = "Connecting to source..."
            self.signals.progress.emit(self.item.id, 0.0, "Downloading media...")

            def download_progress(dl_bytes: int, total_bytes: Optional[int], pct: Optional[float]):
                if pct is not None:
                    msg = f"Downloading: {pct:.0f}% ({format_bytes(dl_bytes)})"
                    self.signals.progress.emit(self.item.id, pct * 0.4, msg)  # 0-40% for download
                else:
                    msg = f"Downloading: {format_bytes(dl_bytes)}"
                    self.signals.progress.emit(self.item.id, 20.0, msg)

            cookies_file = getattr(settings, "cookies_file", "") or ""
            success, temp_file, err = download_media_url(
                url=self.item.source_input,
                progress_callback=download_progress,
                is_cancelled=lambda: self.item.is_cancelled,
                cookies_file=cookies_file if cookies_file and Path(cookies_file).is_file() else None,
            )

            if self.item.is_cancelled:
                self.item.status = JobStatus.CANCELLED
                self.item.status_message = "Cancelled"
                self.signals.cancelled.emit(self.item.id)
                return

            if not success or not temp_file:
                error_msg = f"Download failed: {err}"
                self.item.status = JobStatus.FAILED
                self.item.status_message = error_msg
                self.item.error_message = error_msg
                self._record_database(status="FAILED", error=error_msg)
                self.signals.failed.emit(self.item.id, error_msg)
                return

            self.item.temp_file = temp_file
            local_media_path = temp_file
        else:
            local_media_path = Path(self.item.source_input)
            if not local_media_path.exists():
                error_msg = f"File not found: {self.item.source_input}"
                self.item.status = JobStatus.FAILED
                self.item.status_message = error_msg
                self.item.error_message = error_msg
                self._record_database(status="FAILED", error=error_msg)
                self.signals.failed.emit(self.item.id, error_msg)
                return

        # 3. Resolve destination output path with collision policy
        desired_stem = Path(self.item.display_name).stem
        target_path, should_skip = resolve_output_path(
            output_dir=self.item.output_dir,
            desired_filename=f"{desired_stem}.mp3",
            policy=settings.overwrite_policy
        )

        if should_skip:
            # File already exists and policy is "skip"
            self.item.status = JobStatus.COMPLETED
            self.item.output_path = target_path
            self.item.status_message = "Skipped (already exists)"
            self.item.output_size_bytes = target_path.stat().st_size if target_path.exists() else 0
            self._cleanup_temp()
            self.signals.completed.emit(
                self.item.id, str(target_path), self.item.output_size_bytes, 0.0, 0.0
            )
            return

        self.item.output_path = target_path

        # 4. Probe media duration
        self.item.status = JobStatus.CONVERTING
        self.item.status_message = "Analyzing audio stream..."
        self.signals.progress.emit(self.item.id, 40.0 if self.item.source_type == "URL" else 5.0, "Analyzing...")

        duration = probe_media_duration(ffmpeg_exe, local_media_path)
        if duration:
            self.item.duration_seconds = duration

        # 5. Perform conversion with progress tracking
        def conv_progress(pct: float, curr_sec: float, total_sec: Optional[float]):
            if self.item.source_type == "URL":
                # Scale 40% -> 100%
                scaled = 40.0 + (pct * 0.6)
            else:
                scaled = pct

            sec_display = f"{int(curr_sec)}s"
            if total_sec and total_sec > 0:
                sec_display += f" / {int(total_sec)}s"

            msg = f"Encoding MP3 ({self.item.bitrate_kbps}k): {scaled:.0f}% [{sec_display}]"
            self.signals.progress.emit(self.item.id, scaled, msg)

        conv_ok, conv_err = convert_audio_file(
            ffmpeg_exe=ffmpeg_exe,
            input_path=local_media_path,
            output_path=target_path,
            bitrate_kbps=self.item.bitrate_kbps,
            channels=settings.audio_channels,
            sample_rate=settings.sample_rate,
            total_duration=duration,
            progress_callback=conv_progress,
            is_cancelled=lambda: self.item.is_cancelled
        )

        # Cleanup temporary downloaded file
        self._cleanup_temp()

        self.item.end_time = time.time()
        elapsed = round(self.item.end_time - (self.item.start_time or self.item.created_at), 2)

        if self.item.is_cancelled:
            self.item.status = JobStatus.CANCELLED
            self.item.status_message = "Cancelled"
            self.signals.cancelled.emit(self.item.id)
            return

        if not conv_ok:
            self.item.status = JobStatus.FAILED
            self.item.status_message = f"Failed: {conv_err[:80]}"
            self.item.error_message = conv_err
            self._record_database(status="FAILED", error=conv_err, elapsed=elapsed)
            self.signals.failed.emit(self.item.id, conv_err)
            return

        # 6. Success
        output_size = target_path.stat().st_size if target_path.exists() else 0
        self.item.output_size_bytes = output_size
        self.item.status = JobStatus.COMPLETED
        self.item.status_message = f"Completed ({format_bytes(output_size)} in {elapsed}s)"
        self.item.progress_pct = 100.0

        self._record_database(
            status="COMPLETED",
            output_path=str(target_path),
            size_bytes=output_size,
            duration=self.item.duration_seconds,
            elapsed=elapsed
        )
        self.signals.completed.emit(
            self.item.id, str(target_path), output_size, self.item.duration_seconds, elapsed
        )

    def _cleanup_temp(self):
        if self.item.temp_file and self.item.temp_file.exists():
            try:
                self.item.temp_file.unlink()
            except Exception:
                pass
            self.item.temp_file = None

    def _record_database(
        self,
        status: str,
        output_path: str = "",
        size_bytes: int = 0,
        duration: float = 0.0,
        elapsed: float = 0.0,
        error: str = ""
    ):
        try:
            record = JobRecord(
                job_id=self.item.id,
                source_name=self.item.display_name,
                source_type=self.item.source_type,
                source_path=self.item.source_input,
                output_path=output_path,
                output_size_bytes=size_bytes,
                bitrate_kbps=self.item.bitrate_kbps,
                duration_seconds=duration,
                conversion_time_seconds=elapsed,
                timestamp=datetime.now().isoformat(timespec="seconds"),
                status=status,
                error_message=error
            )
            DatabaseManager().record_job(record)
        except Exception as e:
            logger.error(f"Database recording error for {self.item.id}: {e}")


class QueueManager(QObject):
    """
    Central queue manager controlling queue state, concurrency,
    batch operations, and emitting signals to the UI.
    """
    queue_updated = Signal()
    item_status_changed = Signal(str, str)                  # item_id, status_name
    item_progress_changed = Signal(str, float, str)         # item_id, pct, msg
    overall_progress_changed = Signal(int, int, float)      # completed_count, total_count, overall_pct
    queue_finished = Signal()

    def __init__(self, config_mgr: Optional[ConfigManager] = None):
        super().__init__()
        self.config_mgr = config_mgr or ConfigManager()
        self.items: List[QueueItem] = []
        self._items_by_id: Dict[str, QueueItem] = {}
        self.is_running: bool = False
        self.is_paused: bool = False
        self._active_workers: int = 0

        self.thread_pool = QThreadPool.globalInstance()
        self.signals = WorkerSignals()

        # Connect internal worker signals
        self.signals.started.connect(self._on_worker_started)
        self.signals.progress.connect(self._on_worker_progress)
        self.signals.completed.connect(self._on_worker_completed)
        self.signals.failed.connect(self._on_worker_failed)
        self.signals.cancelled.connect(self._on_worker_cancelled)

    def add_item(self, item: QueueItem) -> None:
        self.items.append(item)
        self._items_by_id[item.id] = item
        self.queue_updated.emit()
        self._update_overall_progress()

    def add_items(self, items: List[QueueItem]) -> None:
        for it in items:
            self.items.append(it)
            self._items_by_id[it.id] = it
        self.queue_updated.emit()
        self._update_overall_progress()

    def start_queue(self) -> None:
        """Start or resume queue execution."""
        if not self.items:
            return

        self.is_running = True
        self.is_paused = False
        self._pump_queue()

    def pause_queue(self) -> None:
        """Pause the queue. Ongoing jobs continue, new pending jobs will not start."""
        self.is_paused = True
        self.queue_updated.emit()

    def resume_queue(self) -> None:
        """Resume starting pending jobs."""
        self.is_paused = False
        self.is_running = True
        self._pump_queue()
        self.queue_updated.emit()

    def cancel_item(self, item_id: str) -> None:
        """Cancel a specific item in the queue."""
        item = self._items_by_id.get(item_id)
        if item:
            item.is_cancelled = True
            if item.status == JobStatus.PENDING:
                item.status = JobStatus.CANCELLED
                item.status_message = "Cancelled"
                self.item_status_changed.emit(item.id, JobStatus.CANCELLED.value)
                self.queue_updated.emit()
                self._update_overall_progress()

    def cancel_all(self) -> None:
        """Cancel all pending and running items."""
        self.is_running = False
        self.is_paused = False
        for item in self.items:
            if item.status in (JobStatus.PENDING, JobStatus.DOWNLOADING, JobStatus.CONVERTING):
                item.is_cancelled = True
                if item.status == JobStatus.PENDING:
                    item.status = JobStatus.CANCELLED
                    item.status_message = "Cancelled"
        self.queue_updated.emit()
        self._update_overall_progress()

    def retry_failed(self) -> None:
        """Reset failed and cancelled items back to PENDING and restart."""
        count = 0
        for item in self.items:
            if item.status in (JobStatus.FAILED, JobStatus.CANCELLED):
                item.status = JobStatus.PENDING
                item.is_cancelled = False
                item.progress_pct = 0.0
                item.status_message = "Waiting in queue"
                item.error_message = ""
                count += 1
        if count > 0:
            self.queue_updated.emit()
            self._update_overall_progress()
            self.start_queue()

    def clear_completed(self) -> None:
        """Remove completed and cancelled items from queue."""
        self.items = [
            it for it in self.items
            if it.status in (JobStatus.PENDING, JobStatus.DOWNLOADING, JobStatus.CONVERTING)
        ]
        self._items_by_id = {it.id: it for it in self.items}
        self.queue_updated.emit()
        self._update_overall_progress()

    def remove_item(self, item_id: str) -> None:
        """Remove an item from the queue list."""
        item = self._items_by_id.get(item_id)
        if item and item.status in (JobStatus.DOWNLOADING, JobStatus.CONVERTING):
            item.is_cancelled = True

        self.items = [it for it in self.items if it.id != item_id]
        if item_id in self._items_by_id:
            del self._items_by_id[item_id]

        self.queue_updated.emit()
        self._update_overall_progress()

    def clear_all(self) -> None:
        """Stop running jobs and empty the entire queue."""
        self.cancel_all()
        self.items.clear()
        self._items_by_id.clear()
        self.queue_updated.emit()
        self._update_overall_progress()

    def _pump_queue(self) -> None:
        """Dispatch pending jobs to QThreadPool up to concurrency limit."""
        if not self.is_running or self.is_paused:
            return

        max_concurrent = self.config_mgr.settings.concurrency

        while self._active_workers < max_concurrent:
            # Find next pending item
            next_item = next(
                (it for it in self.items if it.status == JobStatus.PENDING and not it.is_cancelled),
                None
            )
            if not next_item:
                break

            self._active_workers += 1
            task = ConversionTask(next_item, self.signals, self.config_mgr)
            self.thread_pool.start(task)

        if self._active_workers == 0:
            # Check if all items are processed
            has_pending = any(it.status == JobStatus.PENDING and not it.is_cancelled for it in self.items)
            if not has_pending:
                self.is_running = False
                self.queue_finished.emit()

    def _on_worker_started(self, item_id: str):
        item = self._items_by_id.get(item_id)
        if item:
            self.item_status_changed.emit(item.id, item.status.value)
        self.queue_updated.emit()

    def _on_worker_progress(self, item_id: str, pct: float, msg: str):
        item = self._items_by_id.get(item_id)
        if item:
            item.progress_pct = pct
            item.status_message = msg
            self.item_progress_changed.emit(item.id, pct, msg)
        self._update_overall_progress()

    def _on_worker_completed(self, item_id: str, out_path: str, size: int, duration: float, elapsed: float):
        self._active_workers = max(0, self._active_workers - 1)
        item = self._items_by_id.get(item_id)
        if item:
            self.item_status_changed.emit(item.id, JobStatus.COMPLETED.value)
        self.queue_updated.emit()
        self._update_overall_progress()
        self._pump_queue()

    def _on_worker_failed(self, item_id: str, error: str):
        self._active_workers = max(0, self._active_workers - 1)
        item = self._items_by_id.get(item_id)
        if item:
            self.item_status_changed.emit(item.id, JobStatus.FAILED.value)
        self.queue_updated.emit()
        self._update_overall_progress()
        self._pump_queue()

    def _on_worker_cancelled(self, item_id: str):
        self._active_workers = max(0, self._active_workers - 1)
        item = self._items_by_id.get(item_id)
        if item:
            self.item_status_changed.emit(item.id, JobStatus.CANCELLED.value)
        self.queue_updated.emit()
        self._update_overall_progress()
        self._pump_queue()

    def _update_overall_progress(self):
        total = len(self.items)
        if total == 0:
            self.overall_progress_changed.emit(0, 0, 0.0)
            return

        completed = sum(1 for it in self.items if it.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED))
        sum_pct = sum(
            100.0 if it.status == JobStatus.COMPLETED else
            it.progress_pct if it.status in (JobStatus.DOWNLOADING, JobStatus.CONVERTING) else
            0.0
            for it in self.items
        )
        overall_pct = min(100.0, sum_pct / total)
        self.overall_progress_changed.emit(completed, total, overall_pct)

    def get_existing_keys(self) -> Set[str]:
        """Return lower-cased paths of current queue items for duplicate detection."""
        return {it.source_input.strip().lower() for it in self.items}
