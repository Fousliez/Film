from filmoteca.database import MediaRepository
from filmoteca.models import AudioTrack, MediaFile, MediaItem, SubtitleTrack


def test_item_and_file_roundtrip(tmp_path):
    repository = MediaRepository(tmp_path / "test.sqlite3")
    item_id = repository.add_item(
        MediaItem(
            title="Testovací film",
            media_type="movie",
            year=2025,
            rating=4,
            favorite=True,
            genres="sci-fi",
        )
    )

    item = repository.get_item(item_id)
    assert item is not None
    assert item.title == "Testovací film"
    assert item.favorite is True

    file_id = repository.add_file(
        item_id,
        MediaFile(
            path="/tmp/test.mkv",
            display_name="test.mkv",
            width=1920,
            height=1080,
            size_bytes=1_000_000,
            audio_tracks=[AudioTrack(language="cze", codec="aac", channels=2)],
            subtitle_tracks=[SubtitleTrack(language="cze", codec="subrip")],
        ),
    )

    files = repository.list_files(item_id)
    assert len(files) == 1
    assert files[0].resolution == "1920×1080"
    assert repository.get_audio_tracks(file_id)[0].language == "cze"
    assert repository.get_subtitle_tracks(file_id)[0].codec == "subrip"

    repository.delete_item(item_id)
    assert repository.get_item(item_id) is None
    assert repository.get_file(file_id) is None


def test_filters(tmp_path):
    repository = MediaRepository(tmp_path / "test.sqlite3")
    repository.add_item(MediaItem(title="Film A", media_type="movie", favorite=True))
    repository.add_item(MediaItem(title="Seriál B", media_type="series"))

    assert [item.title for item in repository.list_items(media_type="movie")] == [
        "Film A"
    ]
    assert [item.title for item in repository.list_items(favorite_only=True)] == [
        "Film A"
    ]
    assert [item.title for item in repository.list_items(search="seriál")] == [
        "Seriál B"
    ]
