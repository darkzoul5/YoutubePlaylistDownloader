import logging
from ytplaylist.manager import PlaylistManager
from tests.temp_config import TempConfig


class TestConfig(TempConfig):
    playlists = [{"url": None, "save_path": "./tmp_test", "archive": "archive.txt"}]

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")
    print('--- Running with prune=False ---')
    cfg=TestConfig()
    m=PlaylistManager(cfg, debug=False)
    m.run()
    print('Run complete prune=False')

    print('\n--- Running with prune=True, non_interactive=True ---')
    cfg2=TestConfig()
    cfg2.prune=True
    cfg2.non_interactive=True
    m2=PlaylistManager(cfg2, debug=False)
    m2.run()
    print('Run complete prune=True non_interactive=True')
