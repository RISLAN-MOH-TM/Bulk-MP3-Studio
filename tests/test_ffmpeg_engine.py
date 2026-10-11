"""
Unit tests for FFmpeg execution, argument generation, duration probing, and conversion.
"""

import subprocess
from pathlib import Path
import pytest

from src.ffmpeg_engine import (
    find_ffmpeg_binary,
    get_ffmpeg_version_info,
    build_ffmpeg_args,
    probe_media_duration,
    convert_audio_file
)


def test_build_ffmpeg_args():
    args = build_ffmpeg_args(
        ffmpeg_exe="ffmpeg.exe",
        input_path=Path("input.wav"),
        output_path=Path("output.mp3"),
        bitrate_kbps=96,
        channels="stereo",
        sample_rate="44100"
    )
    assert args[0] == "ffmpeg.exe"
    assert "-i" in args
    assert "-b:a" in args
    idx_b = args.index("-b:a")
    assert args[idx_b + 1] == "96k"
    assert "-ac" in args
    idx_ac = args.index("-ac")
    assert args[idx_ac + 1] == "2"
    assert "-ar" in args
    idx_ar = args.index("-ar")
    assert args[idx_ar + 1] == "44100"
    assert "-progress" in args


def test_find_ffmpeg_binary():
    exe = find_ffmpeg_binary()
    assert exe is not None
    assert Path(exe).exists()
    ok, info = get_ffmpeg_version_info(exe)
    assert ok is True
    assert "ffmpeg version" in info.lower() or "built with" in info.lower()


def test_convert_synthetic_audio(tmp_path):
    exe = find_ffmpeg_binary()
    assert exe is not None

    # 1. Generate a small synthetic 2-second WAV file with FFmpeg
    wav_path = tmp_path / "test_tone.wav"
    gen_cmd = [
        exe, "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
        str(wav_path), "-y"
    ]
    subprocess.run(gen_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    assert wav_path.exists()

    # 2. Probe duration
    duration = probe_media_duration(exe, wav_path)
    assert duration is not None
    assert 1.8 <= duration <= 2.2

    # 3. Convert to 64 kbps MP3
    mp3_path = tmp_path / "test_tone.mp3"
    progress_recorded = []

    def on_progress(pct, curr_sec, tot_sec):
        progress_recorded.append(pct)

    success, err = convert_audio_file(
        ffmpeg_exe=exe,
        input_path=wav_path,
        output_path=mp3_path,
        bitrate_kbps=64,
        total_duration=duration,
        progress_callback=on_progress
    )

    assert success is True
    assert err == ""
    assert mp3_path.exists()
    assert mp3_path.stat().st_size > 0
    assert len(progress_recorded) > 0
    assert progress_recorded[-1] == 100.0
