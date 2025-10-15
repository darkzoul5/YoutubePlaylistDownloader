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

def is_docker():
    return os.path.exists("/.dockerenv") or os.getenv("RUNNING_IN_DOCKER") == "true"

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
                "url": "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID_HERE",
                "download_mode": "audio",  # options: audio, video, both
                "max_video_quality": "1080p", # options: 720p, 1080p, 1440p, 2160p, best
                "save_path": "./downloads",
                "archive": "archive.txt"
            }
        ],
        "yt_dlp_path": "yt-dlp" if is_docker() else ("./bin/yt-dlp.exe" if platform.system() == "Windows" else "./bin/yt-dlp"),
        "ffmpeg_path": "ffmpeg" if is_docker() else ("./bin/ffmpeg.exe" if platform.system() == "Windows" else "./bin/ffmpeg"),
        "aria2c_path": "aria2c" if is_docker() else ("./bin/aria2c.exe" if platform.system() == "Windows" else "./bin/aria2c"),
        "max_parallel_downloads": 10,
        "aria2c_connections": 8
    }

    def __init__(self, config_path=None):
        config_dir = Path("./config")
        config_dir.mkdir(parents=True, exist_ok=True)
        if config_path is None:
            config_path = config_dir / "yt-playlist-config.json"
        else:
            config_path = Path(config_path)
            if not config_path.is_absolute():
                config_path = config_dir / config_path
        self.config_path = Path(config_path).resolve()
        if not self.config_path.exists():
            self._create_default_config()
            print(f"{INFO} Default config created at '{self.config_path}'. Please edit it and rerun.")
            sys.exit(0)

        with self.config_path.open("r", encoding="utf-8") as f:
            self.data = json.load(f)

        # Validate binaries
        self._check_binary(self.yt_dlp_path, "yt-dlp")
        self._check_binary(self.aria2c_path, "aria2c")
        # Only require ffmpeg if download_mode is audio
        if self.download_mode == "audio":
            self._check_binary(self.ffmpeg_path, "ffmpeg")
            if not shutil.which(self.ffmpeg_path) and not Path(self.ffmpeg_path).is_file():
                print(f"{FAIL} ffmpeg is required for audio mode but was not found.\nPlease install ffmpeg or set the correct path in yt-playlist-config.json.")
                sys.exit(1)

    def _create_default_config(self):
        with self.config_path.open("w", encoding="utf-8") as f:
            json.dump(self.DEFAULT_CONFIG, f, indent=2)

    def _check_binary(self, path_str, name):
        # If path_str looks like a system binary (no slashes), check PATH only
        if os.sep not in path_str and '/' not in path_str:
            if shutil.which(path_str):
                return
            print(
                f"{WARN}[ERROR] {name} not found in system PATH.\n"
                f"  Configured path: '{path_str}'\n"
                f"Please install or correct the path in yt-playlist-config.json ."
            )
            sys.exit(1)
        else:
            path = Path(path_str)
            if not path.is_absolute():
                path = (self.config_path.parent / path).resolve()
            if path.is_file() or shutil.which(str(path)):
                return
            print(
                f"{WARN}[ERROR] {name} not found.\n"
                f"  Configured path: '{path_str}'\n"
                f"  Resolved absolute path: '{path}'\n"
                f"Please correct the yt-playlist-config.json path."
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
    def download_mode(self):
        return self.data.get("download_mode", "audio")
    
    @property
    def max_video_quality(self):
        return self.data.get("max_video_quality", "1080p")

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
        self.download_mode = playlist.get("download_mode", config.download_mode)
        self.max_video_quality = playlist.get("max_video_quality", config.max_video_quality)

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
        video_url = f"https://www.youtube.com/watch?v={video['id']}"

        def build_video_format(max_quality):
            mapping = {
                "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "1440p": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
                "2160p": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
                "best": "bestvideo+bestaudio/best"
            }
            return mapping.get(max_quality.lower(), mapping["1080p"])

        cmds = []

        if self.download_mode == "audio":
            output_path = self.save_path / "audio" / f"{track_index:03d} - {safe_title}.mp3"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            args = [
                str(self.yt_dlp),
                "-f", "bestaudio",
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "--ffmpeg-location", str(self.ffmpeg),
                "--download-archive", str(self.archive),
                "-o", str(output_path),
                "--external-downloader", str(self.aria2c),
                "--external-downloader-args",
                f"aria2c:-x {self.aria2c_connections} -s {self.aria2c_connections}",
                video_url
            ]
            cmds.append((args, f"{track_index:03d} - {title} (audio)"))

        elif self.download_mode == "video":
            output_path = self.save_path / "video" / f"{track_index:03d} - {safe_title}.mp4"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fmt = build_video_format(self.max_video_quality)
            args = [
                str(self.yt_dlp),
                "-f", fmt,
                "--merge-output-format", "mp4",
                "--ffmpeg-location", str(self.ffmpeg),
                "--download-archive", str(self.archive),
                "-o", str(output_path),
                "--external-downloader", str(self.aria2c),
                "--external-downloader-args",
                f"aria2c:-x {self.aria2c_connections} -s {self.aria2c_connections}",
                video_url
            ]
            cmds.append((args, f"{track_index:03d} - {title} (video)"))

        elif self.download_mode == "both":
            # audio folder
            audio_folder = self.save_path / "audio"
            audio_folder.mkdir(parents=True, exist_ok=True)
            audio_output = audio_folder / f"{track_index:03d} - {safe_title}.mp3"
            audio_args = [
                str(self.yt_dlp),
                "-f", "bestaudio",
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "--ffmpeg-location", str(self.ffmpeg),
                "--download-archive", str(self.archive),
                "-o", str(audio_output),
                "--external-downloader", str(self.aria2c),
                "--external-downloader-args",
                f"aria2c:-x {self.aria2c_connections} -s {self.aria2c_connections}",
                video_url
            ]
            cmds.append((audio_args, f"{track_index:03d} - {title} (audio)"))

            # video folder
            video_folder = self.save_path / "video"
            video_folder.mkdir(parents=True, exist_ok=True)
            video_output = video_folder / f"{track_index:03d} - {safe_title}.mp4"
            fmt = build_video_format(self.max_video_quality)
            video_args = [
                str(self.yt_dlp),
                "-f", fmt,
                "--merge-output-format", "mp4",
                "--ffmpeg-location", str(self.ffmpeg),
                "--download-archive", str(self.archive),
                "-o", str(video_output),
                "--external-downloader", str(self.aria2c),
                "--external-downloader-args",
                f"aria2c:-x {self.aria2c_connections} -s {self.aria2c_connections}",
                video_url
            ]
            cmds.append((video_args, f"{track_index:03d} - {title} (video)"))

        else:
            print(f"{FAIL} Invalid download_mode '{self.download_mode}', skipping")
            return False

        # --- execute one or both downloads ---
        success = True
        for args, label in cmds:
            try:
                subprocess.run(args, check=True)
                print(f"{OK} Downloaded: {label}")
            except subprocess.CalledProcessError as e:
                err_msg = e.stderr.strip().splitlines()[-1] if e.stderr else "Unknown error"
                print(f"{FAIL} Download failed: {label} — {err_msg}")
                success = False

        return success


    def renumber_all_tracks(self, playlist_entries):
        print(f"\n{STEP} Renumbering files according to playlist order")
        temp_suffix = ".renametemp"

        # --- Build mapping of safe_title → correct filename ---
        final_map_audio = {}
        final_map_video = {}

        for idx, video in enumerate(playlist_entries, start=1):
            title = video.get("title", "[Unknown]")
            safe_title = self.sanitize_title(title, video["id"])

            if self.download_mode in ("audio", "both"):
                final_map_audio[safe_title] = f"{idx:03d} - {safe_title}.mp3"
            if self.download_mode in ("video", "both"):
                final_map_video[safe_title] = f"{idx:03d} - {safe_title}.mp4"

        # --- Helper function to rename files in folder ---
        def rename_files(folder, mapping, ext):
            folder.mkdir(parents=True, exist_ok=True)
            for safe_title, correct_fname in mapping.items():
                matches = list(folder.glob(f"*{ext}"))
                # Find matching file
                for m in matches:
                    if safe_title in m.name:
                        if m.name != correct_fname:
                            temp_path = m.with_suffix(m.suffix + temp_suffix)
                            m.rename(temp_path)

            for safe_title, correct_fname in mapping.items():
                temp_match = list(folder.glob(f"*{ext}{temp_suffix}"))
                for temp_path in temp_match:
                    final_path = folder / correct_fname
                    print(f"Renaming '{temp_path.name}' → '{final_path.name}'")
                    temp_path.rename(final_path)

        if self.download_mode in ("audio", "both"):
            rename_files(self.save_path / "audio", final_map_audio, ".mp3")
        if self.download_mode in ("video", "both"):
            rename_files(self.save_path / "video", final_map_video, ".mp4")

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
            print(f"{OK} No new items found.")
        else:
            print(f"{OK} Found {len(new_videos)} new item(s) to download.")

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

        def clean_folder(folder, ext):
            to_delete = []
            folder.mkdir(parents=True, exist_ok=True)
            for file in folder.glob(f"*{ext}"):
                parts = file.name.split(" - ", 1)
                if len(parts) == 2:
                    safe_title_in_file = parts[1][:-len(ext)]
                    if safe_title_in_file not in valid_titles:
                        to_delete.append(file)

            if not to_delete:
                return

            print(f"{WARN} The following files in '{folder}' are not in the playlist and will be deleted:")
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
                print(f"{OK} Cleanup complete in '{folder}'.")
            else:
                print(f"{OK} Cleanup aborted in '{folder}'. No files were deleted.")

        if self.download_mode in ("audio", "both"):
            clean_folder(self.save_path / "audio", ".mp3")
        if self.download_mode in ("video", "both"):
            clean_folder(self.save_path / "video", ".mp4")



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
