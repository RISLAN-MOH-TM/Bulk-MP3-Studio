"""
Unit tests for file utility and path manipulation functions.
"""

import os
from pathlib import Path
import pytest

from src.utils import (
    sanitize_filename,
    extract_filename_from_url,
    resolve_output_path,
    format_bytes,
    format_duration
)


def test_sanitize_filename_invalid_chars():
    bad_name = 'audio:my*favorite?song<test>|track".mp3'
    cleaned = sanitize_filename(bad_name)
    assert ":" not in cleaned
    assert "*" not in cleaned
    assert "?" not in cleaned
    assert "<" not in cleaned
    assert ">" not in cleaned
    assert "|" not in cleaned
    assert '"' not in cleaned
    assert cleaned.endswith(".mp3")


def test_sanitize_filename_windows_reserved():
    assert sanitize_filename("CON.mp3") == "_CON.mp3"
    assert sanitize_filename("aux.wav") == "_aux.wav"
    assert sanitize_filename("NUL") == "_NUL"


def test_sanitize_filename_empty():
    assert sanitize_filename("") == "audio_track"
    assert sanitize_filename("   ") == "audio_track"


def test_extract_filename_from_url():
    url1 = "https://example.com/media/episodes/podcast_episode_101.wav?token=abc123"
    assert extract_filename_from_url(url1) == "podcast_episode_101.wav"

    url2 = "https://example.com/stream/live"
    assert extract_filename_from_url(url2, fallback="radio") == "live.mp3"


def test_resolve_output_path_rename(tmp_path):
    target_dir = tmp_path / "out"
    target_dir.mkdir()

    # First file does not exist
    path1, skip1 = resolve_output_path(target_dir, "test.mp3", policy="rename")
    assert skip1 is False
    assert path1.name == "test.mp3"
    path1.write_text("dummy")

    # Second file collision -> rename
    path2, skip2 = resolve_output_path(target_dir, "test.mp3", policy="rename")
    assert skip2 is False
    assert path2.name == "test_1.mp3"
    path2.write_text("dummy")

    # Third file collision -> rename
    path3, skip3 = resolve_output_path(target_dir, "test.mp3", policy="rename")
    assert skip3 is False
    assert path3.name == "test_2.mp3"


def test_resolve_output_path_skip(tmp_path):
    target_dir = tmp_path / "out_skip"
    target_dir.mkdir()

    file1 = target_dir / "skip_me.mp3"
    file1.write_text("existing")

    path, skip = resolve_output_path(target_dir, "skip_me.mp3", policy="skip")
    assert skip is True
    assert path == file1


def test_resolve_output_path_overwrite(tmp_path):
    target_dir = tmp_path / "out_overwrite"
    target_dir.mkdir()

    file1 = target_dir / "overwrite_me.mp3"
    file1.write_text("existing")

    path, skip = resolve_output_path(target_dir, "overwrite_me.mp3", policy="overwrite")
    assert skip is False
    assert path == file1


def test_format_bytes():
    assert format_bytes(500) == "500 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1024 * 1024) == "1.00 MB"
    assert format_bytes(5 * 1024 * 1024) == "5.00 MB"
    assert format_bytes(None) == "0 B"


def test_format_duration():
    assert format_duration(0) == "--:--"
    assert format_duration(45) == "00:45"
    assert format_duration(125) == "02:05"
    assert format_duration(3665) == "01:01:05"
