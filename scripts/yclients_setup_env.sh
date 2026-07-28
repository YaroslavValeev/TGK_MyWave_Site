#!/usr/bin/env bash
# Безопасная настройка YCLIENTS токенов (без склейки команд).
# Запуск:
#   bash /var/www/mywave/scripts/yclients_setup_env.sh
set -euo pipefail

cd /var/www/mywave
umask 077

echo "=== MyWave YCLIENTS setup ==="
echo "Сейчас в .env НЕТ partner/user token — их нужно вставить вручную."
echo "Возьмите Partner token в ЛК разработчика: https://clck.ru/3REPzB"
echo

read -r -p "Partner token (Токен партнера): " PARTNER_TOKEN
if [[ -z "${PARTNER_TOKEN}" ]]; then
  echo "ERROR: Partner token пустой — выход" >&2
  exit 1
fi

echo
echo "User token: либо вставьте готовый, либо оставьте пустым и получите через login/password."
read -r -p "User token (можно пусто): " USER_TOKEN

if [[ -z "${USER_TOKEN}" ]]; then
  read -r -p "YCLIENTS login (email/телефон): " YC_LOGIN
  read -r -s -p "YCLIENTS password: " YC_PASSWORD
  echo
  export YCLIENTS_PARTNER_TOKEN="$PARTNER_TOKEN"
  export YCLIENTS_USER_PASSWORD="$YC_PASSWORD"
  source venv/bin/activate
  USER_TOKEN="$(python scripts/yclients_auth_user_token.py --login "$YC_LOGIN" | tail -n 1)"
  unset YCLIENTS_USER_PASSWORD
  if [[ -z "${USER_TOKEN}" ]]; then
    echo "ERROR: не удалось получить user token" >&2
    exit 1
  fi
  echo "User token получен (len=${#USER_TOKEN})"
fi

WEBHOOK_SECRET="$(openssl rand -hex 24)"
GATEWAY_SECRET="$(openssl rand -hex 24)"

TS="$(date +%Y%m%d_%H%M%S)"
cp -a .env ".env.bak_yclients_setup_${TS}"

export PARTNER_TOKEN USER_TOKEN WEBHOOK_SECRET GATEWAY_SECRET
python3 <<'PY'
from pathlib import Path
import os

path = Path(".env")
updates = {
    "YCLIENTS_ENABLED": "0",  # сначала 0; включите после smoke
    "YCLIENTS_READ_ONLY_ENABLED": "1",
    "YCLIENTS_WRITE_ENABLED": "0",
    "YCLIENTS_COMPANY_ID": "2043174",
    "YCLIENTS_API_BASE_URL": "https://api.yclients.com/api/v1",
    "YCLIENTS_ACCEPT": "application/vnd.yclients.v2+json",
    "YCLIENTS_PARTNER_TOKEN": os.environ["PARTNER_TOKEN"],
    "YCLIENTS_USER_TOKEN": os.environ["USER_TOKEN"],
    "YCLIENTS_WEBHOOK_SECRET": os.environ["WEBHOOK_SECRET"],
    "YCLIENTS_GATEWAY_SECRET": os.environ["GATEWAY_SECRET"],
    "BOAT_PROVIDER": "yclients",
    "BOAT_SLOT_DURATION_MINUTES": "30",
    "BOAT_CAPACITY": "1",
}
lines = path.read_text(encoding="utf-8").splitlines()
seen = set()
out = []
for line in lines:
    s = line.strip()
    if s and not s.startswith("#") and "=" in line:
        k = line.split("=", 1)[0].strip()
        if k in updates:
            out.append(f"{k}={updates[k]}")
            seen.add(k)
            continue
    out.append(line)
for k, v in updates.items():
    if k not in seen:
        out.append(f"{k}={v}")
path.write_text("\n".join(out) + "\n", encoding="utf-8")
print("OK: .env updated")
print("WEBHOOK_URL=https://mywavewake.ru/public/integrations/yclients/webhook?token=" + os.environ["WEBHOOK_SECRET"])
print("GATEWAY_SECRET=" + os.environ["GATEWAY_SECRET"])
PY

chown www-data:www-data .env
chmod 600 .env

echo
echo "=== проверка ключей (без значений) ==="
python3 <<'PY'
from pathlib import Path
vals={}
for line in Path('.env').read_text(encoding='utf-8').splitlines():
    s=line.strip()
    if not s or s.startswith('#') or '=' not in line: continue
    k,v=line.split('=',1); vals[k.strip()]=v.strip()
for k in ['YCLIENTS_ENABLED','YCLIENTS_PARTNER_TOKEN','YCLIENTS_USER_TOKEN','YCLIENTS_WEBHOOK_SECRET','YCLIENTS_GATEWAY_SECRET']:
    v=vals.get(k,'')
    if k.endswith(('TOKEN','SECRET')):
        print(f'{k}: {"SET len="+str(len(v)) if v else "MISSING"}')
    else:
        print(f'{k}: {v!r}')
PY

echo
echo "Дальше выполните ТОЛЬКО эти 4 команды (по одной):"
echo "  source venv/bin/activate"
echo "  set -a; source .env; set +a"
echo "  export YCLIENTS_ENABLED=1 YCLIENTS_READ_ONLY_ENABLED=1 YCLIENTS_WRITE_ENABLED=0"
echo "  python scripts/yclients_discover.py"
