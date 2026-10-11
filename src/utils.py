"""
Utility functions for file management, sanitization, collision resolution, and formatting.
"""

import os
import re
import subprocess
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple


WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10))
}

INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_filename(filename: str, fallback_stem: str = "audio_track", max_length: int = 180) -> str:
    """
    Sanitize a filename for safe usage on Windows filesystem.
    Removes forbidden characters, trims whitespace, prevents reserved device names.
    """
    if not filename or not filename.strip():
        filename = fallback_stem

    # Remove invalid characters
    cleaned = INVALID_FILENAME_CHARS.sub("_", filename).strip()

    # Remove trailing periods or spaces which are invalid in Windows
    cleaned = cleaned.rstrip(". ")

    if not cleaned:
        cleaned = fallback_stem

    # Check for reserved Windows device names (e.g. CON, NUL)
    stem_check = Path(cleaned).stem.upper()
    if stem_check in WINDOWS_RESERVED_NAMES:
        cleaned = f"_{cleaned}"

    # Truncate length while preserving extension if possible
    if len(cleaned) > max_length:
        path_obj = Path(cleaned)
        suffix = path_obj.suffix
        stem = path_obj.stem[: max_length - len(suffix)]
        cleaned = f"{stem}{suffix}"

    return cleaned


def extract_filename_from_url(url: str, fallback: str = "media_download") -> str:
    """Extract a clean base filename from a URL path."""
    try:
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed.path)
        base = Path(path).name
        if base and "." in base:
            return sanitize_filename(base, fallback_stem=fallback)
        elif base:
            return sanitize_filename(f"{base}.mp3", fallback_stem=fallback)
    except Exception:
        pass
    return sanitize_filename(f"{fallback}.mp3")


def resolve_output_path(
    output_dir: Path,
    desired_filename: str,
    policy: str = "rename"
) -> Tuple[Optional[Path], bool]:
    """
    Resolve the final output path according to overwrite policy.
    Returns: (final_path, should_skip)
    - If policy == "skip" and file exists, returns (existing_path, True)
    - If policy == "overwrite", returns (target_path, False)
    - If policy == "rename" and file exists, increments `_1`, `_2`, etc.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_name = sanitize_filename(desired_filename)
    if not clean_name.lower().endswith(".mp3"):
        clean_name = f"{Path(clean_name).stem}.mp3"

    target_path = output_dir / clean_name

    if not target_path.exists():
        return target_path, False

    if policy == "overwrite":
        return target_path, False

    if policy == "skip":
        return target_path, True

    # Policy is "rename"
    stem = target_path.stem
    counter = 1
    while True:
        candidate_name = f"{stem}_{counter}.mp3"
        candidate_path = output_dir / candidate_name
        if not candidate_path.exists():
            return candidate_path, False
        counter += 1


def format_bytes(size_bytes: Optional[int]) -> str:
    """Format byte count into human-readable string (B, KB, MB, GB)."""
    if size_bytes is None or size_bytes < 0:
        return "0 B"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_duration(seconds: Optional[float]) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    if seconds is None or seconds <= 0:
        return "--:--"
    total_seconds = int(round(seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def open_file_in_default_app(file_path: Path) -> bool:
    """Launch file in default Windows handler."""
    try:
        if file_path.exists():
            os.startfile(str(file_path))
            return True
    except Exception:
        pass
    return False


def open_folder_and_select(file_path: Path) -> bool:
    """Open Windows Explorer with file selected, or open containing folder."""
    try:
        if file_path.is_file():
            subprocess.Popen(["explorer", f"/select,{str(file_path)}"], shell=False)
            return True
        elif file_path.is_dir():
            os.startfile(str(file_path))
            return True
        elif file_path.parent.exists():
            os.startfile(str(file_path.parent))
            return True
    except Exception:
        pass
    return False
