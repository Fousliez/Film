from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication

from .database import MediaRepository
from .main_window import MainWindow
from .styles import APP_STYLESHEET


def get_data_dir() -> Path:
    location = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    data_dir = Path(location) if location else Path.home() / ".filmoteca"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Filmoteca")
    app.setOrganizationName("Fousliez")
    app.setStyleSheet(APP_STYLESHEET)
    data_dir = get_data_dir()
    repository = MediaRepository(data_dir / "filmoteca.sqlite3")
    window = MainWindow(repository, data_dir)
    window.show()
    return app.exec()
