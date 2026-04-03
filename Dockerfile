# GPU hosts: use nvidia/cuda base and install Python; this image targets CPU/stub CI + dev.
FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src /app/src
ENV PYTHONPATH=/app/src

EXPOSE 4100
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://127.0.0.1:4100/health || exit 1

# API server (override for worker)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "4100", "--app-dir", "/app/src"]
