FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies: aria2, ffmpeg, yt-dlp
# Use --no-install-recommends to keep image small and clean up apt lists
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
	   ca-certificates \
	   aria2 \
	   ffmpeg \
	   yt-dlp \
	&& rm -rf /var/lib/apt/lists/*

COPY yt-playlist-main.py /app/

CMD ["python", "yt-playlist-main.py"]
