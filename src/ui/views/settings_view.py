"""
Settings View for Bulk MP3 Studio.
Configures FFmpeg discovery, audio encoding defaults, overwrite behavior,
concurrency, and includes a live scrolling log viewer.
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QFrame, QFileDialog, QMessageBox, QSpinBox,
    QPlainTextEdit, QScrollArea, QApplication
)
from PySide6.QtCore import Qt, Signal

from src.config import ConfigManager, VALID_BITRATES, BITRATE_PRESETS
from src.ffmpeg_engine import (
    find_ffmpeg_binary,
    get_ffmpeg_version_info
)
from src.logger import (
    get_recent_logs,
    add_log_listener,
    remove_log_listener,
    clear_recent_logs,
    get_log_file_path
)
from src.utils import open_file_in_default_app


class SettingsView(QWidget):
    """Configuration interface for media engine, defaults, and live logs."""

    ffmpeg_status_changed = Signal(bool, str)

    def __init__(self, config_mgr: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_mgr = config_mgr

        self._build_ui()
        self._load_values()
        add_log_listener(self._on_new_log_message)

    def closeEvent(self, event):
        remove_log_listener(self._on_new_log_message)
        super().closeEvent(event)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.setSpacing(20)

        # 1. FFmpeg Configuration Card
        ffmpeg_card = QFrame()
        ffmpeg_card.setObjectName("cardFrame")
        ff_layout = QVBoxLayout(ffmpeg_card)
        ff_layout.setContentsMargins(20, 18, 20, 18)
        ff_layout.setSpacing(12)

        ff_title = QLabel("FFmpeg Media Engine")
        ff_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        ff_desc = QLabel(
            "Bulk MP3 Studio requires FFmpeg to extract audio and encode MP3 files. "
            "You can specify a custom binary or use the automatically discovered path."
        )
        ff_desc.setWordWrap(True)
        ff_desc.setStyleSheet("font-size: 12px; color: #94a3b8;")
        ff_layout.addWidget(ff_title)
        ff_layout.addWidget(ff_desc)

        ff_path_row = QHBoxLayout()
        ff_path_row.setSpacing(8)

        self.ffmpeg_path_input = QLineEdit()
        self.ffmpeg_path_input.setPlaceholderText("Auto-detected or custom path to ffmpeg.exe...")

        btn_detect = QPushButton("Auto-Detect")
        btn_detect.clicked.connect(self._on_auto_detect_ffmpeg)

        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._on_browse_ffmpeg)

        btn_test = QPushButton("⚡ Test FFmpeg")
        btn_test.setObjectName("primaryBtn")
        btn_test.clicked.connect(self._on_test_ffmpeg)

        ff_path_row.addWidget(self.ffmpeg_path_input, 1)
        ff_path_row.addWidget(btn_detect)
        ff_path_row.addWidget(btn_browse)
        ff_path_row.addWidget(btn_test)
        ff_layout.addLayout(ff_path_row)

        self.ffmpeg_status_lbl = QLabel()
        self.ffmpeg_status_lbl.setStyleSheet("font-size: 12px; font-weight: 600;")
        ff_layout.addWidget(self.ffmpeg_status_lbl)

        layout.addWidget(ffmpeg_card)

        # 2. YouTube / Video Cookies Configuration Card
        cookies_card = QFrame()
        cookies_card.setObjectName("cardFrame")
        ck_layout = QVBoxLayout(cookies_card)
        ck_layout.setContentsMargins(20, 18, 20, 18)
        ck_layout.setSpacing(10)

        ck_title = QLabel("🍪 YouTube & Video Site Authentication")
        ck_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        ck_layout.addWidget(ck_title)

        ck_desc = QLabel(
            "YouTube now requires authentication for yt-dlp downloads. "
            "Export your browser cookies to a <b>cookies.txt</b> file and select it here. "
            "This enables downloading any YouTube video you can view in your browser."
        )
        ck_desc.setWordWrap(True)
        ck_desc.setStyleSheet("font-size: 12px; color: #94a3b8;")
        ck_layout.addWidget(ck_desc)

        # How-to guide
        guide_frame = QFrame()
        guide_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(6, 182, 212, 0.07);
                border: 1px solid rgba(6, 182, 212, 0.2);
                border-radius: 6px;
                padding: 4px;
            }
        """)
        guide_layout = QVBoxLayout(guide_frame)
        guide_layout.setContentsMargins(12, 8, 12, 8)
        guide_layout.setSpacing(3)
        guide_lbl = QLabel(
            "<b>How to export cookies:</b><br>"
            "1. Install the <i>'Get cookies.txt LOCALLY'</i> extension in Chrome/Edge/Firefox<br>"
            "2. Visit <b>youtube.com</b> while signed in to your Google account<br>"
            "3. Click the extension icon → Export as <b>cookies.txt</b><br>"
            "4. Save the file anywhere and select it below<br>"
            "<br>"
            "💡 <i>Your cookies are stored only locally and never uploaded anywhere.</i>"
        )
        guide_lbl.setWordWrap(True)
        guide_lbl.setStyleSheet("font-size: 11px; color: #94a3b8; line-height: 1.5;")
        guide_layout.addWidget(guide_lbl)
        ck_layout.addWidget(guide_frame)

        ck_path_row = QHBoxLayout()
        ck_path_row.setSpacing(8)

        self.cookies_file_input = QLineEdit()
        self.cookies_file_input.setPlaceholderText("Path to cookies.txt (optional, enables YouTube auth)...")
        self.cookies_file_input.setReadOnly(True)

        btn_browse_cookies = QPushButton("📂 Browse...")
        btn_browse_cookies.setCursor(Qt.PointingHandCursor)
        btn_browse_cookies.clicked.connect(self._on_browse_cookies_file)

        btn_clear_cookies = QPushButton("✖ Clear")
        btn_clear_cookies.setCursor(Qt.PointingHandCursor)
        btn_clear_cookies.clicked.connect(self._on_clear_cookies_file)

        ck_path_row.addWidget(self.cookies_file_input, 1)
        ck_path_row.addWidget(btn_browse_cookies)
        ck_path_row.addWidget(btn_clear_cookies)
        ck_layout.addLayout(ck_path_row)

        self.cookies_status_lbl = QLabel("No cookies file configured.")
        self.cookies_status_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
        ck_layout.addWidget(self.cookies_status_lbl)

        layout.addWidget(cookies_card)

        defaults_card = QFrame()
        defaults_card.setObjectName("cardFrame")
        d_layout = QVBoxLayout(defaults_card)
        d_layout.setContentsMargins(20, 18, 20, 18)
        d_layout.setSpacing(14)

        d_title = QLabel("Audio Encoding Defaults")
        d_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        d_layout.addWidget(d_title)

        grid_row = QHBoxLayout()
        grid_row.setSpacing(16)

        # Default Bitrate
        col1 = QVBoxLayout()
        lbl1 = QLabel("Default Bitrate Preset:")
        lbl1.setStyleSheet("font-size: 12px; font-weight: 600; color: #cbd5e1;")
        self.bitrate_combo = QComboBox()
        for p in BITRATE_PRESETS:
            self.bitrate_combo.addItem(f"{p['label']} — {p['description']}", p["bitrate"])
        col1.addWidget(lbl1)
        col1.addWidget(self.bitrate_combo)
        grid_row.addLayout(col1)

        # Audio Channels
        col2 = QVBoxLayout()
        lbl2 = QLabel("Audio Channels:")
        lbl2.setStyleSheet("font-size: 12px; font-weight: 600; color: #cbd5e1;")
        self.channels_combo = QComboBox()
        self.channels_combo.addItem("Stereo (2 Channels)", "stereo")
        self.channels_combo.addItem("Mono (1 Channel - Half MB)", "mono")
        col2.addWidget(lbl2)
        col2.addWidget(self.channels_combo)
        grid_row.addLayout(col2)

        # Sample Rate
        col3 = QVBoxLayout()
        lbl3 = QLabel("Sampling Rate:")
        lbl3.setStyleSheet("font-size: 12px; font-weight: 600; color: #cbd5e1;")
        self.samplerate_combo = QComboBox()
        self.samplerate_combo.addItem("Auto (Source Match)", "auto")
        self.samplerate_combo.addItem("44.1 kHz (CD Standard)", "44100")
        self.samplerate_combo.addItem("48.0 kHz (Studio Audio)", "48000")
        self.samplerate_combo.addItem("22.05 kHz (Low Bitrate Speech)", "22050")
        col3.addWidget(lbl3)
        col3.addWidget(self.samplerate_combo)
        grid_row.addLayout(col3)

        d_layout.addLayout(grid_row)
        layout.addWidget(defaults_card)

        # 3. File System & Concurrency Card
        fs_card = QFrame()
        fs_card.setObjectName("cardFrame")
        fs_layout = QVBoxLayout(fs_card)
        fs_layout.setContentsMargins(20, 18, 20, 18)
        fs_layout.setSpacing(14)

        fs_title = QLabel("Output Files & Performance")
        fs_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        fs_layout.addWidget(fs_title)

        # Output Directory
        fs_out_lbl = QLabel("Default Output Directory:")
        fs_out_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #cbd5e1;")
        fs_layout.addWidget(fs_out_lbl)

        out_row = QHBoxLayout()
        self.out_dir_input = QLineEdit()
        self.out_dir_input.setReadOnly(True)
        btn_browse_out = QPushButton("Browse Folder...")
        btn_browse_out.clicked.connect(self._on_browse_output_dir)
        out_row.addWidget(self.out_dir_input, 1)
        out_row.addWidget(btn_browse_out)
        fs_layout.addLayout(out_row)

        perf_row = QHBoxLayout()
        perf_row.setSpacing(16)

        # Overwrite Policy
        col_pol = QVBoxLayout()
        pol_lbl = QLabel("File Overwrite Policy:")
        pol_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #cbd5e1;")
        self.policy_combo = QComboBox()
        self.policy_combo.addItem("Auto-rename with suffix (_1, _2) [Safest]", "rename")
        self.policy_combo.addItem("Skip existing files", "skip")
        self.policy_combo.addItem("Overwrite existing files", "overwrite")
        col_pol.addWidget(pol_lbl)
        col_pol.addWidget(self.policy_combo)
        perf_row.addLayout(col_pol)

        # Parallel Concurrency
        col_conc = QVBoxLayout()
        conc_lbl = QLabel("Parallel Conversion Workers:")
        conc_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #cbd5e1;")
        self.conc_spin = QSpinBox()
        self.conc_spin.setRange(1, 4)
        self.conc_spin.setValue(2)
        col_conc.addWidget(conc_lbl)
        col_conc.addWidget(self.conc_spin)
        perf_row.addLayout(col_conc)

        fs_layout.addLayout(perf_row)
        layout.addWidget(fs_card)

        # 4. Live Log Viewer Card
        log_card = QFrame()
        log_card.setObjectName("cardFrame")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(20, 18, 20, 18)
        log_layout.setSpacing(10)

        log_header = QHBoxLayout()
        log_title = QLabel("Application Logs & Troubleshooting")
        log_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        log_header.addWidget(log_title)
        log_header.addStretch()

        btn_copy_logs = QPushButton("Copy Logs")
        btn_copy_logs.clicked.connect(self._on_copy_logs)

        btn_open_logfile = QPushButton("Open Log File")
        btn_open_logfile.clicked.connect(self._on_open_logfile)

        btn_clear_view = QPushButton("Clear View")
        btn_clear_view.clicked.connect(self._on_clear_log_view)

        log_header.addWidget(btn_copy_logs)
        log_header.addWidget(btn_open_logfile)
        log_header.addWidget(btn_clear_view)
        log_layout.addLayout(log_header)

        self.log_text_edit = QPlainTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setFixedHeight(160)
        self.log_text_edit.setStyleSheet("""
            QPlainTextEdit {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                background-color: #0b111e;
                color: #cbd5e1;
            }
        """)
        # Populate initial logs
        for l in get_recent_logs():
            self.log_text_edit.appendPlainText(l)
        log_layout.addWidget(self.log_text_edit)

        layout.addWidget(log_card)

        # Save Button Bar
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()
        self.btn_save_all = QPushButton("💾 Save Preferences")
        self.btn_save_all.setObjectName("primaryBtn")
        self.btn_save_all.setFixedHeight(38)
        self.btn_save_all.setFixedWidth(180)
        self.btn_save_all.setCursor(Qt.PointingHandCursor)
        self.btn_save_all.clicked.connect(self._save_values)
        btn_bar.addWidget(self.btn_save_all)
        layout.addLayout(btn_bar)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _load_values(self):
        s = self.config_mgr.settings

        # FFmpeg
        detected = find_ffmpeg_binary(s.ffmpeg_custom_path)
        self.ffmpeg_path_input.setText(s.ffmpeg_custom_path or (detected or ""))
        self._check_and_update_ffmpeg_display(detected)

        # Cookies file
        cf = getattr(s, "cookies_file", "") or ""
        self.cookies_file_input.setText(cf)
        self._update_cookies_status(cf)

        # Bitrate
        idx = self.bitrate_combo.findData(s.default_bitrate)
        if idx >= 0:
            self.bitrate_combo.setCurrentIndex(idx)

        # Channels
        idx_ch = self.channels_combo.findData(s.audio_channels)
        if idx_ch >= 0:
            self.channels_combo.setCurrentIndex(idx_ch)

        # Sample rate
        idx_sr = self.samplerate_combo.findData(s.sample_rate)
        if idx_sr >= 0:
            self.samplerate_combo.setCurrentIndex(idx_sr)

        # Output Dir
        self.out_dir_input.setText(s.output_directory)

        # Policy
        idx_p = self.policy_combo.findData(s.overwrite_policy)
        if idx_p >= 0:
            self.policy_combo.setCurrentIndex(idx_p)

        # Concurrency
        self.conc_spin.setValue(s.concurrency)

    def _save_values(self):
        s = self.config_mgr.settings
        s.ffmpeg_custom_path = self.ffmpeg_path_input.text().strip()
        s.default_bitrate = self.bitrate_combo.currentData()
        s.audio_channels = self.channels_combo.currentData()
        s.sample_rate = self.samplerate_combo.currentData()
        s.output_directory = self.out_dir_input.text().strip()
        s.overwrite_policy = self.policy_combo.currentData()
        s.concurrency = self.conc_spin.value()
        s.cookies_file = self.cookies_file_input.text().strip()

        self.config_mgr.save()

        # Update FFmpeg status
        detected = find_ffmpeg_binary(s.ffmpeg_custom_path)
        self._check_and_update_ffmpeg_display(detected)

        QMessageBox.information(self, "Settings Saved", "Preferences have been successfully updated.")

    def _check_and_update_ffmpeg_display(self, binary_path: str):
        if binary_path and Path(binary_path).exists():
            ok, info = get_ffmpeg_version_info(binary_path)
            if ok:
                self.ffmpeg_status_lbl.setText(f"✅ Ready: {info}")
                self.ffmpeg_status_lbl.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 600;")
                self.ffmpeg_status_changed.emit(True, info)
                return

        self.ffmpeg_status_lbl.setText("❌ FFmpeg binary could not be found or executed.")
        self.ffmpeg_status_lbl.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: 600;")
        self.ffmpeg_status_changed.emit(False, "")

    def _on_auto_detect_ffmpeg(self):
        detected = find_ffmpeg_binary()
        if detected:
            self.ffmpeg_path_input.setText(detected)
            self._check_and_update_ffmpeg_display(detected)
            QMessageBox.information(self, "Auto-Detection", f"Found FFmpeg at:\n{detected}")
        else:
            QMessageBox.warning(self, "Not Found", "Could not locate FFmpeg automatically.")

    def _on_browse_ffmpeg(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select FFmpeg Executable",
            "",
            "Executable Files (*.exe);;All Files (*.*)"
        )
        if file_path:
            self.ffmpeg_path_input.setText(file_path)
            self._check_and_update_ffmpeg_display(file_path)

    def _on_test_ffmpeg(self):
        candidate = self.ffmpeg_path_input.text().strip()
        exe = find_ffmpeg_binary(candidate)
        if not exe:
            QMessageBox.critical(self, "FFmpeg Test Failed", "No valid FFmpeg executable could be located.")
            return

        ok, info = get_ffmpeg_version_info(exe)
        if ok:
            QMessageBox.information(
                self,
                "FFmpeg Test Succeeded",
                f"Successfully executed FFmpeg!\n\nPath: {exe}\n\nVersion: {info}"
            )
            self._check_and_update_ffmpeg_display(exe)
        else:
            QMessageBox.critical(self, "FFmpeg Test Failed", f"Execution failed:\n{info}")

    def _on_browse_output_dir(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Default Output Directory",
            self.out_dir_input.text()
        )
        if folder:
            self.out_dir_input.setText(folder)

    def _on_browse_cookies_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select YouTube Cookies File (cookies.txt)",
            "",
            "Cookies Files (*.txt);;All Files (*.*)"
        )
        if file_path:
            self.cookies_file_input.setText(file_path)
            self._update_cookies_status(file_path)

    def _on_clear_cookies_file(self):
        self.cookies_file_input.clear()
        self._update_cookies_status("")

    def _update_cookies_status(self, path: str):
        if path and Path(path).is_file():
            size = Path(path).stat().st_size
            self.cookies_status_lbl.setText(f"✅ Cookies file loaded: {Path(path).name} ({size:,} bytes)")
            self.cookies_status_lbl.setStyleSheet("font-size: 11px; color: #10b981; font-weight: 600;")
        elif path:
            self.cookies_status_lbl.setText(f"❌ File not found: {path}")
            self.cookies_status_lbl.setStyleSheet("font-size: 11px; color: #ef4444;")
        else:
            self.cookies_status_lbl.setText("No cookies file configured. YouTube downloads may fail without one.")
            self.cookies_status_lbl.setStyleSheet("font-size: 11px; color: #64748b;")

    def _on_new_log_message(self, msg: str):
        self.log_text_edit.appendPlainText(msg)

    def _on_copy_logs(self):
        text = self.log_text_edit.toPlainText()
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "Application logs copied to clipboard.")

    def _on_open_logfile(self):
        log_file = get_log_file_path()
        if log_file.exists():
            open_file_in_default_app(log_file)
        else:
            QMessageBox.information(self, "No Log File", "Log file has not been created yet.")

    def _on_clear_log_view(self):
        self.log_text_edit.clear()
        clear_recent_logs()
