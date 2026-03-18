FROM python:3.12-alpine

WORKDIR /app

# Copy application code (package) and bootstrap
COPY yt-playlist-main.py /app/
COPY ytpld/ /app/ytpld/
COPY config/ /app/config/

# Copy helper binaries from the build context (which includes extracted artifacts)
COPY bin/ffmpeg /app/bin/ffmpeg
COPY bin/yt-dlp /app/bin/yt-dlp
COPY bin/aria2c /app/bin/aria2c

# Copy entrypoint that maps environment variables to CLI flags
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh && chmod +x /app/bin/* || true

# Put the bundled bin directory first in PATH
ENV PATH="/app/bin:${PATH}"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD [""]
