#!/usr/bin/env bash
# Быстрое восстановление чата на prod: таблица chat_message + миграции.
set -euo pipefail
cd /var/www/mywave
source venv/bin/activate
export FLASK_CONFIG=production

echo "=== git pull (последние миграции) ==="
git pull

echo "=== flask db upgrade ==="
if ! flask db upgrade; then
  echo "WARN: upgrade failed — создаём chat_message вручную"
  python scripts/ensure_chat_message_table.py
fi

echo "=== проверка chat_message ==="
python scripts/chat_persistence_check.py --config production

echo "=== restart ==="
sudo systemctl restart mywave-site
echo "DONE"
