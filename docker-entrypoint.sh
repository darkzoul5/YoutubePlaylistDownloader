#!/bin/sh
# Entry point for the ytplaylist container.
# Converts environment variables into CLI flags and execs the Python CLI.

set -e

# Map environment variables to CLI flags
ARGS=""

if [ "${YTPL_DEBUG:-0}" != "0" ]; then
  ARGS="$ARGS --debug"
fi

if [ "${YTPL_PRUNE:-0}" != "0" ]; then
  ARGS="$ARGS --prune"
fi

if [ "${YTPL_YES:-0}" != "0" ]; then
  ARGS="$ARGS --yes"
fi

if [ -n "${YTPL_CONFIG}" ]; then
  ARGS="$ARGS --config ${YTPL_CONFIG}"
fi

# If environment-based configuration is provided, materialize it into /app/config/yt-playlist-config.json
# Supported methods (priority order):
# 1) YTPL_CONFIG_JSON -> full JSON payload for the entire config
# 2) YTPL_PLAYLISTS_JSON -> JSON array assigned to 'playlists' key in the base config
# 3) PLAYLIST_{N}_{FIELD} env vars, e.g. PLAYLIST_0_URL, PLAYLIST_0_DOWNLOAD_MODE, etc.
# Top-level overrides (optional): YTPL_YT_DLP_PATH, YTPL_FFMPEG_PATH, YTPL_ARIA2C_PATH,
# YTPL_MAX_PARALLEL_DOWNLOADS, YTPL_ARIAC2_CONNECTIONS, YTPL_MAX_VIDEO_QUALITY, YTPL_DOWNLOAD_MODE

if [ -n "${YTPL_CONFIG_JSON:-}" ] || [ -n "${YTPL_PLAYLISTS_JSON:-}" ] || env | grep -q '^PLAYLIST_' || [ -n "${YTPL_YT_DLP_PATH:-}" ] || [ -n "${YTPL_FFMPEG_PATH:-}" ] || [ -n "${YTPL_ARIA2C_PATH:-}" ]; then
  python - <<'PY'
import os, json, sys
from pathlib import Path

config_dir = Path('/app/config')
config_dir.mkdir(parents=True, exist_ok=True)
config_path = config_dir / 'yt-playlist-config.json'

# Load existing config if present, otherwise start with a minimal default
base = {
  'playlists': [
    {
      'url': 'https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID_HERE',
      'download_mode': 'audio',
      'max_video_quality': '1080p',
      'save_path': './downloads',
      'archive': 'archive.txt'
    }
  ],
  'yt_dlp_path': 'yt-dlp',
  'ffmpeg_path': 'ffmpeg',
  'aria2c_path': 'aria2c',
  'max_parallel_downloads': 10,
  'aria2c_connections': 8,
}

if config_path.exists():
  try:
    with config_path.open('r', encoding='utf-8') as f:
      base = json.load(f)
  except Exception:
    # if existing file is invalid, continue with our base and overwrite below
    pass

# 1) Full config JSON
cfg_json = os.environ.get('YTPL_CONFIG_JSON')
if cfg_json:
  try:
    cfg = json.loads(cfg_json)
    with config_path.open('w', encoding='utf-8') as f:
      json.dump(cfg, f, indent=2)
  except Exception as e:
    print('ERROR: failed to parse YTPL_CONFIG_JSON:', e, file=sys.stderr)
    sys.exit(1)
  sys.exit(0)

# 2) Playlists JSON
pl_json = os.environ.get('YTPL_PLAYLISTS_JSON')
if pl_json:
  try:
    playlists = json.loads(pl_json)
    if isinstance(playlists, list):
      base['playlists'] = playlists
    else:
      raise ValueError('YTPL_PLAYLISTS_JSON must be a JSON array')
  except Exception as e:
    print('ERROR: failed to parse YTPL_PLAYLISTS_JSON:', e, file=sys.stderr)
    sys.exit(1)

# 3) Indexed PLAYLIST_{N}_{FIELD} variables
playlists = {}
for k, v in os.environ.items():
  if not k.startswith('PLAYLIST_'):
    continue
  parts = k.split('_', 2)
  if len(parts) < 3:
    continue
  _, idx, field = parts
  try:
    i = int(idx)
  except Exception:
    continue
  playlists.setdefault(i, {})[field.lower()] = v

if playlists:
  # convert to ordered list
  built = [playlists[i] for i in sorted(playlists.keys())]
  base['playlists'] = built

# Top-level overrides
overrides = {
  'yt_dlp_path': 'YTPL_YT_DLP_PATH',
  'ffmpeg_path': 'YTPL_FFMPEG_PATH',
  'aria2c_path': 'YTPL_ARIA2C_PATH',
  'max_parallel_downloads': 'YTPL_MAX_PARALLEL_DOWNLOADS',
  'aria2c_connections': 'YTPL_ARIA2C_CONNECTIONS',
  'max_video_quality': 'YTPL_MAX_VIDEO_QUALITY',
  'download_mode': 'YTPL_DOWNLOAD_MODE',
}
for key, envname in overrides.items():
  if envname in os.environ and os.environ[envname] != '':
    val = os.environ[envname]
    # cast numbers where appropriate
    if key in ('max_parallel_downloads', 'aria2c_connections'):
      try:
        val = int(val)
      except Exception:
        pass
    base[key] = val

# Write resulting config
try:
  with config_path.open('w', encoding='utf-8') as f:
    json.dump(base, f, indent=2)
except Exception as e:
  print('ERROR: failed to write config file:', e, file=sys.stderr)
  sys.exit(1)

PY
fi

# Allow the user to pass extra args to the container
if [ "$#" -gt 0 ]; then
  exec python -m ytplaylist.cli $ARGS "$@"
else
  exec python -m ytplaylist.cli $ARGS
fi
