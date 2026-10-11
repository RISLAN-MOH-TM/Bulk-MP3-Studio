"""
Unit tests for input validator, URL rules, copyright/platform restrictions, and duplicate handling.
"""

from pathlib import Path
import pytest

from src.validator import (
    InputValidator,
    parse_multiline_inputs,
    detect_duplicates
)


def test_validate_valid_url():
    res = InputValidator.validate_url("https://example.com/audio/sample.wav")
    assert res.is_valid is True
    assert res.source_type == "URL"
    assert res.display_title == "sample.wav"
    assert res.error_message is None


def test_validate_invalid_url_scheme():
    res = InputValidator.validate_url("ftp://example.com/music.mp3")
    assert res.is_valid is False
    assert "HTTP and HTTPS" in res.error_message


def test_validate_youtube_url():
    res1 = InputValidator.validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert res1.is_valid is True
    assert res1.source_type == "URL"
    assert "dQw4w9WgXcQ" in res1.display_title

    res2 = InputValidator.validate_url("https://youtu.be/dQw4w9WgXcQ")
    assert res2.is_valid is True
    assert res2.source_type == "URL"


def test_validate_other_video_platforms():
    res = InputValidator.validate_url("https://vimeo.com/76979871")
    assert res.is_valid is True
    assert res.source_type == "URL"


def test_validate_local_file(tmp_path):
    # Non-existent
    bad_res = InputValidator.validate_local_file(str(tmp_path / "ghost.wav"))
    assert bad_res.is_valid is False
    assert "does not exist" in bad_res.error_message

    # Unsupported format
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("Hello")
    txt_res = InputValidator.validate_local_file(str(txt_file))
    assert txt_res.is_valid is False
    assert "Unsupported media format" in txt_res.error_message

    # Valid format
    wav_file = tmp_path / "track.wav"
    wav_file.write_bytes(b"RIFF dummy wav data")
    ok_res = InputValidator.validate_local_file(str(wav_file))
    assert ok_res.is_valid is True
    assert ok_res.source_type == "LOCAL_FILE"
    assert ok_res.display_title == "track.wav"


def test_parse_multiline_inputs():
    text = """
    https://example.com/one.mp3
    # This is a comment
    
    https://example.com/two.wav
      https://example.com/three.m4a  
    """
    lines = parse_multiline_inputs(text)
    assert len(lines) == 3
    assert lines[0] == "https://example.com/one.mp3"
    assert lines[1] == "https://example.com/two.wav"
    assert lines[2] == "https://example.com/three.m4a"


def test_detect_duplicates():
    r1 = InputValidator.validate_url("https://example.com/one.mp3")
    r2 = InputValidator.validate_url("https://example.com/one.mp3")
    r3 = InputValidator.validate_url("https://example.com/two.mp3")

    existing = {"https://example.com/existing.mp3"}
    uniques, dupes = detect_duplicates([r1, r2, r3], existing)

    assert len(uniques) == 2
    assert len(dupes) == 1
    assert dupes[0].normalized_path == "https://example.com/one.mp3"
