import shutil
from pathlib import Path

from ytplaylist.downloader import PlaylistDownloader
from tests.dummy_config import DummyConfig


def touch(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x")


def test_renumber_all_tracks_and_cleanup(tmp_path):
    cfg = DummyConfig()
    playlist = {"url": "FAKE", "save_path": str(tmp_path)}
    dl = PlaylistDownloader(cfg, playlist, 0)
    # set download mode to both so both folders are considered
    dl.download_mode = "both"

    # Create sample playlist entries with titles that will produce safe_title
    entries = [
        {"id": "ID1", "title": "First Song"},
        {"id": "ID2", "title": "Second Song"},
    ]

    # create files with wrong prefixes
    a1 = tmp_path / "audio" / "oldname First Song.mp3"
    a2 = tmp_path / "audio" / "zzz Second Song.mp3"
    v1 = tmp_path / "video" / "oops First Song.mp4"
    v2 = tmp_path / "video" / "another Second Song.mp4"

    touch(a1)
    touch(a2)
    touch(v1)
    touch(v2)

    # Run renumbering
    dl.renumber_all_tracks(entries)

    # Check that files have been renamed to expected NNN - title.ext
    audio_files = list((tmp_path / "audio").glob("*.mp3"))
    video_files = list((tmp_path / "video").glob("*.mp4"))

    assert any(f.name.startswith("001 - First Song") for f in audio_files)
    assert any(f.name.startswith("002 - Second Song") for f in audio_files)
    assert any(f.name.startswith("001 - First Song") for f in video_files)
    assert any(f.name.startswith("002 - Second Song") for f in video_files)

    # Now test cleanup_removed_tracks: create a stray file not in entries
    stray = tmp_path / "audio" / "999 - NotInPlaylist.mp3"
    touch(stray)
    # ensure prune=False -> no deletion
    dl.prune = False
    dl.cleanup_removed_tracks(entries)
    assert stray.exists()

    # Now enable prune and non_interactive so deletion occurs without input
    dl.prune = True
    dl.non_interactive = True
    dl.cleanup_removed_tracks(entries)
    assert not stray.exists()
