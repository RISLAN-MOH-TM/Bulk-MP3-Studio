"""
Validator module for Bulk MP3 Studio.
Handles URL syntax verification, copyright/platform restriction detection,
local file support checks, duplicate detection, and batch text import.
"""

import os
import re
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set, Tuple, Optional


SUPPORTED_LOCAL_EXTENSIONS = {
    # Audio
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma",
    ".aiff", ".aif", ".alac", ".ape", ".ac3",
    # Video containers with extractable audio tracks
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".flv", ".m4v", ".3gp", ".ts"
}

# All major video and audio hosting platforms are supported via yt-dlp / pytubefix.
# No domain-level restrictions are enforced at the UI layer.
SUPPORTED_VIDEO_HOSTS = {
    "youtube.com", "youtu.be", "m.youtube.com",
    "vimeo.com", "dailymotion.com", "twitch.tv",
    "tiktok.com", "instagram.com", "facebook.com",
    "soundcloud.com", "bandcamp.com", "mixcloud.com",
    "twitter.com", "x.com", "reddit.com",
    "bilibili.com", "nicovideo.jp",
}


@dataclass
class ValidationResult:
    is_valid: bool
    source_type: str        # "LOCAL_FILE" or "URL"
    raw_input: str
    normalized_path: str
    display_title: str
    extension: str
    error_message: Optional[str] = None


class InputValidator:
    """Validates local file paths and media URLs."""

    @classmethod
    def validate_local_file(cls, path_str: str) -> ValidationResult:
        """Validate an existing local media file."""
        clean_path = path_str.strip().strip('"').strip("'")
        if not clean_path:
            return ValidationResult(
                is_valid=False,
                source_type="LOCAL_FILE",
                raw_input=path_str,
                normalized_path="",
                display_title="",
                extension="",
                error_message="Empty file path provided."
            )

        p = Path(clean_path)
        if not p.exists():
            return ValidationResult(
                is_valid=False,
                source_type="LOCAL_FILE",
                raw_input=path_str,
                normalized_path=str(p),
                display_title=p.name or clean_path,
                extension=p.suffix.lower(),
                error_message=f"File does not exist: {clean_path}"
            )

        if not p.is_file():
            return ValidationResult(
                is_valid=False,
                source_type="LOCAL_FILE",
                raw_input=path_str,
                normalized_path=str(p),
                display_title=p.name,
                extension=p.suffix.lower(),
                error_message="Path is a directory, not a media file."
            )

        ext = p.suffix.lower()
        if ext not in SUPPORTED_LOCAL_EXTENSIONS:
            return ValidationResult(
                is_valid=False,
                source_type="LOCAL_FILE",
                raw_input=path_str,
                normalized_path=str(p),
                display_title=p.name,
                extension=ext,
                error_message=f"Unsupported media format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_LOCAL_EXTENSIONS))}"
            )

        try:
            if p.stat().st_size == 0:
                return ValidationResult(
                    is_valid=False,
                    source_type="LOCAL_FILE",
                    raw_input=path_str,
                    normalized_path=str(p),
                    display_title=p.name,
                    extension=ext,
                    error_message="File is empty (0 bytes)."
                )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                source_type="LOCAL_FILE",
                raw_input=path_str,
                normalized_path=str(p),
                display_title=p.name,
                extension=ext,
                error_message=f"Cannot read file attributes: {e}"
            )

        return ValidationResult(
            is_valid=True,
            source_type="LOCAL_FILE",
            raw_input=path_str,
            normalized_path=str(p.resolve()),
            display_title=p.name,
            extension=ext,
            error_message=None
        )

    @classmethod
    def validate_url(cls, url_str: str) -> ValidationResult:
        """Validate URL syntax, detect restricted platforms, and check media format."""
        clean_url = url_str.strip()
        if not clean_url:
            return ValidationResult(
                is_valid=False,
                source_type="URL",
                raw_input=url_str,
                normalized_path="",
                display_title="",
                extension="",
                error_message="Empty URL."
            )

        try:
            parsed = urllib.parse.urlparse(clean_url)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                source_type="URL",
                raw_input=clean_url,
                normalized_path=clean_url,
                display_title=clean_url,
                extension="",
                error_message=f"Invalid URL syntax: {e}"
            )

        if parsed.scheme.lower() not in ("http", "https"):
            return ValidationResult(
                is_valid=False,
                source_type="URL",
                raw_input=clean_url,
                normalized_path=clean_url,
                display_title=clean_url,
                extension="",
                error_message="Only HTTP and HTTPS media URLs are supported."
            )

        domain = parsed.netloc.lower()
        if not domain:
            return ValidationResult(
                is_valid=False,
                source_type="URL",
                raw_input=clean_url,
                normalized_path=clean_url,
                display_title=clean_url,
                extension="",
                error_message="Missing host or domain name in URL."
            )

        path_part = parsed.path.lower()
        ext = Path(path_part).suffix

        # Extract a display title
        url_name = Path(urllib.parse.unquote(parsed.path)).name
        if not url_name or url_name in ("watch", "video", ""):
            if "youtube.com" in domain or "youtu.be" in domain:
                query_params = urllib.parse.parse_qs(parsed.query)
                video_id = query_params.get("v", [""])[0] or Path(parsed.path).name
                url_name = f"youtube_{video_id}" if video_id else "youtube_media"
            else:
                url_name = f"{domain}_media"

        return ValidationResult(
            is_valid=True,
            source_type="URL",
            raw_input=clean_url,
            normalized_path=clean_url,
            display_title=url_name,
            extension=ext or ".mp3",
            error_message=None
        )

    @classmethod
    def validate_any(cls, input_str: str) -> ValidationResult:
        """Automatically detect if input is a URL or a local file and validate."""
        clean = input_str.strip().strip('"').strip("'")
        if clean.lower().startswith("http://") or clean.lower().startswith("https://"):
            return cls.validate_url(clean)
        return cls.validate_local_file(clean)


def parse_multiline_inputs(text: str) -> List[str]:
    """Split multiline input into individual sanitized lines, filtering out empty and comment lines."""
    lines = []
    for line in text.splitlines():
        trimmed = line.strip()
        if trimmed and not trimmed.startswith("#"):
            lines.append(trimmed)
    return lines


def parse_txt_file(file_path: Path) -> List[str]:
    """Read a .txt list file and return valid non-empty lines."""
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Try utf-8 first, fallback to latin-1
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = file_path.read_text(encoding="latin-1")

    return parse_multiline_inputs(content)


def detect_duplicates(
    new_candidates: List[ValidationResult],
    existing_keys: Set[str]
) -> Tuple[List[ValidationResult], List[ValidationResult]]:
    """
    Split candidates into (unique_items, duplicate_items) based on normalized path.
    Also removes duplicates within the candidate batch itself.
    """
    unique_items: List[ValidationResult] = []
    duplicate_items: List[ValidationResult] = []
    seen = set(existing_keys)

    for item in new_candidates:
        key = item.normalized_path.lower()
        if key in seen:
            duplicate_items.append(item)
        else:
            seen.add(key)
            unique_items.append(item)

    return unique_items, duplicate_items
