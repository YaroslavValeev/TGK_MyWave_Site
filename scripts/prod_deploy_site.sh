#!/usr/bin/env bash
# Полный деплой на prod: код, CHAT_BACKEND, миграции, чат, рестарт, smoke.
# Запуск на сервере:
#   cd /var/www/mywave && bash scripts/prod_deploy_site.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/mywave}"
cd "$APP_DIR"

if [[ ! -f venv/bin/activate ]]; then
  echo "FAIL: нет venv в $APP_DIR"
  exit 1
fi

# shellcheck source=/dev/null
source venv/bin/activate
export FLASK_CONFIG=production
export PYTHONPATH="$APP_DIR"

echo "=== git pull ==="
git pull

echo "=== .env: CHAT_BACKEND=completions (без Assistant API / geo 403) ==="
ENV_FILE="$APP_DIR/.env"
if [[ -f "$ENV_FILE" ]]; then
  cp -a "$ENV_FILE" "${ENV_FILE}.bak.$(date +%Y%m%d-%H%M%S)"
  if grep -q '^CHAT_BACKEND=' "$ENV_FILE"; then
    sed -i 's/^CHAT_BACKEND=.*/CHAT_BACKEND=completions/' "$ENV_FILE"
  else
    echo 'CHAT_BACKEND=completions' >> "$ENV_FILE"
  fi
  if ! grep -q '^GPTS_MODEL=' "$ENV_FILE"; then
    echo 'GPTS_MODEL=gpt-4.1-nano' >> "$ENV_FILE"
  fi
  echo "Текущие настройки чата:"
  grep -E '^(CHAT_BACKEND|GPTS_MODEL|OPENAI_HTTP_PROXY|ASSISTANT_ID)=' "$ENV_FILE" || true
else
  echo "WARN: $ENV_FILE не найден — задайте CHAT_BACKEND=completions вручную"
fi

echo "=== flask db upgrade ==="
if ! flask db upgrade; then
  echo "WARN: upgrade failed — ensure chat_message"
  python scripts/ensure_chat_message_table.py
fi

echo "=== chat_message check ==="
python scripts/chat_persistence_check.py --config production

echo "=== restart mywave-site ==="
sudo systemctl restart mywave-site
sleep 2
sudo systemctl is-active mywave-site

echo "=== HTTP smoke ==="
MYWAVE_BASE_URL="${MYWAVE_BASE_URL:-https://mywavewake.ru}" bash scripts/production_smoke.sh

echo "=== chat API smoke (KB / completions, без браузера) ==="
BASE="${MYWAVE_BASE_URL:-https://mywavewake.ru}"
BASE="${BASE%/}"
CHAT_BODY='{"message":"как попасть в кемп?"}'
CHAT_RESP="$(curl -sS --max-time 60 -X POST "$BASE/chat/api" \
  -H 'Content-Type: application/json' \
  -d "$CHAT_BODY" || true)"
if echo "$CHAT_RESP" | grep -q '"response"'; then
  echo "OK   chat/api  (есть поле response)"
  echo "$CHAT_RESP" | head -c 400
  echo
else
  echo "FAIL chat/api  ответ: $CHAT_RESP"
  exit 1
fi

echo
echo "=== DONE ==="
echo "Проверьте в браузере (инкогнито / Ctrl+F5): главная mobile hero + чат."
echo "Логи: journalctl -u mywave-site -f --since '2 min ago'"
