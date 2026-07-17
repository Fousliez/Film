from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from .widgets import StarRatingWidget


class WindowUiMixin:
    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(14)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(190)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 18, 14, 14)
        title = QLabel("FILMOTECA")
        title.setObjectName("appTitle")
        subtitle = QLabel("Filmy a seriály")
        subtitle.setObjectName("muted")
        sidebar_layout.addWidget(title)
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addSpacing(18)

        self.nav_buttons: dict[str, QPushButton] = {}
        for key, label in (
            ("all", "Vše"),
            ("movie", "Filmy"),
            ("series", "Seriály"),
            ("favorites", "Oblíbené"),
        ):
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, value=key: self.set_filter(value))
            sidebar_layout.addWidget(button)
            self.nav_buttons[key] = button
        self.nav_buttons["all"].setChecked(True)
        sidebar_layout.addStretch(1)

        about = QLabel("Lokální SQLite databáze\nbez účtu a bez cloudu")
        about.setObjectName("muted")
        about.setWordWrap(True)
        sidebar_layout.addWidget(about)
        root.addWidget(sidebar)

        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setChildrenCollapsible(False)
        root.addWidget(content_splitter, 1)

        list_panel = QFrame()
        list_panel.setObjectName("card")
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(14, 14, 14, 14)

        toolbar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Hledat název, původní název nebo žánr…")
        self.search_edit.textChanged.connect(self.refresh_items)
        add_button = QPushButton("＋ Přidat")
        add_button.setObjectName("primaryButton")
        add_button.clicked.connect(self.add_item)
        toolbar.addWidget(self.search_edit, 1)
        toolbar.addWidget(add_button)
        list_layout.addLayout(toolbar)

        self.items_table = QTableWidget(0, 6)
        self.items_table.setHorizontalHeaderLabels(
            ["Název", "Typ", "Rok", "Hodnocení", "Stav", "Soubory"]
        )
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for column in range(1, 6):
            self.items_table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        self.items_table.itemSelectionChanged.connect(self._on_item_selected)
        list_layout.addWidget(self.items_table, 1)
        content_splitter.addWidget(list_panel)

        detail_panel = QFrame()
        detail_panel.setObjectName("detailPanel")
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(16, 16, 16, 16)

        detail_header = QHBoxLayout()
        self.poster_label = QLabel("Bez plakátu")
        self.poster_label.setObjectName("posterPlaceholder")
        self.poster_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.poster_label.setFixedSize(150, 220)
        detail_header.addWidget(self.poster_label)

        heading_layout = QVBoxLayout()
        self.detail_title = QLabel("Vyber položku")
        self.detail_title.setObjectName("sectionTitle")
        self.detail_title.setWordWrap(True)
        self.detail_meta = QLabel(
            "Přidej film nebo seriál a lidská civilizace může pokračovat."
        )
        self.detail_meta.setObjectName("muted")
        self.detail_meta.setWordWrap(True)
        self.detail_rating = StarRatingWidget(editable=False)
        self.detail_status = QLabel("")
        self.detail_genres = QLabel("")
        self.detail_genres.setWordWrap(True)
        heading_layout.addWidget(self.detail_title)
        heading_layout.addWidget(self.detail_meta)
        heading_layout.addWidget(self.detail_rating)
        heading_layout.addWidget(self.detail_status)
        heading_layout.addWidget(self.detail_genres)
        heading_layout.addStretch(1)

        action_row = QHBoxLayout()
        self.edit_button = QPushButton("Upravit")
        self.edit_button.clicked.connect(self.edit_item)
        self.delete_button = QPushButton("Smazat")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(self.delete_item)
        action_row.addWidget(self.edit_button)
        action_row.addWidget(self.delete_button)
        action_row.addStretch(1)
        heading_layout.addLayout(action_row)
        detail_header.addLayout(heading_layout, 1)
        detail_layout.addLayout(detail_header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_overview_tab(), "Přehled")
        self.tabs.addTab(self._build_files_tab(), "Soubory")
        self.tabs.addTab(self._build_tracks_tab(), "Audio a titulky")
        detail_layout.addWidget(self.tabs, 1)
        content_splitter.addWidget(detail_panel)
        content_splitter.setSizes([660, 650])

        self.setCentralWidget(central)
        self._set_detail_enabled(False)

    def _build_overview_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        self.notes_label = QLabel("Žádné poznámky.")
        self.notes_label.setWordWrap(True)
        self.notes_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        layout.addWidget(QLabel("Poznámky"))
        layout.addWidget(self.notes_label, 1)
        return widget

    def _build_files_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        buttons = QHBoxLayout()
        self.add_file_button = QPushButton("＋ Přidat soubor")
        self.add_file_button.setObjectName("primaryButton")
        self.add_file_button.clicked.connect(self.add_media_file)
        self.rescan_file_button = QPushButton("Znovu analyzovat")
        self.rescan_file_button.clicked.connect(self.rescan_media_file)
        self.episode_button = QPushButton("Řada/epizoda")
        self.episode_button.clicked.connect(self.edit_episode_numbers)
        self.open_file_button = QPushButton("Otevřít")
        self.open_file_button.clicked.connect(self.open_media_file)
        self.remove_file_button = QPushButton("Odebrat")
        self.remove_file_button.setObjectName("dangerButton")
        self.remove_file_button.clicked.connect(self.remove_media_file)
        buttons.addWidget(self.add_file_button)
        buttons.addWidget(self.rescan_file_button)
        buttons.addWidget(self.episode_button)
        buttons.addWidget(self.open_file_button)
        buttons.addWidget(self.remove_file_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.files_table = QTableWidget(0, 10)
        self.files_table.setHorizontalHeaderLabels(
            [
                "Soubor",
                "S/E",
                "Kontejner",
                "Rozlišení",
                "Video",
                "FPS",
                "Délka",
                "Tok",
                "Velikost",
                "A/T",
            ]
        )
        self.files_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.files_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.files_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.files_table.verticalHeader().setVisible(False)
        self.files_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for column in range(1, 10):
            self.files_table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        self.files_table.itemSelectionChanged.connect(self._on_file_selected)
        layout.addWidget(self.files_table, 1)
        return widget

    def _build_tracks_tab(self) -> QWidget:
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(QLabel("Zvukové stopy"), 0, 0)
        layout.addWidget(QLabel("Titulky"), 0, 1)

        self.audio_table = QTableWidget(0, 7)
        self.audio_table.setHorizontalHeaderLabels(
            ["Jazyk", "Kodek", "Název", "Kanály", "Vzorkování", "Tok", "Výchozí"]
        )
        self.subtitle_table = QTableWidget(0, 5)
        self.subtitle_table.setHorizontalHeaderLabels(
            ["Jazyk", "Formát", "Název", "Výchozí", "Vynucené"]
        )
        for table in (self.audio_table, self.subtitle_table):
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
            table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.audio_table, 1, 0)
        layout.addWidget(self.subtitle_table, 1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        return widget
