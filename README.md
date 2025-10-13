# YouTube Playlist Downloader

A cross-platform tool and workflow for downloading entire YouTube playlists as MP3 files, using [yt-dlp](https://github.com/yt-dlp/yt-dlp), [ffmpeg](https://ffmpeg.org/), and [aria2c](https://github.com/aria2/aria2). Includes Gitea CI/CD workflow for packaging and releasing Windows and Linux binaries.

---

## Features

- **Download full YouTube playlists** as high-quality MP3 files.
- **Parallel downloads** using aria2c for speed.
- **Automatic numbering:** numbers tracks same as the origin playlist.
- **Cleanup of tracks:** optioon to remove tracks not in playlist anymore.
- **Configurable output paths** and archive tracking.
- **Cross-platform:** Windows and Linux support.
- **Gitea CI/CD workflow** for automated packaging and release.

---

## Requirements

- Python 3.8+

---

## Installation

### Quick Start

1. **Download the latest release:**
   - Go to the [Releases](https://git.darkzoul.org/dark_zoul/YouTube-Playlist-Downloader/releases) page.
   - Download the appropriate archive for your platform (Windows or Linux).

2. **Unzip the archive:**
   - Extract the contents to a folder of your choice.

3. **Edit configuration:**
   - Open `yt-playlist-config.json` and adjust paths and playlist URLs as needed.

4. **Run the downloader:**
   - On Windows:
     ```sh
     python yt-playlist-main.py
     ```
   - On Linux:
     ```sh
     python3 yt-playlist-main.py
     ```

---

## Usage

### Configuration

Edit `yt-playlist-config.json` to specify playlists and paths:

```json
{
  "playlists": [
    {
      "url": "https://www.youtube.com/playlist?list=playlistidhere",
      "save_path": "./music",
      "archive": "archive.txt"
    }
  ],
  "yt_dlp_path": "./bin/yt-dlp.exe",
  "ffmpeg_path": "./bin/ffmpeg.exe",
  "aria2c_path": "./bin/aria2c.exe",
  "max_parallel_downloads": 10,
  "aria2c_connections": 8
}
```

- **playlists:** List of playlist objects. Each must have a `url`, `save_path`, and `archive`.
- **yt_dlp_path, ffmpeg_path, aria2c_path:** Paths to binaries (relative or absolute).
- **max_parallel_downloads:** Number of simultaneous downloads.
- **aria2c_connections:** Connections per download.

### Running

```sh
python yt-playlist-main.py
```

- The script will check for binaries, update yt-dlp, and download all new tracks in the playlist.
- Tracks are saved and numbered in the specified folder.
- Deleted/private videos are skipped.
- Archive file prevents re-downloading existing tracks.

---


## Troubleshooting

- **No binaries found:** Ensure paths in `yt-playlist-config.json` are correct.
- **No tracks downloaded:** Check playlist URL and archive file.

---

## License

See [LICENSE](LICENSE).

---

## Credits

- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [ffmpeg](https://ffmpeg.org/)
- [aria2c](https://github.com/aria2/aria2)

---