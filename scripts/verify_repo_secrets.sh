#!/usr/bin/env bash
# Поиск типичных следов секретов (нужен ripgrep: rg).
# Запуск: bash scripts/verify_repo_secrets.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v rg &>/dev/null; then
  echo "Установите ripgrep (команда: rg)." >&2
  exit 2
fi

ec=0
rgq() { rg -n -S --hidden "$@" . 2>/dev/null || true; }

echo "=== sk- (возможные API-ключи) ==="
out=$(rgq --glob "!.env" --glob "!.env.*" --glob "!.git/*" --glob "!**/node_modules/**" --glob "!**/venv/**" --glob "!.venv/**" --glob "!**/venv_backup*/**" "sk-[a-zA-Z0-9]{20,}")
if [ -n "$out" ]; then
  echo "$out" | head -n 40
  echo "^^^ Проверьте вручную" >&2
  ec=1
else
  echo "Совпадений не найдено."
fi

echo "=== ghp_|github_pat_ ==="
out=$(rgq --glob "!.env" --glob "!.env.*" --glob "!.git/*" "ghp_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+")
if [ -n "$out" ]; then
  echo "$out" | head -n 40
  echo "^^^ Проверьте вручную" >&2
  ec=1
else
  echo "Совпадений не найдено."
fi

echo "Код выхода: $ec"
exit "$ec"
