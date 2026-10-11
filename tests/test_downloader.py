"""
Unit tests for universal media downloader.
"""

from pathlib import Path
import pytest

from src.downloader import download_media_url


def test_download_direct_http_file(tmp_path):
    # Use reliable GitHub raw sample audio file
    url = "https://raw.githubusercontent.com/rafaelreis-hotmart/Audio-Sample-files/master/sample.mp3"
    progresses = []

    def on_prog(downloaded, total, pct):
        if pct is not None:
            progresses.append(pct)

    ok, out_path, err = download_media_url(
        url=url,
        temp_dir=tmp_path,
        progress_callback=on_prog
    )

    assert ok is True
    assert out_path is not None
    assert out_path.exists()
    assert out_path.stat().st_size > 0
    assert err == ""
    assert len(progresses) > 0


def test_download_cancellation(tmp_path):
    url = "https://raw.githubusercontent.com/rafaelreis-hotmart/Audio-Sample-files/master/sample.mp3"
    cancelled_flag = [False]

    def on_prog(downloaded, total, pct):
        cancelled_flag[0] = True

    ok, out_path, err = download_media_url(
        url=url,
        temp_dir=tmp_path,
        progress_callback=on_prog,
        is_cancelled=lambda: cancelled_flag[0]
    )

    assert ok is False
    assert "cancelled" in err.lower()
