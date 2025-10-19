import time

from .downloader import PlaylistDownloader


class PlaylistManager:
    def __init__(self, config):
        self.config = config
        self.playlists = [PlaylistDownloader(config, pl, idx) for idx, pl in enumerate(config.playlists)]

    def run(self):
        total_connections = self.config.max_parallel_downloads * self.config.aria2c_connections
        if total_connections > 100:
            print(
                "\033[91m"
                f"⚠[WARNING] Total connections ({self.config.max_parallel_downloads} × {self.config.aria2c_connections} = {total_connections}) may overload your network! Pausing 5 seconds..."
                "\033[0m"
            )
            time.sleep(5)

        for playlist in self.playlists:
            playlist.update()
