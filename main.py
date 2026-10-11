"""
Main application entry point for Bulk MP3 Studio.
"""

import os
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src.logger import setup_logging, get_logger
from src.ui.main_window import MainWindow

logger = get_logger("app")


def main():
    # Setup application logging
    setup_logging()
    logger.info("Starting Bulk MP3 Studio...")

    # Enable High DPI scaling
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QApplication(sys.argv)
    app.setApplicationName("Bulk MP3 Studio")
    app.setApplicationDisplayName("Bulk MP3 Studio")
    app.setOrganizationName("LocalAudio")
    app.setOrganizationDomain("localaudio.desktop")

    window = MainWindow()
    window.show()

    exit_code = app.exec()
    logger.info(f"Bulk MP3 Studio exited with code {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
