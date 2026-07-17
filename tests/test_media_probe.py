from pathlib import Path

from filmoteca.media_probe import guess_episode_numbers, parse_probe_payload


def test_parse_probe_payload():
    payload = {
        "format": {
            "format_name": "matroska,webm",
            "duration": "120.5",
            "size": "123456789",
            "bit_rate": "8192000",
        },
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "hevc",
                "width": 3840,
                "height": 2160,
                "avg_frame_rate": "24000/1001",
                "bit_rate": "7000000",
            },
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "eac3",
                "channels": 6,
                "channel_layout": "5.1(side)",
                "sample_rate": "48000",
                "bit_rate": "640000",
                "tags": {"language": "cze", "title": "Česky"},
                "disposition": {"default": 1},
            },
            {
                "index": 2,
                "codec_type": "subtitle",
                "codec_name": "subrip",
                "tags": {"language": "eng"},
                "disposition": {"default": 0, "forced": 1},
            },
        ],
    }

    result = parse_probe_payload(payload, Path("/tmp/example.mkv"))
    assert result.container == "matroska"
    assert result.resolution == "3840×2160"
    assert round(result.fps or 0, 3) == 23.976
    assert result.audio_tracks[0].language == "cze"
    assert result.audio_tracks[0].is_default is True
    assert result.subtitle_tracks[0].is_forced is True


def test_guess_episode_numbers():
    assert guess_episode_numbers("Show.S02E07.1080p.mkv") == (2, 7)
    assert guess_episode_numbers("Show 3x11.mp4") == (3, 11)
    assert guess_episode_numbers("Film.2025.mkv") == (None, None)
