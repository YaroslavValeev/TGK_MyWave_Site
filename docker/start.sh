#!/bin/bash
set -e

# Start Gunicorn with configuration
exec gunicorn \
    --bind 0.0.0.0:8080 \
    --workers 4 \
    --worker-class eventlet \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    "${APP_MODULE:-main:app}"

