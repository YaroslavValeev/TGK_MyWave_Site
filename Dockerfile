# MyWave web: Flask + Gunicorn (eventlet worker для Socket.IO)
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN mkdir -p prometheus_multiproc logs

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=15s --start-period=40s --retries=3 \
  CMD curl -fsS http://127.0.0.1:5000/health >/dev/null || exit 1

CMD ["gunicorn", "-c", "gunicorn.conf.py", "main:app"]
