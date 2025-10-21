import logging
from ytplaylist.manager import PlaylistManager

class test:
    playlists=[{"url": None, "save_path":"./tmp_test", "archive":"archive.txt"}]
    yt_dlp_path="yt-dlp"
    ffmpeg_path="ffmpeg"
    aria2c_path="aria2c"
    max_parallel_downloads=2
    aria2c_connections=2
    debug=False
    non_interactive=False
    prune=False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")
    print('--- Running with prune=False ---')
    cfg=test()
    m=PlaylistManager(cfg, debug=False)
    m.run()
    print('Run complete prune=False')

    print('\n--- Running with prune=True, non_interactive=True ---')
    cfg2=test()
    cfg2.prune=True
    cfg2.non_interactive=True
    m2=PlaylistManager(cfg2, debug=False)
    m2.run()
    print('Run complete prune=True non_interactive=True')
