from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class StarRatingWidget(QWidget):
    ratingChanged = Signal(int)

    def __init__(self, parent: QWidget | None = None, *, editable: bool = True):
        super().__init__(parent)
        self._rating = 0
        self._editable = editable
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.buttons: list[QPushButton] = []
        for index in range(1, 6):
            button = QPushButton("☆")
            button.setObjectName("starButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFixedSize(31, 31)
            button.setFlat(True)
            button.setEnabled(editable)
            button.clicked.connect(
                lambda _checked=False, value=index: self.set_rating(value, emit=True)
            )
            layout.addWidget(button)
            self.buttons.append(button)
        layout.addStretch(1)
        self._refresh()

    def rating(self) -> int:
        return self._rating

    def set_rating(self, rating: int, *, emit: bool = False) -> None:
        rating = max(0, min(5, int(rating)))
        if self._editable and rating == self._rating:
            rating = 0
        changed = rating != self._rating
        self._rating = rating
        self._refresh()
        if emit and changed:
            self.ratingChanged.emit(rating)

    def _refresh(self) -> None:
        for index, button in enumerate(self.buttons, start=1):
            button.setText("★" if index <= self._rating else "☆")
            button.setProperty("active", index <= self._rating)
            button.style().unpolish(button)
            button.style().polish(button)
