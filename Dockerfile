FROM python:3.12-slim
WORKDIR /app
COPY yt-playlist-main.py /app/
COPY bin/aria2c.exe /app/bin/
COPY bin/ffmpeg.exe /app/bin/
COPY bin/yt-dlp.exe /app/bin/
ENV PATH="/app/bin:$PATH"
CMD ["python", "yt-playlist-main.py"]
