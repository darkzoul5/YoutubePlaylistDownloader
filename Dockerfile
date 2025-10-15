FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y aria2 ffmpeg yt-dlp
COPY yt-playlist-main.py /app/
CMD ["python", "yt-playlist-main.py"]
