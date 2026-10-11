"""
Configuration and settings management for Bulk MP3 Studio.
Handles JSON persistence, bitrate presets, and default preferences.
"""

import json
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, Any, List

BITRATE_PRESETS = [
    {
        "bitrate": 32,
        "label": "32 kbps",
        "description": "Ultra Compact (Speech, Audiobooks, Voice notes)",
        "mb_per_min": 0.234,
    },
    {
        "bitrate": 48,
        "label": "48 kbps",
        "description": "Compact (Lectures, Podcasts, Radio Talk)",
        "mb_per_min": 0.351,
    },
    {
        "bitrate": 64,
        "label": "64 kbps (Recommended)",
        "description": "Balanced Low-MB (Standard Podcasts, Web Audio)",
        "mb_per_min": 0.469,
    },
    {
        "bitrate": 96,
        "label": "96 kbps",
        "description": "Good Quality (Music, Mixed Media)",
        "mb_per_min": 0.703,
    },
    {
        "bitrate": 128,
        "label": "128 kbps",
        "description": "Standard Quality (High Fidelity Music)",
        "mb_per_min": 0.938,
    },
]

VALID_BITRATES = [p["bitrate"] for p in BITRATE_PRESETS]


def get_default_output_dir() -> Path:
    """Return default folder for converted MP3 outputs."""
    user_profile = os.getenv("USERPROFILE")
    if user_profile:
        music_dir = Path(user_profile) / "Music" / "BulkMP3_Studio"
    else:
        music_dir = Path.home() / "Music" / "BulkMP3_Studio"
    music_dir.mkdir(parents=True, exist_ok=True)
    return music_dir


def get_config_dir() -> Path:
    """Return directory for storing application configuration."""
    app_data = os.getenv("APPDATA")
    if app_data:
        cfg_dir = Path(app_data) / "BulkMP3Studio"
    else:
        cfg_dir = Path.home() / ".bulk_mp3_studio"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir


def get_config_file_path() -> Path:
    return get_config_dir() / "config.json"


@dataclass
class AppSettings:
    output_directory: str = field(default_factory=lambda: str(get_default_output_dir()))
    default_bitrate: int = 64
    audio_channels: str = "stereo"  # "stereo" or "mono"
    sample_rate: str = "auto"       # "auto", "44100", "48000", "22050"
    overwrite_policy: str = "rename"  # "rename", "skip", "overwrite"
    concurrency: int = 2            # Number of parallel conversion workers (1-4)
    ffmpeg_custom_path: str = ""    # Custom path to ffmpeg.exe if specified by user
    cookies_file: str = ""          # Path to Netscape cookies.txt for YouTube/authenticated downloads
    dark_mode: bool = True
    notifications_enabled: bool = True

    def validate(self) -> None:
        """Sanitize and ensure settings constraints."""
        if self.default_bitrate not in VALID_BITRATES:
            self.default_bitrate = 64
        if self.overwrite_policy not in ("rename", "skip", "overwrite"):
            self.overwrite_policy = "rename"
        if not (1 <= self.concurrency <= 8):
            self.concurrency = 2
        if self.audio_channels not in ("stereo", "mono"):
            self.audio_channels = "stereo"


class ConfigManager:
    """Singleton-style manager for loading and saving settings."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance.settings = AppSettings()
            cls._instance.load()
        return cls._instance

    def load(self) -> AppSettings:
        cfg_path = get_config_file_path()
        if cfg_path.exists():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.settings = AppSettings(**{k: v for k, v in data.items() if k in AppSettings.__dataclass_fields__})
                self.settings.validate()
            except Exception as e:
                # If reading fails, keep defaults
                self.settings = AppSettings()
        else:
            self.settings = AppSettings()
            self.save()
        return self.settings

    def save(self) -> bool:
        cfg_path = get_config_file_path()
        try:
            self.settings.validate()
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(asdict(self.settings), f, indent=2)
            return True
        except Exception:
            return False

    @classmethod
    def estimate_file_size_mb(cls, duration_seconds: float, bitrate_kbps: int) -> float:
        """
        Calculate estimated file size in Megabytes (MB).
        Size (bytes) = (bitrate_kbps * 1000 / 8) * duration_seconds + MP3 header overhead (~1-2KB)
        MB = bytes / (1024 * 1024)
        """
        if duration_seconds <= 0 or bitrate_kbps <= 0:
            return 0.0
        bytes_est = (bitrate_kbps * 1000 / 8.0) * duration_seconds + 2048
        return round(bytes_est / (1024.0 * 1024.0), 2)
