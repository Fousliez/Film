from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import AudioTrack, MediaFile, SubtitleTrack


class ProbeError(RuntimeError):
    """Chyba při čtení technických údajů média."""


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_fraction(value: Any) -> float | None:
    if value in (None, "", "0/0"):
        return None
    text = str(value)
    if "/" not in text:
        return _to_float(text)
    numerator, denominator = text.split("/", 1)
    try:
        denominator_value = float(denominator)
        return float(numerator) / denominator_value if denominator_value else None
    except ValueError:
        return None


def guess_episode_numbers(filename: str) -> tuple[int | None, int | None]:
    """Zkusí najít S01E02 nebo 1x02 v názvu souboru."""
    patterns = (
        r"(?i)(?:^|[._\-\s])s(\d{1,3})[._\-\s]*e(\d{1,4})(?:$|[._\-\s])",
        r"(?i)(?:^|[._\-\s])(\d{1,3})x(\d{1,4})(?:$|[._\-\s])",
    )
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None, None


def ffprobe_available(executable: str = "ffprobe") -> bool:
    return shutil.which(executable) is not None


def probe_media(path: str | Path, executable: str = "ffprobe") -> MediaFile:
    media_path = Path(path).expanduser().resolve()
    if not media_path.is_file():
        raise ProbeError(f"Soubor neexistuje: {media_path}")
    if not ffprobe_available(executable):
        raise ProbeError(
            "Program ffprobe nebyl nalezen. Nainstaluj balík FFmpeg a zkus soubor načíst znovu."
        )

    command = [
        executable,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(media_path),
    ]
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProbeError("Analýza souboru trvala příliš dlouho.") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "Neznámá chyba ffprobe.").strip()
        raise ProbeError(f"Soubor se nepodařilo analyzovat: {detail}") from exc

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ProbeError("ffprobe vrátil neplatná data.") from exc

    return parse_probe_payload(payload, media_path)


def parse_probe_payload(payload: dict[str, Any], media_path: Path) -> MediaFile:
    format_info = payload.get("format") or {}
    streams = payload.get("streams") or []
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})

    audio_tracks: list[AudioTrack] = []
    subtitle_tracks: list[SubtitleTrack] = []

    for stream in streams:
        tags = stream.get("tags") or {}
        disposition = stream.get("disposition") or {}
        stream_type = stream.get("codec_type")
        if stream_type == "audio":
            audio_tracks.append(
                AudioTrack(
                    stream_index=_to_int(stream.get("index")) or 0,
                    language=str(tags.get("language") or "und"),
                    title=str(tags.get("title") or ""),
                    codec=str(stream.get("codec_name") or ""),
                    channels=_to_int(stream.get("channels")),
                    channel_layout=str(stream.get("channel_layout") or ""),
                    sample_rate=_to_int(stream.get("sample_rate")),
                    bitrate=_to_int(stream.get("bit_rate")),
                    is_default=bool(disposition.get("default", 0)),
                )
            )
        elif stream_type == "subtitle":
            subtitle_tracks.append(
                SubtitleTrack(
                    stream_index=_to_int(stream.get("index")) or 0,
                    language=str(tags.get("language") or "und"),
                    title=str(tags.get("title") or ""),
                    codec=str(stream.get("codec_name") or ""),
                    is_default=bool(disposition.get("default", 0)),
                    is_forced=bool(disposition.get("forced", 0)),
                )
            )

    file_size = _to_int(format_info.get("size"))
    if file_size is None:
        try:
            file_size = media_path.stat().st_size
        except OSError:
            file_size = None

    season_number, episode_number = guess_episode_numbers(media_path.name)

    return MediaFile(
        path=str(media_path),
        display_name=media_path.name,
        season_number=season_number,
        episode_number=episode_number,
        duration_seconds=_to_float(format_info.get("duration")),
        size_bytes=file_size,
        container=str(format_info.get("format_name") or "").split(",", 1)[0],
        video_codec=str(video_stream.get("codec_name") or ""),
        width=_to_int(video_stream.get("width")),
        height=_to_int(video_stream.get("height")),
        fps=_parse_fraction(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")),
        video_bitrate=_to_int(video_stream.get("bit_rate")),
        overall_bitrate=_to_int(format_info.get("bit_rate")),
        audio_tracks=audio_tracks,
        subtitle_tracks=subtitle_tracks,
    )


def probe_to_dict(media_file: MediaFile) -> dict[str, Any]:
    """Pomocník pro logování a případný export."""
    return asdict(media_file)
