from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import Optional, Tuple


class DependencyError(RuntimeError):
    pass


@dataclass(frozen=True)
class DependencyStatus:
    yt_dlp_ok: bool
    yt_dlp_version: Optional[str]
    ffmpeg_ok: bool
    ffmpeg_path: Optional[str]
    ffprobe_ok: bool
    ffprobe_path: Optional[str]


def get_yt_dlp_version() -> Optional[str]:
    try:
        import yt_dlp  # type: ignore

        # yt-dlp exposes version in different places depending on install
        return getattr(yt_dlp, "__version__", None) or getattr(getattr(yt_dlp, "version", None), "__version__", None)
    except Exception:
        return None


def ensure_yt_dlp_available() -> str:
    """
    Ensures yt-dlp Python package is importable. Returns version string when known.
    """
    try:
        import yt_dlp  # noqa: F401  # type: ignore
    except Exception as exc:
        raise DependencyError("yt-dlp Python package is required. Install with: pip install -U yt-dlp") from exc
    return get_yt_dlp_version() or "unknown"


def _resolve_tool_paths(tool_hint: Optional[str], exe_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (resolved_exe_path, resolved_dir_hint).
    - If tool_hint is a file path, use it.
    - If tool_hint is a directory, append exe_name.
    - Otherwise, treat tool_hint as a command and fall back to PATH resolution.
    """
    if tool_hint:
        hint_str = str(tool_hint).strip().strip('"').strip("'")
        hint = Path(hint_str)
        # Expand envvars (%FFMPEG%) etc.
        expanded = Path(os.path.expandvars(str(hint)))
        if expanded.is_dir():
            cand = expanded / exe_name
            if cand.exists():
                return str(cand), str(expanded)
        if expanded.exists():
            return str(expanded), str(expanded.parent)

    # PATH lookup
    found = which(exe_name)
    if found:
        return found, str(Path(found).parent)
    return None, None


def ensure_ffmpeg_available(ffmpeg_hint: Optional[str]) -> Tuple[str, str]:
    """
    Ensures ffmpeg is runnable. Returns (ffmpeg_path, ffmpeg_path).

    Note: ffprobe is intentionally not required. This project uses ffmpeg directly for
    audio extraction, and yt-dlp can still function for muxed downloads without ffprobe.
    """
    ffmpeg_exe = "ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg"

    ffmpeg_path, ffmpeg_dir = _resolve_tool_paths(ffmpeg_hint, ffmpeg_exe)
    if not ffmpeg_path:
        raise DependencyError("ffmpeg not found. Install ffmpeg or set 'ffmpeg_path' in config.")

    # Smoke test (fast)
    try:
        subprocess.run([ffmpeg_path, "-version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as exc:
        raise DependencyError("ffmpeg exists but is not runnable. Check permissions/architecture/path.") from exc

    # Keep return shape stable for existing callers
    return ffmpeg_path, ffmpeg_path
