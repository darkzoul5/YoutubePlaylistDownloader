from __future__ import annotations

import os

import pytest

from app.core.database.db import Database
from app.core.sync.executor import ActionExecutor
from app.core.events.event_bus import EventBus
from app.core.sync.service import SyncService


PLAYLIST_URL = os.getenv("TEST_PLAYLIST_URL")


def _require_integration():
    if not os.getenv("INTEGRATION_TEST"):
        pytest.skip("Set INTEGRATION_TEST=1 to enable real download tests")
    if not PLAYLIST_URL:
        pytest.skip("Set TEST_PLAYLIST_URL to enable real download tests")


def _skip_if_bot_check(errors: list[str]) -> None:
    msg = "\n".join(errors).lower()
    if "sign in to confirm you’re not a bot" in msg or "sign in to confirm you're not a bot" in msg:
        pytest.skip("YouTube bot-check blocked download; provide cookies to yt-dlp to run this test reliably")


@pytest.mark.integration
def test_integration_download_video(tmp_path):
    _require_integration()

    db_path = tmp_path / "app.db"
    save_path = tmp_path / "downloads"
    save_path.mkdir(parents=True, exist_ok=True)

    cfg = {
        "url": PLAYLIST_URL,
        "download_mode": "video",
        "save_path": str(save_path),
        "ffmpeg_path": os.getenv("FFMPEG_PATH"),
        "max_download_quality": "1080p",
    }

    db = Database(db_path.resolve())
    service = SyncService(db)
    actions = service.sync_from_config(cfg)

    download_actions = [a for a in actions if a.type.name == "DOWNLOAD"]
    if not download_actions:
        pytest.skip("No download actions produced (playlist empty or already downloaded?)")

    first_vid = download_actions[0].item.video_id if download_actions[0].item else None
    assert first_vid
    subset = [a for a in download_actions if a.item and a.item.video_id == first_vid]
    subset = [a for a in subset if (a.to_name or "").endswith(".mp4")]
    assert subset

    errors: list[str] = []
    bus = EventBus()

    async def on_failed(payload):
        errors.append(str(payload.get("error", "")))

    bus.subscribe("DownloadFailed", on_failed)

    executor = ActionExecutor(db, concurrency=1, event_bus=bus)
    import asyncio

    asyncio.run(executor.execute(subset, cfg))

    video_dir = save_path / "video"
    assert video_dir.exists()
    if not any(p.suffix.lower() == ".mp4" for p in video_dir.glob("*.mp4")):
        _skip_if_bot_check(errors)
        assert False
