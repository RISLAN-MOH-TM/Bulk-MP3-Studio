"""
Unit tests for configuration manager and bitrate preset calculation.
"""

from pathlib import Path
import pytest

from src.config import (
    ConfigManager,
    AppSettings,
    BITRATE_PRESETS,
    VALID_BITRATES
)


def test_bitrate_presets_contain_required():
    required = {32, 48, 64, 96, 128}
    present = {p["bitrate"] for p in BITRATE_PRESETS}
    assert required.issubset(present)
    assert set(VALID_BITRATES) == {32, 48, 64, 96, 128}


def test_estimate_file_size_mb():
    # 60 seconds at 128 kbps:
    # 128,000 / 8 = 16,000 bytes/sec * 60 = 960,000 bytes ~ 0.92 MB
    mb = ConfigManager.estimate_file_size_mb(duration_seconds=60, bitrate_kbps=128)
    assert 0.85 <= mb <= 1.0

    # 300 seconds (5 min) at 32 kbps:
    # 32,000 / 8 = 4,000 bytes/sec * 300 = 1,200,000 bytes ~ 1.15 MB
    mb_low = ConfigManager.estimate_file_size_mb(duration_seconds=300, bitrate_kbps=32)
    assert 1.0 <= mb_low <= 1.3

    # Zero duration
    assert ConfigManager.estimate_file_size_mb(0, 64) == 0.0


def test_app_settings_validation():
    s = AppSettings(
        default_bitrate=999,  # invalid
        overwrite_policy="invalid_policy",
        concurrency=50
    )
    s.validate()
    assert s.default_bitrate == 64
    assert s.overwrite_policy == "rename"
    assert s.concurrency == 2
