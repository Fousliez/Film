from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .models import AudioTrack, MediaFile, MediaItem, SubtitleTrack


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS media_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    original_title TEXT NOT NULL DEFAULT '',
    media_type TEXT NOT NULL CHECK (media_type IN ('movie', 'series')),
    year INTEGER,
    seasons INTEGER,
    episodes INTEGER,
    rating INTEGER NOT NULL DEFAULT 0 CHECK (rating BETWEEN 0 AND 5),
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'watching', 'watched')),
    favorite INTEGER NOT NULL DEFAULT 0,
    genres TEXT NOT NULL DEFAULT '',
    country TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    poster_path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS media_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    season_number INTEGER,
    episode_number INTEGER,
    duration_seconds REAL,
    size_bytes INTEGER,
    container TEXT NOT NULL DEFAULT '',
    video_codec TEXT NOT NULL DEFAULT '',
    width INTEGER,
    height INTEGER,
    fps REAL,
    video_bitrate INTEGER,
    overall_bitrate INTEGER,
    scanned_at TEXT NOT NULL,
    UNIQUE(media_id, path)
);

CREATE TABLE IF NOT EXISTS audio_tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES media_files(id) ON DELETE CASCADE,
    stream_index INTEGER NOT NULL,
    language TEXT NOT NULL DEFAULT 'und',
    title TEXT NOT NULL DEFAULT '',
    codec TEXT NOT NULL DEFAULT '',
    channels INTEGER,
    channel_layout TEXT NOT NULL DEFAULT '',
    sample_rate INTEGER,
    bitrate INTEGER,
    is_default INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS subtitle_tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES media_files(id) ON DELETE CASCADE,
    stream_index INTEGER NOT NULL,
    language TEXT NOT NULL DEFAULT 'und',
    title TEXT NOT NULL DEFAULT '',
    codec TEXT NOT NULL DEFAULT '',
    is_default INTEGER NOT NULL DEFAULT 0,
    is_forced INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_media_items_title ON media_items(title);
CREATE INDEX IF NOT EXISTS idx_media_items_type ON media_items(media_type);
CREATE INDEX IF NOT EXISTS idx_media_files_media_id ON media_files(media_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class MediaRepository:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(SCHEMA)

    def list_items(
        self,
        *,
        search: str = "",
        media_type: str | None = None,
        favorite_only: bool = False,
    ) -> list[MediaItem]:
        conditions: list[str] = []
        parameters: list[Any] = []
        if search.strip():
            conditions.append("(title LIKE ? OR original_title LIKE ? OR genres LIKE ?)")
            term = f"%{search.strip()}%"
            parameters.extend([term, term, term])
        if media_type in {"movie", "series"}:
            conditions.append("media_type = ?")
            parameters.append(media_type)
        if favorite_only:
            conditions.append("favorite = 1")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT * FROM media_items
            {where_clause}
            ORDER BY favorite DESC, rating DESC, title COLLATE NOCASE ASC
        """
        with self.connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [MediaItem.from_row(row) for row in rows]

    def get_item(self, item_id: int) -> MediaItem | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM media_items WHERE id = ?", (item_id,)
            ).fetchone()
        return MediaItem.from_row(row) if row else None

    def add_item(self, item: MediaItem) -> int:
        timestamp = _now()
        values = self._item_values(item)
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO media_items (
                    title, original_title, media_type, year, seasons, episodes,
                    rating, status, favorite, genres, country, notes, poster_path,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (*values, timestamp, timestamp),
            )
            return int(cursor.lastrowid)

    def update_item(self, item: MediaItem) -> None:
        if item.id is None:
            raise ValueError("Položka nemá ID.")
        with self.connection() as connection:
            connection.execute(
                """
                UPDATE media_items SET
                    title = ?, original_title = ?, media_type = ?, year = ?,
                    seasons = ?, episodes = ?, rating = ?, status = ?, favorite = ?,
                    genres = ?, country = ?, notes = ?, poster_path = ?, updated_at = ?
                WHERE id = ?
                """,
                (*self._item_values(item), _now(), item.id),
            )

    def delete_item(self, item_id: int) -> None:
        with self.connection() as connection:
            connection.execute("DELETE FROM media_items WHERE id = ?", (item_id,))

    @staticmethod
    def _item_values(item: MediaItem) -> tuple[Any, ...]:
        return (
            item.title.strip(),
            item.original_title.strip(),
            item.media_type,
            item.year,
            item.seasons,
            item.episodes,
            max(0, min(5, int(item.rating))),
            item.status,
            int(item.favorite),
            item.genres.strip(),
            item.country.strip(),
            item.notes.strip(),
            item.poster_path.strip(),
        )

    def list_files(self, media_id: int) -> list[MediaFile]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM media_files
                WHERE media_id = ?
                ORDER BY COALESCE(season_number, 0), COALESCE(episode_number, 0), display_name
                """,
                (media_id,),
            ).fetchall()
        return [self._file_from_row(row) for row in rows]

    def get_file(self, file_id: int) -> MediaFile | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM media_files WHERE id = ?", (file_id,)
            ).fetchone()
        return self._file_from_row(row) if row else None

    def add_file(self, media_id: int, media_file: MediaFile) -> int:
        timestamp = _now()
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO media_files (
                    media_id, path, display_name, season_number, episode_number,
                    duration_seconds, size_bytes, container, video_codec, width, height,
                    fps, video_bitrate, overall_bitrate, scanned_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    media_id,
                    media_file.path,
                    media_file.display_name,
                    media_file.season_number,
                    media_file.episode_number,
                    media_file.duration_seconds,
                    media_file.size_bytes,
                    media_file.container,
                    media_file.video_codec,
                    media_file.width,
                    media_file.height,
                    media_file.fps,
                    media_file.video_bitrate,
                    media_file.overall_bitrate,
                    timestamp,
                ),
            )
            file_id = int(cursor.lastrowid)
            self._insert_tracks(connection, file_id, media_file)
            return file_id

    def replace_file_metadata(self, file_id: int, media_file: MediaFile) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                UPDATE media_files SET
                    path = ?, display_name = ?, season_number = ?, episode_number = ?,
                    duration_seconds = ?, size_bytes = ?, container = ?, video_codec = ?,
                    width = ?, height = ?, fps = ?, video_bitrate = ?, overall_bitrate = ?,
                    scanned_at = ?
                WHERE id = ?
                """,
                (
                    media_file.path,
                    media_file.display_name,
                    media_file.season_number,
                    media_file.episode_number,
                    media_file.duration_seconds,
                    media_file.size_bytes,
                    media_file.container,
                    media_file.video_codec,
                    media_file.width,
                    media_file.height,
                    media_file.fps,
                    media_file.video_bitrate,
                    media_file.overall_bitrate,
                    _now(),
                    file_id,
                ),
            )
            connection.execute("DELETE FROM audio_tracks WHERE file_id = ?", (file_id,))
            connection.execute("DELETE FROM subtitle_tracks WHERE file_id = ?", (file_id,))
            self._insert_tracks(connection, file_id, media_file)

    def update_episode_numbers(
        self, file_id: int, season_number: int | None, episode_number: int | None
    ) -> None:
        with self.connection() as connection:
            connection.execute(
                "UPDATE media_files SET season_number = ?, episode_number = ? WHERE id = ?",
                (season_number, episode_number, file_id),
            )

    def delete_file(self, file_id: int) -> None:
        with self.connection() as connection:
            connection.execute("DELETE FROM media_files WHERE id = ?", (file_id,))

    def get_audio_tracks(self, file_id: int) -> list[AudioTrack]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM audio_tracks WHERE file_id = ? ORDER BY stream_index",
                (file_id,),
            ).fetchall()
        return [
            AudioTrack(
                stream_index=row["stream_index"],
                language=row["language"],
                title=row["title"],
                codec=row["codec"],
                channels=row["channels"],
                channel_layout=row["channel_layout"],
                sample_rate=row["sample_rate"],
                bitrate=row["bitrate"],
                is_default=bool(row["is_default"]),
            )
            for row in rows
        ]

    def get_subtitle_tracks(self, file_id: int) -> list[SubtitleTrack]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM subtitle_tracks WHERE file_id = ? ORDER BY stream_index",
                (file_id,),
            ).fetchall()
        return [
            SubtitleTrack(
                stream_index=row["stream_index"],
                language=row["language"],
                title=row["title"],
                codec=row["codec"],
                is_default=bool(row["is_default"]),
                is_forced=bool(row["is_forced"]),
            )
            for row in rows
        ]

    @staticmethod
    def _file_from_row(row: sqlite3.Row) -> MediaFile:
        return MediaFile(
            id=row["id"],
            media_id=row["media_id"],
            path=row["path"],
            display_name=row["display_name"],
            season_number=row["season_number"],
            episode_number=row["episode_number"],
            duration_seconds=row["duration_seconds"],
            size_bytes=row["size_bytes"],
            container=row["container"],
            video_codec=row["video_codec"],
            width=row["width"],
            height=row["height"],
            fps=row["fps"],
            video_bitrate=row["video_bitrate"],
            overall_bitrate=row["overall_bitrate"],
            scanned_at=row["scanned_at"],
        )

    @staticmethod
    def _insert_tracks(
        connection: sqlite3.Connection, file_id: int, media_file: MediaFile
    ) -> None:
        connection.executemany(
            """
            INSERT INTO audio_tracks (
                file_id, stream_index, language, title, codec, channels,
                channel_layout, sample_rate, bitrate, is_default
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    file_id,
                    track.stream_index,
                    track.language,
                    track.title,
                    track.codec,
                    track.channels,
                    track.channel_layout,
                    track.sample_rate,
                    track.bitrate,
                    int(track.is_default),
                )
                for track in media_file.audio_tracks
            ],
        )
        connection.executemany(
            """
            INSERT INTO subtitle_tracks (
                file_id, stream_index, language, title, codec, is_default, is_forced
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    file_id,
                    track.stream_index,
                    track.language,
                    track.title,
                    track.codec,
                    int(track.is_default),
                    int(track.is_forced),
                )
                for track in media_file.subtitle_tracks
            ],
        )
