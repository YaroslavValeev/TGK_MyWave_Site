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

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
HTTP_CODE="$(curl -fsS --max-time 15 -o "$TMP" -w '%{http_code}' "$URL" || echo "000")"
STATUS="$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('status',''))" "$TMP" 2>/dev/null || echo "")"

if [[ "$HTTP_CODE" != "200" ]] || [[ "$STATUS" == "unhealthy" ]]; then
  MSG="MyWave: healthcheck failed ${URL} http=${HTTP_CODE} status=${STATUS:-unknown}"
  logger -t mywave-healthcheck "$MSG" || true
  if [[ -n "$BOT" && -n "$CHAT" ]]; then
    curl -fsS -X POST "https://api.telegram.org/bot${BOT}/sendMessage" \
      -d "chat_id=${CHAT}" \
      --data-urlencode "text=⚠️ ${MSG}" >/dev/null || true
  fi
  exit 1
fi
exit 0
