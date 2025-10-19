import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed

OK = "✔"
FAIL = "✘"
WARN = "⚠"
STEP = "➜"


class PlaylistDownloader:
    illegal_chars = '<>:"/\\|?*'

    def __init__(self, config, playlist: dict, index: int):
        self.url = playlist.get("url")
        self.skip = False
        if not self.url:
            print(
                f"{FAIL} Playlist #{index + 1} has invalid or empty URL: '{self.url}' skipping"
            )
            self.skip = True
        else:
            parsed = urlparse(self.url)
            qs = parse_qs(parsed.query)
            if "list" in qs and qs.get("list"):
                self.skip = False
            else:
                if (
                    "v" in qs
                    or parsed.netloc.endswith("youtu.be")
                    or parsed.path.startswith("/watch")
                ):
                    print(
                        f"{WARN} URL for playlist #{index + 1} looks like a video URL, not a playlist: '{self.url}' — skipping"
                    )
                    self.skip = True
                else:
                    print(
                        f"{WARN} URL for playlist #{index + 1} does not contain a playlist id: '{self.url}'. Attempting to fetch, but it may fail."
                    )
                    self.skip = False

        self.download_mode = playlist.get("download_mode", config.download_mode)
        self.max_video_quality = playlist.get("max_video_quality", config.max_video_quality)

        self.save_path = Path(playlist.get("save_path", "./music"))
        self.save_path.mkdir(parents=True, exist_ok=True)

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
        safe_title = title.translate(str.maketrans({c: "-" for c in self.illegal_chars})).strip()
        return safe_title if safe_title else fallback_id

    def get_file_path(self, track_index, title):
        return self.save_path / f"{track_index:03d} - {title}.mp3"

    def fetch_videos(self):
        if getattr(self, "skip", False) or not self.url:
            return []

        try:
            result = subprocess.run(
                [self.yt_dlp, "-J", "--flat-playlist", self.url],
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(result.stdout)
            entries = data.get("entries", [])
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").lower()
            if any(k in stderr for k in ("private", "sign in", "login required", "403", "authorization failed")):
                print(f"{WARN} Playlist appears to be private or requires authentication: '{self.url}'. Skipping.")
                self.skip = True
                return []
            print(f"{FAIL} Failed to fetch playlist '{self.url}': {e.stderr.strip() if e.stderr else str(e)}")
            self.skip = True
            return []
        except json.JSONDecodeError:
            print(f"{FAIL} Failed to parse yt-dlp output for URL: '{self.url}'. Skipping.")
            self.skip = True
            return []

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
                "1440p": "bestvideo[height<=1440]+bestaudio+bestaudio/best[height<=1440]",
                "2160p": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
                "best": "bestvideo+bestaudio/best",
            }
            return mapping.get(max_quality.lower(), mapping["1080p"])

        cmds = []

        if self.download_mode == "audio":
            output_path = (self.save_path / "audio" / f"{track_index:03d} - {safe_title}.mp3")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            args = [
                str(self.yt_dlp),
                "-f",
                "bestaudio",
                "--extract-audio",
                "--audio-format",
                "mp3",
                "--audio-quality",
                "0",
            ]
            if not shutil.which(str(self.ffmpeg)):
                args += ["--ffmpeg-location", str(self.ffmpeg)]
            args += [
                "--download-archive",
                str(self.archive),
                "-o",
                str(output_path),
                "--external-downloader",
                str(self.aria2c),
                "--external-downloader-args",
                f"aria2c:-x {self.aria2c_connections} -s {self.aria2c_connections}",
                video_url,
            ]
            cmds.append((args, f"{track_index:03d} - {title} (audio)"))

        elif self.download_mode == "video":
            output_path = (self.save_path / "video" / f"{track_index:03d} - {safe_title}.mp4")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fmt = build_video_format(self.max_video_quality)
            args = [
                str(self.yt_dlp),
                "-f",
                fmt,
                "--merge-output-format",
                "mp4",
            ]
            if not shutil.which(str(self.ffmpeg)):
                args += ["--ffmpeg-location", str(self.ffmpeg)]
            args += [
                "--download-archive",
                str(self.archive),
                "-o",
                str(output_path),
                "--external-downloader",
                str(self.aria2c),
                "--external-downloader-args",
                f"aria2c:-x {self.aria2c_connections} -s {self.aria2c_connections}",
                video_url,
            ]
            cmds.append((args, f"{track_index:03d} - {title} (video)"))

        elif self.download_mode == "both":
            video_folder = self.save_path / "video"
            video_folder.mkdir(parents=True, exist_ok=True)
            video_output = video_folder / f"{track_index:03d} - {safe_title}.mp4"
            fmt = build_video_format(self.max_video_quality)
            video_args = [
                str(self.yt_dlp),
                "-f",
                fmt,
                "--merge-output-format",
                "mp4",
                "--download-archive",
                str(self.archive),
                "-o",
                str(video_output),
                "--external-downloader",
                str(self.aria2c),
                "--external-downloader-args",
                f"aria2c:-x {self.aria2c_connections} -s {self.aria2c_connections}",
                video_url,
            ]
            try:
                subprocess.run(video_args, check=True)
            except subprocess.CalledProcessError as e:
                err = (e.stderr or "").strip()
                print(f"{FAIL} Video download failed: {title} — {err}")
                return False

            audio_folder = self.save_path / "audio"
            audio_folder.mkdir(parents=True, exist_ok=True)
            audio_output = audio_folder / f"{track_index:03d} - {safe_title}.mp3"
            ffmpeg_exe = str(self.ffmpeg)
            if not (shutil.which(ffmpeg_exe) or Path(ffmpeg_exe).is_file()):
                ffmpeg_exe = shutil.which("ffmpeg") or ffmpeg_exe

            if ffmpeg_exe:
                ffmpeg_cmd = [
                    ffmpeg_exe,
                    "-y",
                    "-i",
                    str(video_output),
                    "-vn",
                    "-codec:a",
                    "libmp3lame",
                    "-q:a",
                    "0",
                    str(audio_output),
                ]
                try:
                    subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
                except subprocess.CalledProcessError as e:
                    print(f"{WARN} ffmpeg failed to extract audio for {title}: {(e.stderr or '').strip()}")
            else:
                print(f"{WARN} ffmpeg not found; audio not extracted for {title}.")

            print(f"{OK} Downloaded video and extracted audio for: {track_index:03d} - {title}")
            return True

        else:
            print(f"{FAIL} Invalid download_mode '{self.download_mode}', skipping")
            return False

        success = True
        for args, label in cmds:
            try:
                subprocess.run(args, check=True)
                print(f"{OK} Downloaded: {label}")
            except subprocess.CalledProcessError as e:
                err_msg = (e.stderr.strip().splitlines()[-1] if e.stderr else "Unknown error")
                print(f"{FAIL} Download failed: {label} — {err_msg}")
                success = False

        return success

    def renumber_all_tracks(self, playlist_entries):
        print(f"\n{STEP} Renumbering files according to playlist order")
        temp_suffix = ".renametemp"

        final_map_audio = {}
        final_map_video = {}

        for idx, video in enumerate(playlist_entries, start=1):
            title = video.get("title", "[Unknown]")
            safe_title = self.sanitize_title(title, video["id"])

            if self.download_mode in ("audio", "both"):
                final_map_audio[safe_title] = f"{idx:03d} - {safe_title}.mp3"
            if self.download_mode in ("video", "both"):
                final_map_video[safe_title] = f"{idx:03d} - {safe_title}.mp4"

        def rename_files(folder, mapping, ext):
            folder.mkdir(parents=True, exist_ok=True)
            for safe_title, correct_fname in mapping.items():
                matches = list(folder.glob(f"*{ext}"))
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
            idx_map = {v["id"]: i + 1 for i, v in enumerate(playlist_entries)}
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
                    safe_title_in_file = parts[1][: -len(ext)]
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
