from __future__ import annotations

import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTableWidgetItem,
)

from .database import MediaRepository
from .dialogs import EpisodeDialog, ItemDialog
from .formatting import format_bitrate, format_duration, format_size
from .media_probe import ProbeError, probe_media
from .window_ui import WindowUiMixin


STATUS_LABELS = {
    "planned": "Chci vidět",
    "watching": "Sleduji",
    "watched": "Zhlédnuto",
}


class MainWindow(WindowUiMixin, QMainWindow):
    def __init__(self, repository: MediaRepository, data_dir: Path):
        super().__init__()
        self.repository = repository
        self.data_dir = data_dir
        self.selected_item_id: int | None = None
        self.selected_file_id: int | None = None
        self.current_filter = "all"

        self.setWindowTitle("Filmoteca")
        self.setMinimumSize(1180, 720)
        self.resize(1450, 860)
        self._build_ui()
        self.refresh_items()

    def set_filter(self, value: str) -> None:
        self.current_filter = value
        for key, button in self.nav_buttons.items():
            button.setChecked(key == value)
        self.refresh_items()

    def refresh_items(self) -> None:
        media_type = self.current_filter if self.current_filter in {"movie", "series"} else None
        favorite_only = self.current_filter == "favorites"
        items = self.repository.list_items(
            search=self.search_edit.text() if hasattr(self, "search_edit") else "",
            media_type=media_type,
            favorite_only=favorite_only,
        )
        previously_selected = self.selected_item_id
        self.items_table.blockSignals(True)
        self.items_table.setRowCount(0)
        for row_index, item in enumerate(items):
            self.items_table.insertRow(row_index)
            title = f"★ {item.title}" if item.favorite else item.title
            values = [
                title,
                "Film" if item.media_type == "movie" else "Seriál",
                str(item.year or "—"),
                "★" * item.rating + "☆" * (5 - item.rating),
                STATUS_LABELS.get(item.status, item.status),
                str(len(self.repository.list_files(item.id or 0))),
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole, item.id)
                self.items_table.setItem(row_index, column, cell)
        self.items_table.blockSignals(False)

        visible_ids = {item.id for item in items}
        if items and previously_selected in visible_ids:
            self._select_item_by_id(previously_selected)
        elif items:
            self.selected_item_id = None
            self.items_table.selectRow(0)
        else:
            self.selected_item_id = None
            self.clear_detail()

    def _on_item_selected(self) -> None:
        selected = self.items_table.selectedItems()
        if not selected:
            return
        item_id = selected[0].data(Qt.ItemDataRole.UserRole)
        self.selected_item_id = int(item_id)
        self.load_detail()

    def load_detail(self) -> None:
        if self.selected_item_id is None:
            self.clear_detail()
            return
        item = self.repository.get_item(self.selected_item_id)
        if item is None:
            self.clear_detail()
            return

        self._set_detail_enabled(True)
        self.detail_title.setText(item.title)
        type_label = "Film" if item.media_type == "movie" else "Seriál"
        original = f" · {item.original_title}" if item.original_title else ""
        series_info = ""
        if item.media_type == "series":
            bits = []
            if item.seasons:
                bits.append(f"{item.seasons} řad")
            if item.episodes:
                bits.append(f"{item.episodes} epizod")
            series_info = f" · {', '.join(bits)}" if bits else ""
        self.detail_meta.setText(
            f"{type_label} · {item.year or 'rok neuveden'}{series_info}{original}"
        )
        self.detail_rating.set_rating(item.rating)
        favorite = " · Oblíbené" if item.favorite else ""
        self.detail_status.setText(
            f"{STATUS_LABELS.get(item.status, item.status)}{favorite}"
        )
        self.detail_genres.setText(
            " · ".join(filter(None, [item.genres, item.country]))
            or "Bez žánru a země"
        )
        self.notes_label.setText(item.notes or "Žádné poznámky.")
        self._set_poster(item.poster_path)
        self.refresh_files()

    def clear_detail(self) -> None:
        self.detail_title.setText("Vyber položku")
        self.detail_meta.setText("Seznam je zatím prázdný nebo filtr nic nenašel.")
        self.detail_rating.set_rating(0)
        self.detail_status.clear()
        self.detail_genres.clear()
        self.notes_label.setText("Žádné poznámky.")
        self.poster_label.setPixmap(QPixmap())
        self.poster_label.setText("Bez plakátu")
        self.files_table.setRowCount(0)
        self.audio_table.setRowCount(0)
        self.subtitle_table.setRowCount(0)
        self._set_detail_enabled(False)

    def _set_detail_enabled(self, enabled: bool) -> None:
        for widget in (
            self.edit_button,
            self.delete_button,
            self.add_file_button,
            self.tabs,
        ):
            widget.setEnabled(enabled)
        self._set_file_actions_enabled(False)

    def _set_file_actions_enabled(self, enabled: bool) -> None:
        for widget in (
            self.rescan_file_button,
            self.episode_button,
            self.open_file_button,
            self.remove_file_button,
        ):
            widget.setEnabled(enabled)

    def _set_poster(self, path: str) -> None:
        pixmap = QPixmap(path) if path and Path(path).is_file() else QPixmap()
        if pixmap.isNull():
            self.poster_label.setPixmap(QPixmap())
            self.poster_label.setText("Bez plakátu")
            return
        self.poster_label.setText("")
        self.poster_label.setPixmap(
            pixmap.scaled(
                self.poster_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def add_item(self) -> None:
        dialog = ItemDialog(parent=self)
        if dialog.exec() != ItemDialog.DialogCode.Accepted:
            return
        item = dialog.build_item()
        item.poster_path = self._store_poster(item.poster_path)
        self.selected_item_id = self.repository.add_item(item)
        self.refresh_items()
        self._select_item_by_id(self.selected_item_id)

    def edit_item(self) -> None:
        if self.selected_item_id is None:
            return
        item = self.repository.get_item(self.selected_item_id)
        if item is None:
            return
        original_poster = item.poster_path
        dialog = ItemDialog(item, self)
        if dialog.exec() != ItemDialog.DialogCode.Accepted:
            return
        updated = dialog.build_item()
        if updated.poster_path != original_poster:
            updated.poster_path = self._store_poster(updated.poster_path)
        self.repository.update_item(updated)
        self.refresh_items()
        self._select_item_by_id(updated.id)
        self.load_detail()

    def delete_item(self) -> None:
        if self.selected_item_id is None:
            return
        item = self.repository.get_item(self.selected_item_id)
        if item is None:
            return
        answer = QMessageBox.question(
            self,
            "Smazat položku",
            f"Opravdu smazat „{item.title}“ včetně všech přiřazených souborů a stop?\n\n"
            "Skutečné video soubory na disku se nesmažou.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.repository.delete_item(self.selected_item_id)
        self.selected_item_id = None
        self.refresh_items()

    def _store_poster(self, source: str) -> str:
        if not source:
            return ""
        source_path = Path(source)
        if not source_path.is_file():
            return source
        poster_dir = self.data_dir / "posters"
        poster_dir.mkdir(parents=True, exist_ok=True)
        try:
            if source_path.resolve().parent == poster_dir.resolve():
                return str(source_path)
        except OSError:
            pass
        destination = poster_dir / f"{uuid.uuid4().hex}{source_path.suffix.lower()}"
        try:
            shutil.copy2(source_path, destination)
            return str(destination)
        except OSError:
            return source

    def _select_item_by_id(self, item_id: int | None) -> None:
        if item_id is None:
            return
        for row in range(self.items_table.rowCount()):
            cell = self.items_table.item(row, 0)
            if cell and cell.data(Qt.ItemDataRole.UserRole) == item_id:
                self.items_table.clearSelection()
                self.items_table.setCurrentCell(row, 0)
                self.items_table.selectRow(row)
                return

    def refresh_files(self) -> None:
        self.files_table.blockSignals(True)
        self.files_table.setRowCount(0)
        self.selected_file_id = None
        self._set_file_actions_enabled(False)
        self.audio_table.setRowCount(0)
        self.subtitle_table.setRowCount(0)
        if self.selected_item_id is None:
            self.files_table.blockSignals(False)
            return

        files = self.repository.list_files(self.selected_item_id)
        for row_index, media_file in enumerate(files):
            self.files_table.insertRow(row_index)
            season_episode = "—"
            if (
                media_file.season_number is not None
                or media_file.episode_number is not None
            ):
                season_episode = (
                    f"S{media_file.season_number or 0:02d}"
                    f"E{media_file.episode_number or 0:02d}"
                )
            audio_count = len(self.repository.get_audio_tracks(media_file.id or 0))
            subtitle_count = len(
                self.repository.get_subtitle_tracks(media_file.id or 0)
            )
            values = [
                media_file.display_name,
                season_episode,
                media_file.container or "—",
                media_file.resolution,
                media_file.video_codec or "—",
                f"{media_file.fps:.3g}" if media_file.fps else "—",
                format_duration(media_file.duration_seconds),
                format_bitrate(media_file.overall_bitrate),
                format_size(media_file.size_bytes),
                f"{audio_count}/{subtitle_count}",
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole, media_file.id)
                cell.setToolTip(media_file.path)
                self.files_table.setItem(row_index, column, cell)
        self.files_table.blockSignals(False)
        if files:
            self.files_table.selectRow(0)

    def add_media_file(self) -> None:
        if self.selected_item_id is None:
            return
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Vybrat video soubory",
            str(Path.home()),
            "Video (*.mkv *.mp4 *.avi *.mov *.wmv *.m4v *.webm *.ts *.m2ts);;"
            "Všechny soubory (*)",
        )
        if not paths:
            return
        errors: list[str] = []
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for path in paths:
                try:
                    data = probe_media(path)
                    self.repository.add_file(self.selected_item_id, data)
                except Exception as exc:
                    errors.append(f"{Path(path).name}: {exc}")
        finally:
            QApplication.restoreOverrideCursor()
        self.refresh_files()
        self.refresh_items()
        if errors:
            QMessageBox.warning(
                self,
                "Některé soubory se nepodařilo přidat",
                "\n".join(errors),
            )

    def _on_file_selected(self) -> None:
        selected = self.files_table.selectedItems()
        if not selected:
            self.selected_file_id = None
            self._set_file_actions_enabled(False)
            return
        self.selected_file_id = int(selected[0].data(Qt.ItemDataRole.UserRole))
        self._set_file_actions_enabled(True)
        self.load_tracks()

    def load_tracks(self) -> None:
        self.audio_table.setRowCount(0)
        self.subtitle_table.setRowCount(0)
        if self.selected_file_id is None:
            return

        audio_tracks = self.repository.get_audio_tracks(self.selected_file_id)
        for row_index, track in enumerate(audio_tracks):
            self.audio_table.insertRow(row_index)
            values = [
                track.language,
                track.codec or "—",
                track.title or "—",
                track.channel_layout
                or (str(track.channels) if track.channels else "—"),
                f"{track.sample_rate / 1000:.1f} kHz"
                if track.sample_rate
                else "—",
                format_bitrate(track.bitrate),
                "Ano" if track.is_default else "Ne",
            ]
            for column, value in enumerate(values):
                self.audio_table.setItem(
                    row_index, column, QTableWidgetItem(value)
                )

        subtitle_tracks = self.repository.get_subtitle_tracks(self.selected_file_id)
        for row_index, track in enumerate(subtitle_tracks):
            self.subtitle_table.insertRow(row_index)
            values = [
                track.language,
                track.codec or "—",
                track.title or "—",
                "Ano" if track.is_default else "Ne",
                "Ano" if track.is_forced else "Ne",
            ]
            for column, value in enumerate(values):
                self.subtitle_table.setItem(
                    row_index, column, QTableWidgetItem(value)
                )

    def rescan_media_file(self) -> None:
        if self.selected_file_id is None:
            return
        existing = self.repository.get_file(self.selected_file_id)
        if existing is None:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            rescanned = probe_media(existing.path)
            rescanned.season_number = existing.season_number
            rescanned.episode_number = existing.episode_number
            self.repository.replace_file_metadata(existing.id or 0, rescanned)
        except ProbeError as exc:
            QMessageBox.critical(self, "Analýza selhala", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.refresh_files()

    def edit_episode_numbers(self) -> None:
        if self.selected_file_id is None:
            return
        media_file = self.repository.get_file(self.selected_file_id)
        if media_file is None:
            return
        dialog = EpisodeDialog(
            media_file.season_number,
            media_file.episode_number,
            self,
        )
        if dialog.exec() != EpisodeDialog.DialogCode.Accepted:
            return
        season_number, episode_number = dialog.values()
        self.repository.update_episode_numbers(
            self.selected_file_id,
            season_number,
            episode_number,
        )
        self.refresh_files()

    def remove_media_file(self) -> None:
        if self.selected_file_id is None:
            return
        media_file = self.repository.get_file(self.selected_file_id)
        if media_file is None:
            return
        answer = QMessageBox.question(
            self,
            "Odebrat soubor",
            f"Odebrat „{media_file.display_name}“ z databáze?\n"
            "Skutečný soubor na disku zůstane beze změny.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.repository.delete_file(self.selected_file_id)
        self.refresh_files()
        self.refresh_items()

    def open_media_file(self) -> None:
        if self.selected_file_id is None:
            return
        media_file = self.repository.get_file(self.selected_file_id)
        if media_file is None or not Path(media_file.path).exists():
            QMessageBox.warning(
                self,
                "Soubor nenalezen",
                "Původní soubor už na této cestě není.",
            )
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(media_file.path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", media_file.path])
            else:
                subprocess.Popen(["xdg-open", media_file.path])
        except OSError as exc:
            QMessageBox.critical(self, "Soubor nelze otevřít", str(exc))
