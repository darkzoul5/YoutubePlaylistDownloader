import os
import sys
import json
import shutil
import platform
import time
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
if platform.system() == "Windows":
    sys.stdout.reconfigure(encoding="utf-8") # type: ignore

OK = "✔"
FAIL = "✘"
WARN = "⚠"
INFO = "ℹ"
STEP = "➜"
def update_yt_dlp(yt_dlp_path: str):
    try:
        subprocess.run(
            [yt_dlp_path, "-U"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,   # capture error output
            text=True
        )
        print(f"{OK} yt-dlp is up to date.")
    except subprocess.CalledProcessError as e:
        print(f"{WARN} Could not update yt-dlp: Internet unavailable or cannot reach update server")



class ConfigLoader:
    DEFAULT_CONFIG = {
        "playlists": [
            {
                "url": "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_HERE",
                "save_path": "./music",
                "archive": "archive.txt"
            }
        ],
        "yt_dlp_path": "yt-dlp.exe" if platform.system() == "Windows" else "yt-dlp",
        "ffmpeg_path": "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg",
        "aria2c_path": "aria2c.exe" if platform.system() == "Windows" else "aria2c",
        "max_parallel_downloads": 10,
        "aria2c_connections": 8
    }

    def __init__(self, config_path: str = "yt-playlist-config.json"):
        self.config_path = Path(config_path).resolve()
        if not self.config_path.exists():
            self._create_default_config()
            print(f"{INFO} Default config created at '{self.config_path}'. Please edit it and rerun.")
            sys.exit(0)

        with self.config_path.open("r", encoding="utf-8") as f:
            self.data = json.load(f)

        # Validate binaries
        self._check_binary(self.yt_dlp_path, "yt-dlp")
        self._check_binary(self.ffmpeg_path, "ffmpeg")
        self._check_binary(self.aria2c_path, "aria2c")

    def _create_default_config(self):
        with self.config_path.open("w", encoding="utf-8") as f:
            json.dump(self.DEFAULT_CONFIG, f, indent=2)

    def _check_binary(self, path_str, name):
        path = Path(path_str)

        # If relative, resolve relative to the config file location
        if not path.is_absolute():
            path = (self.config_path.parent / path).resolve()

        # Check direct file existence OR system PATH
        if path.is_file() or shutil.which(str(path)):
            return

        print(
            f"{WARN}[ERROR] {name} not found.\n"
            f"  Configured path: '{path_str}'\n"
            f"  Resolved absolute path: '{path}'\n"
            f"Please install or correct the yt-playlist-config.json path."
        )
        sys.exit(1)

    @property
    def playlists(self):
        return self.data.get("playlists", [])

    @property
    def yt_dlp_path(self):
        return self.data["yt_dlp_path"]

    @property
    def ffmpeg_path(self):
        return self.data["ffmpeg_path"]

    @property
    def aria2c_path(self):
        return self.data["aria2c_path"]

    @property
    def max_parallel_downloads(self):
        return self.data.get("max_parallel_downloads", 10)

    @property
    def aria2c_connections(self):
        return self.data.get("aria2c_connections", 8)


class PlaylistDownloader:
    illegal_chars = '<>:"/\\|?*'

    def __init__(self, config: ConfigLoader, playlist: dict, index: int):

        # Determine a friendly identifier for the playlist
        playlist_id = playlist.get("url") or playlist.get("save_path") or f"playlist #{index+1}"

        # Check for missing or empty URL
        self.url = playlist.get("url")
        if not self.url or not self.url.startswith("https://www.youtube.com/playlist?list=") or len(self.url) <= len("https://www.youtube.com/playlist?list="):
            print(f"{FAIL} Playlist #{index+1} has invalid or empty URL: '{self.url}' skipping")
            self.skip = True
        else:
            self.skip = False

        # Continue with normal initialization
        self.save_path = Path(playlist.get("save_path", "./music"))
        self.save_path.mkdir(parents=True, exist_ok=True)

        # Archive path
        self.archive = Path(playlist.get("archive", "archive.txt"))
        if not self.archive.is_absolute():
            self.archive = self.save_path / self.archive
        self.archive.touch(exist_ok=True)

        self.yt_dlp = config.yt_dlp_path
        self.ffmpeg = config.ffmpeg_path
        self.aria2c = config.aria2c_path
        self.max_parallel = config.max_parallel_downloads
        self.aria2c_connections = config.aria2c_connections


    def sanitize_title(self, title, fallback_id):
        safe_title = title.translate(str.maketrans({c: '-' for c in self.illegal_chars})).strip()
        return safe_title if safe_title else fallback_id

    def get_file_path(self, track_index, title):
        return self.save_path / f"{track_index:03d} - {title}.mp3"

    def fetch_videos(self):
        if getattr(self, "skip", False) or not self.url:
            return []  # nothing to fetch
    
        result = subprocess.run(
            [self.yt_dlp, "-J", "--flat-playlist", self.url],
            capture_output=True, text=True, check=True
        )
        data = json.loads(result.stdout)
        entries = data.get("entries", [])

        valid = []
        for v in entries:
            if not v:
                continue
            title = v.get("title", "")
            if title in ("[Deleted video]", "[Private video]"):
                print(f"[SKIP] {v['id']} - {title}")
                continue
            valid.append(v)
        return valid

    def get_archive_ids(self):
        ids = set()
        with self.archive.open("r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    ids.add(parts[1])
        return ids

    def download_video(self, video, track_index):
        title = video.get("title", "[Unknown]")
        safe_title = self.sanitize_title(title, video["id"])
        file_output = self.get_file_path(track_index, safe_title)
        video_url = f"https://www.youtube.com/watch?v={video['id']}"

        try:
            subprocess.run([
                str(self.yt_dlp),
                "-f", "bestaudio",
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "--ffmpeg-location", str(self.ffmpeg),
                "--download-archive", str(self.archive),
                "-o", str(file_output),
                "--external-downloader", str(self.aria2c),
                "--external-downloader-args", f"aria2c:-x {self.aria2c_connections} -s {self.aria2c_connections}",
                video_url
            ], check=True)
            print(f"{OK} Downloaded: {track_index:03d} - {title}")
            return True
        except subprocess.CalledProcessError as e:
            #print(f"{FAIL} Error downloading {title}: {e}") #print full error
            err_msg = e.stderr.strip().splitlines()[-1] if e.stderr else "Video Unlisted or Unavailable"
            print(f"{FAIL} Download failed: {title} — {err_msg}")
            return False

    def renumber_all_tracks(self, playlist_entries):
        print(f"\n{STEP} Renumbering files according to playlist order")
        temp_suffix = ".renametemp"

        final_map = {}
        for idx, video in enumerate(playlist_entries, start=1):
            title = video.get("title", "[Unknown]")
            safe_title = self.sanitize_title(title, video["id"])
            correct_fname = f"{idx:03d} - {safe_title}.mp3"
            final_map[safe_title] = correct_fname

        for safe_title, correct_fname in final_map.items():
            matches = list(self.save_path.glob(f"* - {safe_title}.mp3"))
            if matches:
                current_path = matches[0]
                if current_path.name != correct_fname:
                    temp_path = current_path.with_suffix(current_path.suffix + temp_suffix)
                    #print(f"Temporarily renaming '{current_path.name}' → '{temp_path.name}'")
                    current_path.rename(temp_path)

        for safe_title, correct_fname in final_map.items():
            temp_match = list(self.save_path.glob(f"* - {safe_title}.mp3{temp_suffix}"))
            if temp_match:
                temp_path = temp_match[0]
                final_path = self.save_path / correct_fname
                print(f"Renaming '{temp_path.name}' → '{final_path.name}'")
                temp_path.rename(final_path)

        print(f"{OK} Renumbering complete.")

    def update(self):
        playlist_id = self.url or self.save_path or "unknown playlist"
        if getattr(self, "skip", False):
            print(f"{WARN} Skipping playlist '{playlist_id}': URL missing in the config.")
            return

        print(f"{STEP} Updating playlist: {playlist_id}")
        playlist_entries = self.fetch_videos()
        archive_ids = self.get_archive_ids()
        new_videos = [v for v in playlist_entries if v["id"] not in archive_ids]

        if not new_videos:
            print(f"{OK} No new tracks found.")
        else:
            print(f"{OK} Found {len(new_videos)} new track(s) to download.")

            idx_map = {v["id"]: i+1 for i, v in enumerate(playlist_entries)}

            with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
                futures = [executor.submit(self.download_video, v, idx_map[v["id"]]) for v in new_videos]
                for f in as_completed(futures):
                    try:
                        f.result()
                    except subprocess.CalledProcessError as e:
                        print(f"{FAIL} Download failed: {e}")

        self.renumber_all_tracks(playlist_entries)
        self.cleanup_removed_tracks(playlist_entries)

    def cleanup_removed_tracks(self, playlist_entries):
        print(f"{STEP} Checking for files not in the playlist")
        valid_titles = set()
        for video in playlist_entries:
            title = video.get("title", "[Unknown]")
            safe_title = self.sanitize_title(title, video["id"])
            valid_titles.add(safe_title)

        to_delete = []
        for file in self.save_path.glob("*.mp3"):
            parts = file.name.split(" - ", 1)
            if len(parts) == 2:
                safe_title_in_file = parts[1][:-4]
                if safe_title_in_file not in valid_titles:
                    to_delete.append(file)

        if not to_delete:
            print(f"{OK} No extra files to delete.")
            return

        print(f"{WARN} The following files are not in the playlist and will be deleted:")
        for f in to_delete:
            print(f"  {f.name}")

        try:
            confirm = input(f"{WARN} Delete these files? [y/N]: ").strip().lower()
        except EOFError:
            confirm = "n"

        if confirm == "y":
            for f in to_delete:
                try:
                    f.unlink()
                    print(f"{OK} Deleted: {f.name}")
                except Exception as ex:
                    print(f"{FAIL} Failed to delete {f.name}: {ex}")
            print(f"{OK} Cleanup complete.")
        else:
            print(f"{OK} Cleanup aborted. No files were deleted.")


class PlaylistManager:
    def __init__(self, config: ConfigLoader):
        self.config = config
        self.playlists = [
            PlaylistDownloader(config, pl, idx)
            for idx, pl in enumerate(config.playlists)
        ]

    def run(self):
        total_connections = self.config.max_parallel_downloads * self.config.aria2c_connections
        if total_connections > 100:
            print("\033[91m"
                  f"{WARN}[WARNING] Total connections ({self.config.max_parallel_downloads} × "
                  f"{self.config.aria2c_connections} = {total_connections}) may overload your network! Pausing 5 seconds..."
                  "\033[0m")
            time.sleep(5)

        for playlist in self.playlists:
            playlist.update()


if __name__ == "__main__":
    cfg = ConfigLoader("yt-playlist-config.json")
    update_yt_dlp(cfg.yt_dlp_path) #update yt-dpl executable
    manager = PlaylistManager(cfg)
    manager.run()
