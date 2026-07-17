from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .models import MediaItem
from .widgets import StarRatingWidget


class NullableSpinBox(QWidget):
    def __init__(self, minimum: int, maximum: int, suffix: str = "", parent=None):
        super().__init__(parent)
        self.spin = QSpinBox()
        self.spin.setRange(minimum - 1, maximum)
        self.spin.setSpecialValueText("—")
        self.spin.setValue(minimum - 1)
        self.spin.setSuffix(suffix)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.spin)

    def value_or_none(self) -> int | None:
        return None if self.spin.value() == self.spin.minimum() else self.spin.value()

    def set_optional_value(self, value: int | None) -> None:
        self.spin.setValue(self.spin.minimum() if value is None else value)


class ItemDialog(QDialog):
    def __init__(self, item: MediaItem | None = None, parent=None):
        super().__init__(parent)
        self.item = item or MediaItem()
        self.setWindowTitle("Upravit titul" if item else "Přidat film nebo seriál")
        self.setMinimumWidth(590)

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(11)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Povinný název")
        self.original_title_edit = QLineEdit()

        self.type_combo = QComboBox()
        self.type_combo.addItem("Film", "movie")
        self.type_combo.addItem("Seriál", "series")
        self.type_combo.currentIndexChanged.connect(self._update_series_fields)

        self.year_spin = NullableSpinBox(1870, 2200)
        self.seasons_spin = NullableSpinBox(1, 999)
        self.episodes_spin = NullableSpinBox(1, 99999)

        self.rating_widget = StarRatingWidget()
        self.status_combo = QComboBox()
        self.status_combo.addItem("Chci vidět", "planned")
        self.status_combo.addItem("Sleduji", "watching")
        self.status_combo.addItem("Zhlédnuto", "watched")
        self.favorite_check = QCheckBox("Oblíbené")

        self.genres_edit = QLineEdit()
        self.genres_edit.setPlaceholderText("např. sci-fi, thriller, komedie")
        self.country_edit = QLineEdit()
        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(100)

        self.poster_edit = QLineEdit()
        self.poster_edit.setReadOnly(True)
        poster_button = QPushButton("Vybrat…")
        poster_button.clicked.connect(self._choose_poster)
        poster_row = QWidget()
        poster_layout = QHBoxLayout(poster_row)
        poster_layout.setContentsMargins(0, 0, 0, 0)
        poster_layout.addWidget(self.poster_edit, 1)
        poster_layout.addWidget(poster_button)

        form.addRow("Název:", self.title_edit)
        form.addRow("Původní název:", self.original_title_edit)
        form.addRow("Typ:", self.type_combo)
        form.addRow("Rok:", self.year_spin)
        form.addRow("Počet řad:", self.seasons_spin)
        form.addRow("Počet epizod:", self.episodes_spin)
        form.addRow("Hodnocení:", self.rating_widget)
        form.addRow("Stav:", self.status_combo)
        form.addRow("", self.favorite_check)
        form.addRow("Žánry:", self.genres_edit)
        form.addRow("Země:", self.country_edit)
        form.addRow("Plakát:", poster_row)
        form.addRow("Poznámky:", self.notes_edit)
        root.addLayout(form)

        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: #ff8f8f;")
        root.addWidget(self.validation_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Uložit")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Zrušit")
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._load_item()

    def _load_item(self) -> None:
        self.title_edit.setText(self.item.title)
        self.original_title_edit.setText(self.item.original_title)
        self.type_combo.setCurrentIndex(0 if self.item.media_type == "movie" else 1)
        self.year_spin.set_optional_value(self.item.year)
        self.seasons_spin.set_optional_value(self.item.seasons)
        self.episodes_spin.set_optional_value(self.item.episodes)
        self.rating_widget.set_rating(self.item.rating)
        status_index = self.status_combo.findData(self.item.status)
        self.status_combo.setCurrentIndex(max(0, status_index))
        self.favorite_check.setChecked(self.item.favorite)
        self.genres_edit.setText(self.item.genres)
        self.country_edit.setText(self.item.country)
        self.notes_edit.setPlainText(self.item.notes)
        self.poster_edit.setText(self.item.poster_path)
        self._update_series_fields()

    def _update_series_fields(self) -> None:
        is_series = self.type_combo.currentData() == "series"
        self.seasons_spin.setEnabled(is_series)
        self.episodes_spin.setEnabled(is_series)

    def _choose_poster(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Vybrat plakát",
            str(Path.home()),
            "Obrázky (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if path:
            self.poster_edit.setText(path)

    def _validate_and_accept(self) -> None:
        if not self.title_edit.text().strip():
            self.validation_label.setText("Název nesmí být prázdný.")
            self.title_edit.setFocus()
            return
        self.accept()

    def build_item(self) -> MediaItem:
        media_type = str(self.type_combo.currentData())
        return MediaItem(
            id=self.item.id,
            title=self.title_edit.text().strip(),
            original_title=self.original_title_edit.text().strip(),
            media_type=media_type,
            year=self.year_spin.value_or_none(),
            seasons=self.seasons_spin.value_or_none() if media_type == "series" else None,
            episodes=self.episodes_spin.value_or_none() if media_type == "series" else None,
            rating=self.rating_widget.rating(),
            status=str(self.status_combo.currentData()),
            favorite=self.favorite_check.isChecked(),
            genres=self.genres_edit.text().strip(),
            country=self.country_edit.text().strip(),
            notes=self.notes_edit.toPlainText().strip(),
            poster_path=self.poster_edit.text().strip(),
            created_at=self.item.created_at,
            updated_at=self.item.updated_at,
        )


class EpisodeDialog(QDialog):
    def __init__(
        self, season_number: int | None = None, episode_number: int | None = None, parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Řada a epizoda")
        self.setMinimumWidth(340)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.season_spin = NullableSpinBox(1, 999)
        self.episode_spin = NullableSpinBox(1, 99999)
        self.season_spin.set_optional_value(season_number)
        self.episode_spin.set_optional_value(episode_number)
        form.addRow("Řada:", self.season_spin)
        form.addRow("Epizoda:", self.episode_spin)
        root.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Uložit")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Zrušit")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def values(self) -> tuple[int | None, int | None]:
        return self.season_spin.value_or_none(), self.episode_spin.value_or_none()
