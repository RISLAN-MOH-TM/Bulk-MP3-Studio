"""
PyInstaller packaging script for Bulk MP3 Studio.
Builds a standalone Windows executable and bundles FFmpeg if available.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from src.ffmpeg_engine import find_ffmpeg_binary


def build_application(mode: str = "onedir"):
    """
    Build Bulk MP3 Studio executable using PyInstaller.
    :param mode: 'onedir' (recommended for fast launch and bundling) or 'onefile'
    """
    root_dir = Path(__file__).resolve().parent
    main_script = root_dir / "main.py"
    dist_dir = root_dir / "dist"
    build_dir = root_dir / "build"

    print(f"==================================================")
    print(f"Building Bulk MP3 Studio (Mode: {mode})")
    print(f"==================================================")

    # Locate FFmpeg binary to bundle
    ffmpeg_exe = find_ffmpeg_binary()
    print(f"Found FFmpeg executable: {ffmpeg_exe or 'None (will require system FFmpeg)'}")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "BulkMP3Studio",
        "--clean",
        "--noconfirm",
        "--windowed", # No black console window
    ]

    if mode == "onedir":
        cmd.append("--onedir")
    else:
        cmd.append("--onefile")

    # Add data / imports if necessary
    cmd.extend([
        "--hidden-import", "PySide6",
        "--hidden-import", "PySide6.QtCore",
        "--hidden-import", "PySide6.QtGui",
        "--hidden-import", "PySide6.QtWidgets",
        "--hidden-import", "sqlite3",
        "--hidden-import", "requests",
        "--hidden-import", "imageio_ffmpeg",
        "--hidden-import", "yt_dlp",
        str(main_script)
    ])

    print("Running PyInstaller command:")
    print(" ".join(cmd))

    res = subprocess.run(cmd, cwd=str(root_dir))
    if res.returncode != 0:
        print(f"PyInstaller build failed with exit code {res.returncode}", file=sys.stderr)
        return False

    print("\nPyInstaller compilation completed successfully!")

    # If mode is onedir, copy ffmpeg.exe into dist/BulkMP3Studio/bin/
    if mode == "onedir" and ffmpeg_exe and Path(ffmpeg_exe).is_file():
        target_bin = dist_dir / "BulkMP3Studio" / "bin"
        target_bin.mkdir(parents=True, exist_ok=True)
        target_ffmpeg = target_bin / "ffmpeg.exe"
        try:
            print(f"Bundling FFmpeg binary to: {target_ffmpeg}")
            shutil.copy2(ffmpeg_exe, target_ffmpeg)
            print("FFmpeg binary bundled successfully.")
        except Exception as e:
            print(f"Warning: Could not copy FFmpeg to dist: {e}")

    print("\n--------------------------------------------------")
    print(f"Output available in: {dist_dir}")
    print("--------------------------------------------------")
    return True


if __name__ == "__main__":
    mode_arg = "onedir"
    if len(sys.argv) > 1 and sys.argv[1] in ("onedir", "onefile"):
        mode_arg = sys.argv[1]
    success = build_application(mode=mode_arg)
    sys.exit(0 if success else 1)
