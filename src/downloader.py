"""
Universal media stream and web video downloader for Bulk MP3 Studio.
Multi-strategy download engine:
  1. yt-dlp with user-supplied cookies file (most reliable for YouTube)
  2. yt-dlp with auto-detected browser cookies (Chrome/Edge/Firefox)
  3. pytubefix with PO token (alternative YouTube path)
  4. yt-dlp without auth (works for some platforms/videos)
  5. Direct HTTP streaming (for static media URLs, podcasts, etc.)
"""

import os
import tempfile
import urllib.parse
from pathlib import Path
from typing import Optional, Callable, Tuple, List

import requests
from src.logger import get_logger

logger = get_logger("downloader")

DEFAULT_TIMEOUT = (15.0, 60.0)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# YouTube host patterns
YOUTUBE_HOSTS = {"youtube.com", "youtu.be", "m.youtube.com", "www.youtube.com"}


def is_youtube_url(url: str) -> bool:
    """Return True if the URL is a YouTube video link."""
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.lower().lstrip("www.")
        return host in YOUTUBE_HOSTS or "youtube.com" in host or "youtu.be" in host
    except Exception:
        return False


def download_media_url(
    url: str,
    temp_dir: Optional[Path] = None,
    progress_callback: Optional[Callable[[int, Optional[int], Optional[float]], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
    cookies_file: Optional[str] = None,
) -> Tuple[bool, Optional[Path], str]:
    """
    Download media from any video or audio URL to a temporary local file.

    Strategy order:
    1. yt-dlp + user cookies file (if provided and file exists)
    2. yt-dlp + auto browser cookies (Chrome → Edge → Firefox)
    3. pytubefix (alternative YouTube engine)
    4. yt-dlp without auth
    5. Direct HTTP streaming

    Returns: (success: bool, downloaded_temp_path: Optional[Path], error_message: str)
    """
    if temp_dir is None:
        temp_dir = Path(tempfile.gettempdir()) / "BulkMP3Studio_Cache"
    temp_dir.mkdir(parents=True, exist_ok=True)

    youtube = is_youtube_url(url)

    # --- Strategy 1: yt-dlp + explicit cookies file ---
    if cookies_file and Path(cookies_file).is_file():
        logger.info(f"Trying yt-dlp with cookies file: {cookies_file}")
        ok, path, err = _download_with_ytdlp(
            url, temp_dir, progress_callback, is_cancelled,
            cookies_file=cookies_file
        )
        if ok:
            return True, path, ""
        if "cancelled" in err.lower():
            return False, None, "Download cancelled by user."
        logger.info(f"yt-dlp+cookies-file failed: {err}")

    # --- Strategy 2: yt-dlp + auto browser cookies ---
    for browser in ("chrome", "edge", "firefox", "opera", "brave"):
        logger.info(f"Trying yt-dlp with {browser} browser cookies...")
        ok, path, err = _download_with_ytdlp(
            url, temp_dir, progress_callback, is_cancelled,
            cookies_from_browser=browser
        )
        if ok:
            return True, path, ""
        if "cancelled" in err.lower():
            return False, None, "Download cancelled by user."
        if "sign in" in err.lower() or "bot" in err.lower() or "cookies" in err.lower():
            logger.info(f"yt-dlp+{browser} cookies: auth required, trying next...")
        elif "could not copy" in err.lower() or "decrypt" in err.lower() or "not found" in err.lower():
            logger.info(f"yt-dlp+{browser}: browser not available, skipping.")
            continue
        else:
            logger.info(f"yt-dlp+{browser} failed: {err[:100]}")
        break  # Only try next browser if the current one has no cookies or can't be read

    # --- Strategy 3: pytubefix (YouTube-specific alternative) ---
    if youtube:
        logger.info("Trying pytubefix for YouTube download...")
        ok, path, err = _download_with_pytubefix(url, temp_dir, progress_callback, is_cancelled)
        if ok:
            return True, path, ""
        if "cancelled" in err.lower():
            return False, None, "Download cancelled by user."
        logger.info(f"pytubefix failed: {err[:100]}")

    # --- Strategy 4: yt-dlp without auth (may work for non-restricted videos/platforms) ---
    logger.info("Trying yt-dlp without authentication...")
    ok, path, err = _download_with_ytdlp(url, temp_dir, progress_callback, is_cancelled)
    if ok:
        return True, path, ""
    if "cancelled" in err.lower():
        return False, None, "Download cancelled by user."

    ytdlp_final_err = err
    logger.info(f"yt-dlp no-auth failed: {err[:100]}")

    # --- Strategy 5: Direct HTTP streaming ---
    logger.info("Falling back to direct HTTP streaming...")
    ok, path, err = _download_direct_http(url, temp_dir, progress_callback, is_cancelled)
    if ok:
        return True, path, ""
    if "cancelled" in err.lower():
        return False, None, "Download cancelled by user."

    # All strategies failed — give a helpful error message
    if youtube and ("sign in" in ytdlp_final_err.lower() or "bot" in ytdlp_final_err.lower()):
        return False, None, (
            "YouTube requires authentication to download this video.\n\n"
            "FIX: Export your browser cookies as cookies.txt and add the file in\n"
            "Settings → YouTube Cookies File.\n\n"
            "Use the 'Get cookies.txt LOCALLY' browser extension to export.\n"
            f"(yt-dlp error: {ytdlp_final_err[:120]})"
        )

    return False, None, f"All download strategies failed.\nyt-dlp: {ytdlp_final_err[:120]}\nHTTP: {err[:80]}"


# ─────────────────────────────────────────────────────────────
# yt-dlp Engine
# ─────────────────────────────────────────────────────────────

def _download_with_ytdlp(
    url: str,
    temp_dir: Path,
    progress_callback: Optional[Callable] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
    cookies_file: Optional[str] = None,
    cookies_from_browser: Optional[str] = None,
) -> Tuple[bool, Optional[Path], str]:
    try:
        import yt_dlp
    except ImportError:
        return False, None, "yt-dlp not installed."

    downloaded_files: List[Path] = []

    def progress_hook(d):
        if is_cancelled and is_cancelled():
            raise Exception("CANCELLED_BY_USER")
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            pct = (downloaded / total * 100.0) if total else 20.0
            if progress_callback:
                progress_callback(downloaded, total, pct)
        elif status == "finished":
            fn = d.get("filename")
            if fn:
                downloaded_files.append(Path(fn))

    out_tmpl = str(temp_dir / "bulk_dl_%(id)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_tmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [progress_hook],
        "geo_bypass": True,
        "http_headers": {"User-Agent": USER_AGENT},
        "extractor_args": {
            "youtube": {
                "player_client": ["web_creator", "ios", "mweb"],
                "skip": ["translated_subs"],
            }
        },
    }

    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file
    elif cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Find the downloaded file
        for f in downloaded_files:
            if f.exists() and f.stat().st_size > 0:
                return True, f, ""

        # Glob for any recent file matching pattern
        candidates = sorted(
            temp_dir.glob("bulk_dl_*.*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if candidates and candidates[0].stat().st_size > 0:
            return True, candidates[0], ""

        return False, None, "No media file produced by yt-dlp."

    except Exception as e:
        msg = str(e)
        if "CANCELLED_BY_USER" in msg:
            return False, None, "Download cancelled by user."
        return False, None, msg


# ─────────────────────────────────────────────────────────────
# pytubefix Engine (YouTube-specific)
# ─────────────────────────────────────────────────────────────

def _download_with_pytubefix(
    url: str,
    temp_dir: Path,
    progress_callback: Optional[Callable] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> Tuple[bool, Optional[Path], str]:
    try:
        from pytubefix import YouTube
    except ImportError:
        return False, None, "pytubefix not installed."

    try:
        _downloaded_path: Optional[Path] = None
        _downloaded_bytes = [0]

        def on_progress(stream, chunk: bytes, remaining: int):
            if is_cancelled and is_cancelled():
                raise Exception("CANCELLED_BY_USER")
            size = stream.filesize
            _downloaded_bytes[0] += len(chunk)
            if size and progress_callback:
                pct = (_downloaded_bytes[0] / size) * 100.0
                progress_callback(_downloaded_bytes[0], size, pct)

        yt = YouTube(url, on_progress_callback=on_progress, use_oauth=False, allow_oauth_cache=False)
        title = yt.title or "youtube_media"

        # Best audio stream
        audio_stream = (
            yt.streams.filter(only_audio=True).order_by("abr").last()
            or yt.streams.filter(progressive=False).order_by("abr").last()
            or yt.streams.get_audio_only()
        )

        if not audio_stream:
            return False, None, "No audio stream found in pytubefix."

        # Download to temp_dir
        safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_"))[:60].strip()
        out_filename = f"pyfix_{safe_title}.{audio_stream.subtype or 'mp4'}"
        out_path = temp_dir / out_filename

        audio_stream.download(output_path=str(temp_dir), filename=out_filename)

        if out_path.exists() and out_path.stat().st_size > 0:
            return True, out_path, ""

        return False, None, "pytubefix download produced empty file."

    except Exception as e:
        msg = str(e)
        if "CANCELLED_BY_USER" in msg:
            return False, None, "Download cancelled by user."
        return False, None, msg


# ─────────────────────────────────────────────────────────────
# Direct HTTP Streaming Engine
# ─────────────────────────────────────────────────────────────

def _download_direct_http(
    url: str,
    temp_dir: Path,
    progress_callback: Optional[Callable] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> Tuple[bool, Optional[Path], str]:
    try:
        parsed = urllib.parse.urlparse(url)
        path_stem = Path(urllib.parse.unquote(parsed.path))
        suffix = path_stem.suffix if path_stem.suffix else ".media"
    except Exception:
        suffix = ".media"

    temp_file = None
    try:
        headers = {"User-Agent": USER_AGENT}
        with requests.get(url, headers=headers, stream=True, timeout=DEFAULT_TIMEOUT) as response:
            if response.status_code != 200:
                return False, None, f"HTTP Error {response.status_code}: {response.reason}"

            total_size_header = response.headers.get("content-length")
            total_size = int(total_size_header) if total_size_header and total_size_header.isdigit() else None

            fd, temp_path_str = tempfile.mkstemp(suffix=suffix, dir=str(temp_dir), prefix="bulk_mp3_")
            temp_file = Path(temp_path_str)

            downloaded_bytes = 0
            chunk_size = 64 * 1024

            with os.fdopen(fd, "wb") as f_out:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if is_cancelled and is_cancelled():
                        f_out.close()
                        if temp_file.exists():
                            temp_file.unlink()
                        return False, None, "Download cancelled by user."
                    if chunk:
                        f_out.write(chunk)
                        downloaded_bytes += len(chunk)
                        pct = (downloaded_bytes / total_size * 100.0) if total_size else None
                        if progress_callback:
                            progress_callback(downloaded_bytes, total_size, pct)

            if downloaded_bytes == 0:
                if temp_file.exists():
                    temp_file.unlink()
                return False, None, "Downloaded file was empty (0 bytes)."

            return True, temp_file, ""

    except requests.exceptions.Timeout:
        if temp_file and temp_file.exists():
            temp_file.unlink()
        return False, None, "Connection timed out while downloading media."
    except requests.exceptions.ConnectionError as ce:
        if temp_file and temp_file.exists():
            temp_file.unlink()
        return False, None, f"Network connection error: {ce}"
    except Exception as e:
        if temp_file and temp_file.exists():
            temp_file.unlink()
        return False, None, f"Download failed: {e}"
