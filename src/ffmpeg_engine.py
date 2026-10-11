"""
FFmpeg media processing engine for Bulk MP3 Studio.
Handles executable resolution, metadata probing, command generation with argument arrays,
real-time progress monitoring via pipe:1, and clean cancellation.
"""

import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Tuple, Callable

from src.logger import get_logger

logger = get_logger("ffmpeg_engine")

DURATION_REGEX = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
OUT_TIME_US_REGEX = re.compile(r"^out_time_us=(\d+)")
OUT_TIME_MS_REGEX = re.compile(r"^out_time_ms=(\d+)")


class FFmpegNotFoundError(Exception):
    """Raised when no valid FFmpeg executable could be located."""
    pass


class FFmpegConversionError(Exception):
    """Raised when FFmpeg conversion fails with non-zero exit code or error output."""
    pass


def find_ffmpeg_binary(custom_path: Optional[str] = None) -> Optional[str]:
    """
    Locate FFmpeg executable using cascading search:
    1. Custom path specified by the user
    2. Bundled exe in PyInstaller _MEIPASS or app directory
    3. System PATH ('ffmpeg' or 'ffmpeg.exe')
    4. imageio-ffmpeg library bundled binary
    """
    # 1. Custom path
    if custom_path and custom_path.strip():
        p = Path(custom_path.strip().strip('"'))
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)

    # 2. Bundled in PyInstaller extraction dir
    if hasattr(sys, "_MEIPASS"):
        meipass_ffmpeg = Path(sys._MEIPASS) / "ffmpeg.exe"
        if meipass_ffmpeg.is_file():
            return str(meipass_ffmpeg)

    # 3. Bundled in local bin/ folder adjacent to main script
    app_dir = Path(__file__).resolve().parent.parent
    local_candidates = [
        app_dir / "bin" / "ffmpeg.exe",
        app_dir / "ffmpeg.exe",
    ]
    for cand in local_candidates:
        if cand.is_file():
            return str(cand)

    # 4. System PATH
    path_ffmpeg = shutil.which("ffmpeg")
    if path_ffmpeg:
        return path_ffmpeg

    # 5. imageio-ffmpeg fallback
    try:
        import imageio_ffmpeg
        img_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        if img_ffmpeg and Path(img_ffmpeg).is_file():
            return str(img_ffmpeg)
    except Exception:
        pass

    return None


def get_ffmpeg_version_info(ffmpeg_exe: str) -> Tuple[bool, str]:
    """Test running the given FFmpeg binary and extract version information."""
    if not ffmpeg_exe or not Path(ffmpeg_exe).is_file():
        return False, "Executable path does not exist."

    try:
        res = subprocess.run(
            [ffmpeg_exe, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5.0,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if res.returncode == 0:
            first_line = res.stdout.splitlines()[0] if res.stdout else "FFmpeg ready"
            return True, first_line
        return False, f"FFmpeg returned code {res.returncode}"
    except subprocess.TimeoutExpired:
        return False, "FFmpeg version check timed out."
    except Exception as e:
        return False, f"Failed to execute FFmpeg: {e}"


def probe_media_duration(ffmpeg_exe: str, media_path: Path) -> Optional[float]:
    """
    Probe the duration in seconds of a local media file using FFmpeg stderr output.
    Returns duration in seconds (float) or None if cannot be determined.
    """
    if not media_path.exists():
        return None

    try:
        cmd = [ffmpeg_exe, "-i", str(media_path)]
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=8.0,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        # Duration is emitted to stderr by ffmpeg
        match = DURATION_REGEX.search(res.stderr)
        if match:
            h, m, s = match.groups()
            duration_sec = int(h) * 3600 + int(m) * 60 + float(s)
            return duration_sec
    except Exception as e:
        logger.warning(f"Could not probe duration for {media_path}: {e}")
    return None


def build_ffmpeg_args(
    ffmpeg_exe: str,
    input_path: Path,
    output_path: Path,
    bitrate_kbps: int = 64,
    channels: str = "stereo",
    sample_rate: str = "auto"
) -> list:
    """Build a robust argument array for FFmpeg conversion without shell concatenation."""
    cmd = [
        ffmpeg_exe,
        "-y",               # Overwrite target because collision resolution is handled before calling
        "-i", str(input_path),
        "-vn",              # Disable video stream (audio extraction)
        "-c:a", "libmp3lame",
        "-b:a", f"{bitrate_kbps}k"
    ]

    if channels == "mono":
        cmd.extend(["-ac", "1"])
    elif channels == "stereo":
        cmd.extend(["-ac", "2"])

    if sample_rate in ("44100", "48000", "22050"):
        cmd.extend(["-ar", sample_rate])

    # Enable machine-readable progress output
    cmd.extend([
        "-progress", "pipe:1",
        "-nostats",
        str(output_path)
    ])

    return cmd


def convert_audio_file(
    ffmpeg_exe: str,
    input_path: Path,
    output_path: Path,
    bitrate_kbps: int = 64,
    channels: str = "stereo",
    sample_rate: str = "auto",
    total_duration: Optional[float] = None,
    progress_callback: Optional[Callable[[float, float, Optional[float]], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None
) -> Tuple[bool, str]:
    """
    Convert an input audio/video file to MP3 at the specified bitrate.
    Streams progress in real time via pipe:1 and supports immediate cancellation.
    Returns (success: bool, error_message: str).
    """
    if not Path(ffmpeg_exe).is_file():
        raise FFmpegNotFoundError(f"FFmpeg binary not found at '{ffmpeg_exe}'")

    if not input_path.exists():
        return False, f"Input media file does not exist: {input_path}"

    # If duration wasn't supplied, probe it
    if total_duration is None or total_duration <= 0:
        total_duration = probe_media_duration(ffmpeg_exe, input_path)

    cmd = build_ffmpeg_args(
        ffmpeg_exe=ffmpeg_exe,
        input_path=input_path,
        output_path=output_path,
        bitrate_kbps=bitrate_kbps,
        channels=channels,
        sample_rate=sample_rate
    )

    logger.info(f"Starting conversion: {' '.join(cmd[:6])} ... -> {output_path.name}")

    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    proc = None
    stderr_lines = []

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            shell=False,
            creationflags=creationflags
        )

        def read_stderr():
            try:
                for line in proc.stderr:
                    stderr_lines.append(line)
            except Exception:
                pass

        err_thread = threading.Thread(target=read_stderr, daemon=True)
        err_thread.start()

        last_progress_time = 0.0

        # Read machine-readable stdout progress lines
        for line in proc.stdout:
            if is_cancelled and is_cancelled():
                logger.info(f"Cancellation requested for {output_path.name}")
                proc.terminate()
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                # Clean up partial output file
                if output_path.exists():
                    try:
                        output_path.unlink()
                    except Exception:
                        pass
                return False, "Conversion cancelled by user."

            line = line.strip()
            # Match out_time_us (microseconds) or out_time_ms
            match_us = OUT_TIME_US_REGEX.match(line)
            if match_us:
                us = int(match_us.group(1))
                curr_sec = us / 1_000_000.0
                now = time.time()
                if now - last_progress_time >= 0.1:  # Throttle updates to 10Hz
                    last_progress_time = now
                    if total_duration and total_duration > 0:
                        pct = min(100.0, (curr_sec / total_duration) * 100.0)
                    else:
                        pct = 0.0
                    if progress_callback:
                        progress_callback(pct, curr_sec, total_duration)

        proc.stdout.close()
        return_code = proc.wait()
        err_thread.join(timeout=2.0)

        if return_code != 0:
            error_details = "".join(stderr_lines[-10:])
            msg = f"FFmpeg failed (exit code {return_code}): {error_details.strip()}"
            logger.error(msg)
            # Remove failed output file
            if output_path.exists():
                try:
                    output_path.unlink()
                except Exception:
                    pass
            return False, msg

        # Final 100% notification
        if progress_callback:
            progress_callback(100.0, total_duration or 0.0, total_duration)

        logger.info(f"Successfully converted {output_path.name}")
        return True, ""

    except Exception as e:
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass
        if output_path.exists():
            try:
                output_path.unlink()
            except Exception:
                pass
        logger.error(f"Error during audio conversion: {e}")
        return False, str(e)
