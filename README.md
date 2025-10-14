# YouTube Playlist Downloader

A cross-platform tool and workflow for downloading entire YouTube playlists as MP3 or MP4 files, using [yt-dlp](https://github.com/yt-dlp/yt-dlp), [ffmpeg](https://ffmpeg.org/), and [aria2c](https://github.com/aria2/aria2). Includes Gitea CI/CD workflow for packaging and releasing Windows and Linux binaries.

Supports audio, video, or both download modes, music and viedos are numbered as they are on your youtube playlist, playlist cleanup, and configurable parallel download options.

---


## Features

- **Download full YouTube playlists** as high-quality MP3 (audio), MP4 (video), or both.
- **Download mode:** Choose `audio`, `video`, or `both` for each playlist.
- **Max video quality:** Select from `720p`, `1080p`, `1440p`, `2160p`, or `best`.
- **Parallel downloads:** Using aria2 for speed.
- **Automatic renumbering:** Tracks are renumbered to match playlist order after download.
- **Cleanup of tracks:** Option to remove files not in playlist anymore, with confirmation.
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
  - Open `yt-playlist-config.json` and adjust paths, playlist URLs, download mode, and quality as needed.

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

Edit `yt-playlist-config.json` to specify playlists, paths, and options:

```json
{
  "playlists": [
    {
      "url": "https://www.youtube.com/playlist?list=playlistidhere",
      "save_path": "./music",
      "archive": "archive.txt"
    }
  ],
  "yt_dlp_path": "./bin/yt-dlp.exe",      // or "yt-dlp" for Linux
  "ffmpeg_path": "./bin/ffmpeg.exe",      // or "ffmpeg" for Linux
  "aria2c_path": "./bin/aria2c.exe",      // or "aria2c" for Linux
  "download_mode": "audio",               // "audio", "video", or "both"
  "max_video_quality": "1080p",           // "720p", "1080p", "1440p", "2160p", "best"
  "max_parallel_downloads": 10,
  "aria2c_connections": 8
}
```

- **playlists:** List of playlist objects. Each must have a `url`, `save_path`, and `archive`.
- **yt_dlp_path, ffmpeg_path, aria2c_path:** Paths to binaries (relative or absolute).
- **download_mode:** Choose `audio`, `video`, or `both`.
- **max_video_quality:** Set max video quality for downloads.
- **max_parallel_downloads:** Number of simultaneous downloads.
- **aria2c_connections:** Connections per download.


### Running

```sh
python yt-playlist-main.py
```

- The script checks for required binaries and updates yt-dlp.
- Downloads new tracks in the playlist according to your chosen mode and quality.
- Tracks are saved and automatically renumbered to match playlist order.
- Deleted/private videos are skipped.
- Archive file prevents re-downloading existing tracks.
- After download, you can optionally clean up files not present in the playlist anymore (confirmation required).

---



## Troubleshooting

- **No binaries found:** Ensure paths in `yt-playlist-config.json` are correct and binaries are present.
- **No tracks downloaded:** Check playlist URL and archive file.
- **Download mode or quality issues:** Make sure `download_mode` and `max_video_quality` are set to valid values.
- **Network overload warning:** If you set very high parallel/connections, the script will warn you.

---


## License

See [LICENSE](LICENSE).

---


## Credits

- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [ffmpeg](https://ffmpeg.org/)
- [aria2c](https://github.com/aria2/aria2)

---