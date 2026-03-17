### Python-first

- Primary GUI framework: `PySide6` (Qt for Python) — native desktop look, cross-platform on Windows and Linux, mature widget set, good documentation.
- Desktop architecture: keep the core downloader logic as a Python package and expose a local HTTP/WebSocket API (e.g., `FastAPI`) that the GUI talks to. The GUI stays a thin client that issues commands and receives status updates.

### Why this approach

- Stay in Python end-to-end for now, minimizing new languages or runtimes.
- A local API boundary lets you reuse the same backend for a future Web frontend (React/Next.js or plain SPA) and for Android (native or Flutter shell that talks to the API or a hosted API).
- `PySide6` provides a polished native desktop UX and easier packaging for Windows/Linux compared with Python mobile toolkits.

### Packaging & Distribution (brief)

- Bundle the backend and GUI into one distributable. The GUI should spawn the local API process (background subprocess) on startup.
- Windows: use `pyinstaller` or `briefcase` to create an executable/installer. Consider creating an MSI or Inno Setup installer for a polished UX.
- Linux: provide AppImage, Snap, or distribution-specific packages (deb/rpm) — AppImage is a good starting point for single-file distribution.
- Security: bind the local API to `localhost` only, use a short-lived token or IPC for authentication between GUI and backend, and avoid exposing unnecessary ports.

### Roadmap (GUI → Web → Mobile)

1. Desktop prototype: `FastAPI` backend + `PySide6` GUI (thin client) with basic playlist add/update/download controls and status streaming.
2. Packaging: create Windows exe/installer and Linux AppImage for the prototype.
3. Web frontend: build a web SPA that consumes the same backend API (hosted or local) — this reuses business logic with minimal change.
4. Android: either a native app or cross-platform UI (Flutter/React Native) that calls the backend API; alternatively host the backend and make a thin mobile client.

If you want, I can now: scaffold a minimal `FastAPI` backend and `PySide6` desktop starter in this repo, or produce concise packaging steps for Windows and Linux. Which do you prefer? 
