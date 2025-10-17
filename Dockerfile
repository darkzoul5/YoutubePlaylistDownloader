FROM python:3.12-alpine

WORKDIR /app

COPY yt-playlist-main.py /app/
COPY ./bin/ffmpeg /app/bin
COPY ./bin/yt-dlp /app/bin
COPY ./bin/aria2c /app/bin

CMD ["python", "yt-playlist-main.py"]
