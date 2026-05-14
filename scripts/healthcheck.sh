#!/usr/bin/env bash
# Скрипт для cron: проверка /health + алерт в Telegram.
# Права: chmod +x scripts/healthcheck.sh
# Cron: */5 * * * * /var/www/mywave/scripts/healthcheck.sh >> /var/log/mywave/healthcheck.log 2>&1
set -euo pipefail

ROOT="${MYWAVE_ROOT:-/var/www/mywave}"
ENV_FILE="${MYWAVE_ENV_FILE:-$ROOT/.env}"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a && source "$ENV_FILE" && set +a
fi

URL="${HEALTHCHECK_URL:-https://mywavewake.ru/health}"
BOT="${ALERT_TELEGRAM_BOT_TOKEN:-${NOTIFICATION_BOT_TOKEN:-}}"
CHAT="${ALERT_TELEGRAM_CHAT_ID:-${TRAINER_CHAT_ID:-}}"

if ! curl -fsS --max-time 15 "$URL" >/dev/null; then
  MSG="MyWave: healthcheck failed ${URL}"
  logger -t mywave-healthcheck "$MSG" || true
  if [[ -n "$BOT" && -n "$CHAT" ]]; then
    curl -fsS -X POST "https://api.telegram.org/bot${BOT}/sendMessage" \
      -d "chat_id=${CHAT}" \
      --data-urlencode "text=⚠️ ${MSG}" >/dev/null || true
  fi
  exit 1
fi
exit 0
