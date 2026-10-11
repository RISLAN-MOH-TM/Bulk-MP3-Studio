# Bulk MP3 Studio — Local Audio Conversion & Batch Manager

**Bulk MP3 Studio** is a modern, high-performance Windows desktop application built with **Python 3.12+**, **PySide6**, **FFmpeg**, and **SQLite**. It offers batch media queue management, multi-line URL ingestion, local file drag-and-drop, and low-MB MP3 audio conversion (32, 48, 64, 96, and 128 kbps).

---

## Key Features

1. **Modern Dark UI**:
   - Sleek glassmorphism-inspired dark theme with slate/indigo/cyan accents.
   - Four dedicated modules: **Dashboard**, **Batch Queue**, **Job History**, and **Settings**.
   - Top header with live FFmpeg status indicator, queue pill, and output directory launcher.

2. **Bulk Input Manager**:
   - **Multiline URL Input**: Paste multiple authorized direct media URLs (one per line).
   - **TXT File Import**: Load batch lists from text files with comment (`#`) and empty line filtering.
   - **Local File Drag & Drop**: Drop audio or video files directly onto the UI or browse with the multi-file picker.
   - Supported input formats: `.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`, `.ogg`, `.opus`, `.wma`, `.aiff`, `.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.webm`, `.flv`, `.m4v`, and more.

3. **Compliant URL & Syntax Validation**:
   - URL scheme and syntax verification.
   - In-batch and cross-queue **duplicate detection**.
   - **Copyright & Platform Restriction Guard**: Proactively identifies proprietary streaming platforms (e.g., YouTube, Spotify, TikTok) that restrict direct extraction under DRM and platform terms, providing clear educational messages and directing users to direct authorized media streams or local media files.

4. **Low-MB Bitrate Presets**:
   - **32 kbps**: Ultra Compact (Voice notes, audiobooks, lectures — ~0.24 MB/min)
   - **48 kbps**: Compact (Talk radio, podcasts — ~0.35 MB/min)
   - **64 kbps (Recommended)**: Balanced Low-MB (Standard podcasts, background audio — ~0.47 MB/min)
   - **96 kbps**: Good Quality (Mobile music, mixed media — ~0.70 MB/min)
   - **128 kbps**: Standard Quality (High-fidelity music — ~0.94 MB/min)
   - Real-time estimated output file size display.

5. **Safe File Collision & Output Management**:
   - Custom output directory selector with one-click File Explorer integration.
   - Windows filename sanitization (strips invalid characters `<>:"/\|?*` and reserved names like `CON`, `NUL`).
   - Configurable overwrite policies:
     - **Auto-rename**: Automatically increments suffixes (`track_1.mp3`, `track_2.mp3`).
     - **Skip existing**: Prevents redundant re-conversion.
     - **Overwrite**: Replaces existing files.

6. **Batch Queue & Multithreaded Execution**:
   - Asynchronous background execution using `QThreadPool` and `QRunnable` (UI never freezes).
   - Real-time conversion percentage parsed directly from FFmpeg `-progress pipe:1`.
   - Comprehensive controls: **Start Batch**, **Pause/Resume Queue**, **Cancel Individual Job**, **Cancel All**, **Retry Failed**, and **Clear Completed**.

7. **Persistent SQLite Job History**:
   - Automatically records all completed and failed conversions with timestamps, source paths, output paths, file sizes, durations, and error details.
   - Search by keyword and filter by status (`COMPLETED`, `FAILED`).
   - Actions to launch output files in default player or reveal in File Explorer.
   - Export history to **CSV**.

8. **FFmpeg Engine Diagnostics & Settings**:
   - Cascading FFmpeg auto-detection (Custom path → Bundled executable → System PATH → `imageio-ffmpeg`).
   - Built-in "Test FFmpeg" diagnostic tool.
   - Configurable concurrency (1 to 4 worker threads), audio channels (Stereo/Mono), and sample rates.
   - Live streaming in-app log viewer and persistent log file (`bulk_mp3_studio.log`).

---

## Technology Stack

| Component | Technology |
|---|---|
| **Language** | Python 3.12+ |
| **Desktop UI** | PySide6 (Qt 6.12 for Python) |
| **Media Engine** | FFmpeg (Direct subprocess execution with argument arrays) |
| **Concurrency** | `QThreadPool`, `QRunnable`, and `QObject` signals |
| **Persistence** | SQLite (Thread-safe history database) + JSON (Settings) |
| **Packaging** | PyInstaller (Windows portable executable) |

---

## Directory Structure

```
bulk-mp3-studio/
├── src/
│   ├── __init__.py
│   ├── config.py              # Settings persistence (JSON) & bitrate presets
│   ├── database.py            # SQLite database schema, history queries, statistics
│   ├── downloader.py          # Safe HTTP/HTTPS stream downloader with progress & cancellation
│   ├── ffmpeg_engine.py       # FFmpeg resolution, duration probing, command runner, pipe:1 parser
│   ├── logger.py              # File logger and live UI log ring buffer
│   ├── queue_manager.py       # Batch state machine, QThreadPool concurrency, signals
│   ├── utils.py               # Filename sanitization, collision handling, size formatters
│   ├── validator.py           # URL validation, platform restrictions, duplicate detection
│   └── ui/
│       ├── __init__.py
│       ├── theme.py           # Dark UI stylesheet, color tokens
│       ├── main_window.py     # Main application window & responsive navigation
│       ├── widgets/
│       │   ├── drop_zone.py   # Drag & drop local media area
│       │   ├── header.py      # Top status bar with FFmpeg & queue pills
│       │   ├── sidebar.py     # Sidebar navigation menu with badge counter
│       │   ├── stat_card.py   # Dashboard metric summary cards
│       │   └── status_badge.py# Status chip widgets
│       └── views/
│           ├── dashboard_view.py # Input aggregation, presets, quick conversion
│           ├── queue_view.py     # Batch queue table, progress bars, pause/cancel/retry
│           ├── history_view.py   # SQLite history table, search, CSV export
│           └── settings_view.py  # FFmpeg diagnostics, preferences, live log viewer
├── tests/
│   ├── test_config.py         # Bitrate presets & settings validation tests
│   ├── test_database.py       # SQLite CRUD & statistics tests
│   ├── test_ffmpeg_engine.py  # Command generation, probing, synthetic conversion tests
│   ├── test_integration_flow.py # End-to-end batch conversion test
│   ├── test_queue_manager.py  # Queue states, item cancellation, retries tests
│   ├── test_ui.py             # UI views, page switching, table rendering tests
│   ├── test_utils.py          # Sanitization, collision resolution, formatting tests
│   └── test_validator.py      # URL syntax, copyright guard, duplicate detection tests
├── build_exe.py               # PyInstaller build automation script
├── main.py                    # Application entry point
├── requirements.txt           # Dependencies
└── README.md                  # Complete documentation
```

---

## Installation & Setup

### 1. Prerequisites
- Windows 10 or 11 (64-bit)
- Python 3.12 or newer

### 2. Clone or Extract Project
Navigate to the project directory:
```powershell
cd c:\Users\User\User\Desktop\mp3
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. FFmpeg Setup
Bulk MP3 Studio automatically detects FFmpeg through several mechanisms:
1. **Auto-included**: When `imageio-ffmpeg` is installed, the app detects and uses its bundled FFmpeg binary automatically.
2. **System PATH**: If FFmpeg is already installed on your machine (`ffmpeg.exe` in PATH).
3. **Local Folder**: Place `ffmpeg.exe` in the application folder or inside `bin/ffmpeg.exe`.
4. **Custom Path**: Open **Settings** within the application and select your `ffmpeg.exe` path using the file browser.

To install FFmpeg globally via Windows Package Manager:
```powershell
winget install Gyan.FFmpeg
```

---

## Running the Application

Launch the desktop application directly:
```powershell
python main.py
```

---

## Running Unit & Integration Tests

The test suite covers bitrate presets, filename collisions, input validation, queue states, database persistence, FFmpeg argument generation, UI navigation, and end-to-end audio conversion:
```powershell
pytest -v
```

All tests run locally in seconds without requiring network access.

---

## Building the Windows Executable

To compile Bulk MP3 Studio into a standalone Windows executable:

### Option A: Onedir Package (Recommended)
Builds the application into `dist/BulkMP3Studio/` and automatically bundles the FFmpeg executable:
```powershell
python build_exe.py onedir
```
Run the generated executable:
```powershell
.\dist\BulkMP3Studio\BulkMP3Studio.exe
```

### Option B: Single File Executable
```powershell
python build_exe.py onefile
```

---

## Troubleshooting & Logs

- **Log File Location**:
  `%APPDATA%\BulkMP3Studio\logs\bulk_mp3_studio.log`
- **Settings File**:
  `%APPDATA%\BulkMP3Studio\config.json`
- **Database History**:
  `%APPDATA%\BulkMP3Studio\history.db`
- **Live Logs**: Open the **Settings** tab in the application to view real-time logs, copy them to clipboard, or open the log file directly in Notepad.
