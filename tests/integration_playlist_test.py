"""
Integration test (opt-in):
- Set environment variable INTEGRATION_TEST=1
- Set TEST_PLAYLIST_URL to a small public playlist (1-3 items) for testing
This test will only fetch the playlist JSON via yt-dlp (no downloads).
"""
import os
import sys
import logging

if not os.getenv("INTEGRATION_TEST"):
    print("Skipping integration test (set INTEGRATION_TEST=1 to enable)")
    sys.exit(0)

from ytplaylist.downloader import PlaylistDownloader

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

playlist_url = os.getenv("TEST_PLAYLIST_URL")
if not playlist_url:
    print("Please set TEST_PLAYLIST_URL to a public YouTube playlist URL for integration testing")
    sys.exit(1)

# build a small temporary config-like object
class TempConfig:
    yt_dlp_path = os.getenv("YTDLP_PATH", "yt-dlp")
    ffmpeg_path = os.getenv("FFMPEG_PATH", "ffmpeg")
    aria2c_path = os.getenv("ARIA2C_PATH", "aria2c")
    max_parallel_downloads = 2
    aria2c_connections = 2
    download_mode = "audio"
    max_video_quality = "1080p"

cfg = TempConfig()
pl = {"url": playlist_url, "save_path": "./tmp_integration", "archive": "archive.txt"}

d = PlaylistDownloader(cfg, pl, 0)
entries = d.fetch_videos()
print(f"Fetched {len(entries)} entries")
if len(entries) == 0:
    print("No entries fetched; either playlist is empty or fetch failed")
    sys.exit(2)

# verify sanitize and renumber mapping logic
sample = entries[:2]
for i, e in enumerate(sample, start=1):
    title = e.get('title', '')
    safe = d.sanitize_title(title, e.get('id'))
    print(f"{i}: {title} -> {safe}")

print('Integration test completed successfully')
