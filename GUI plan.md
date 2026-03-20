# GUI Plan

## Python-first Desktop Architecture

- **Primary GUI framework**: `PySide6` (Qt for Python).
- **Communication Layer**: A local `FastAPI` backend to separate core logic from the UI.
- **IPC Mechanism**: The GUI spawns the FastAPI server on a random high port (binding to `127.0.0.1` ONLY) and communicates via REST/WebSockets.

## Core Features to Implement

1. **Dashboard Overview**: List all tracked playlists, their status (Last Sync), and total size.
2. **Interactive Configuration**: Wizard-style setup for new playlists (URL detection, folder picker).
3. **Queue Manager**: Visual progress bars for active downloads, showing speed, ETA, and current video title.
4. **Log Viewer**: Real-time streaming of yt-dlp logs for troubleshooting.
5. **Settings Panel**: Global settings for binary paths (ffmpeg, aria2c), max parallel jobs, and Docker detection toggle.

## Phase 1 Roadmap: "The Bridge"

- [ ] **Refactor `src/manager.py`**: Convert CLI-first execution to async-compatible methods for FastAPI consumption.
- [ ] **FastAPI Integration**: Create endpoints for `/playlists`, `/status`, and `/download/start`.
- [ ] **PySide6 Skeleton**: Basic window with `QWebEngine` (if hybrid) or native `QWidget` dashboard.
- [ ] **Packaging**: `pyinstaller` configuration to bundle both backend and frontend into a single `.exe`.

## Packaging & Distribution (brief)

- Bundle the backend and GUI into one distributable. The GUI should spawn the local API process (background subprocess) on startup.
- Windows: use `pyinstaller` or `briefcase` to create an executable/installer. Consider creating an MSI or Inno Setup installer for a polished UX.
- Linux: provide AppImage, Snap, or distribution-specific packages (deb/rpm) — AppImage is a good starting point for single-file distribution.
- Security: bind the local API to `localhost` only, use a short-lived token or IPC for authentication between GUI and backend, and avoid exposing unnecessary ports.

## Roadmap (GUI → Web → Mobile)

1. Desktop prototype: `FastAPI` backend + `PySide6` GUI (thin client) with basic playlist add/update/download controls and status streaming.
2. Packaging: create Windows exe/installer and Linux AppImage for the prototype.
3. Web frontend: build a web SPA that consumes the same backend API (hosted or local) — this reuses business logic with minimal change.
4. Android: either a native app or cross-platform UI (Flutter/React Native) that calls the backend API; alternatively host the backend and make a thin mobile client.

If you want, I can now: scaffold a minimal `FastAPI` backend and `PySide6` desktop starter in this repo, or produce concise packaging steps for Windows and Linux. Which do you prefer?
