#!/usr/bin/env bash
# Проверка чистой установки зависимостей и импорта main:app (Python 3.11+).
# Использование: bash scripts/import_preflight.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${IMPORT_PREFLIGHT_VENV:-/tmp/mw-import-preflight-venv}"
PYTHON="${PYTHON:-python3.11}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  PYTHON=python3
fi

echo "Using: $($PYTHON --version 2>&1)"
rm -rf "$VENV_DIR"
"$PYTHON" -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --upgrade pip wheel
pip install -r "$ROOT/requirements.txt"
cd "$ROOT"
export ENABLE_GOOGLE_SERVICES=0
export FLASK_ENV=testing
export FLASK_CONFIG=testing
python -c "import main; print('main import OK')"
echo "import_preflight OK"
