from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MediaItem:
    id: int | None = None
    title: str = ""
    original_title: str = ""
    media_type: str = "movie"
    year: int | None = None
    seasons: int | None = None
    episodes: int | None = None
    rating: int = 0
    status: str = "planned"
    favorite: bool = False
    genres: str = ""
    country: str = ""
    notes: str = ""
    poster_path: str = ""
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_row(cls, row: Any) -> "MediaItem":
        values = dict(row)
        values["favorite"] = bool(values.get("favorite", 0))
        return cls(**values)


@dataclass(slots=True)
class AudioTrack:
    stream_index: int = 0
    language: str = "und"
    title: str = ""
    codec: str = ""
    channels: int | None = None
    channel_layout: str = ""
    sample_rate: int | None = None
    bitrate: int | None = None
    is_default: bool = False


@dataclass(slots=True)
class SubtitleTrack:
    stream_index: int = 0
    language: str = "und"
    title: str = ""
    codec: str = ""
    is_default: bool = False
    is_forced: bool = False


@dataclass(slots=True)
class MediaFile:
    id: int | None = None
    media_id: int | None = None
    path: str = ""
    display_name: str = ""
    season_number: int | None = None
    episode_number: int | None = None
    duration_seconds: float | None = None
    size_bytes: int | None = None
    container: str = ""
    video_codec: str = ""
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    video_bitrate: int | None = None
    overall_bitrate: int | None = None
    scanned_at: str = ""
    audio_tracks: list[AudioTrack] = field(default_factory=list)
    subtitle_tracks: list[SubtitleTrack] = field(default_factory=list)

    @property
    def resolution(self) -> str:
        if self.width and self.height:
            return f"{self.width}×{self.height}"
        return "—"
