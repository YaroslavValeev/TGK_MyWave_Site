# Owner — Parser fix: stop minting `file (N).ext`

**Status 2026-07-31:** **CLOSED PASS** on `/opt/bot3/parser-new-bot`  
- patched: `utils/media_utils.py`, `utils/helpers.py`  
- `collectors/telegram_parser.py` → `download_media_helper` from helpers (no local dir-mode)  
- paths: `tg_{chat}_{mid}` overwrite · sized `(N)` count **0** · parser `active`

**Root cause:** Telethon `download_media(file="downloads/")` (directory) kept original names → `IMG_… (1).MOV`.

**Script:** `docs/deploy/scripts/patch_parser_no_dup_n.py`  
**Не вставляйте большой python heredoc в SSH** — только curl + python3.


---

## 0) Diagnose (сейчас — paste сломался)

```bash
cd /opt/bot3/parser-new-bot
```

```bash
grep -n 'download_media\|file=download_dir\|file="downloads/"\|tg_' utils/media_utils.py | tail -20
```

```bash
grep -n 'download_media\|file="downloads/"\|tg_' utils/helpers.py collectors/telegram_parser.py | head -40
```

```bash
systemctl is-active parser-news-bot
```

Пришлите вывод, если apply не пройдёт.

---

## 1) Backup (по одной строке)

```bash
cd /opt/bot3/parser-new-bot
```

```bash
TS=$(date +%Y%m%d_%H%M%S); echo bak=$TS
```

```bash
sudo cp -a utils/media_utils.py utils/media_utils.py.bak_${TS}
```

```bash
sudo cp -a collectors/telegram_parser.py collectors/telegram_parser.py.bak_${TS}
```

```bash
sudo cp -a utils/helpers.py utils/helpers.py.bak_${TS}
```

---

## 2) Download script + apply

```bash
curl -fsSL -o /tmp/patch_parser_no_dup_n.py \
  https://raw.githubusercontent.com/YaroslavValeev/TGK_MyWave_Site/main/docs/deploy/scripts/patch_parser_no_dup_n.py
```

```bash
wc -l /tmp/patch_parser_no_dup_n.py; head -3 /tmp/patch_parser_no_dup_n.py
```

```bash
sudo PARSER_ROOT=/opt/bot3/parser-new-bot python3 /tmp/patch_parser_no_dup_n.py
```

**PASS apply:** строки `patched ...` и `VERIFY_OK` / `OK`.

---

## 3) Restart + verify

```bash
sudo systemctl restart parser-news-bot
```

```bash
systemctl is-active parser-news-bot
```

```bash
grep -nE 'file="downloads/"|file=download_dir\)' \
  /opt/bot3/parser-new-bot/utils/media_utils.py \
  /opt/bot3/parser-new-bot/utils/helpers.py \
  /opt/bot3/parser-new-bot/collectors/telegram_parser.py \
  || echo 'no directory-mode (good)'
```

```bash
sudo find /opt/bot3/parser-new-bot/downloads -xdev -type f -name '* ([0-9]*).*' ! -size 0 | wc -l
```

```bash
curl -fsS https://mywavewake.ru/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status"))'
```

---

## Rollback

```bash
cd /opt/bot3/parser-new-bot
# подставьте TS
sudo cp -a utils/media_utils.py.bak_TS utils/media_utils.py
sudo cp -a collectors/telegram_parser.py.bak_TS collectors/telegram_parser.py
sudo cp -a utils/helpers.py.bak_TS utils/helpers.py
sudo systemctl restart parser-news-bot
```
