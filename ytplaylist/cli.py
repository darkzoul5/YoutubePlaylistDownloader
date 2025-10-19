import subprocess
from .config import ConfigLoader, is_docker
from .manager import PlaylistManager


def update_yt_dlp(yt_dlp_path: str):
    try:
        subprocess.run([
            yt_dlp_path,
            "-U",
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        print("✔ yt-dlp is up to date.")
    except subprocess.CalledProcessError:
        print("⚠ Could not update yt-dlp: Internet unavailable or cannot reach update server")


def main(config_path: str = "yt-playlist-config.json"):
    cfg = ConfigLoader(config_path)
    if not is_docker():
        update_yt_dlp(cfg.yt_dlp_path)
    manager = PlaylistManager(cfg)
    manager.run()
