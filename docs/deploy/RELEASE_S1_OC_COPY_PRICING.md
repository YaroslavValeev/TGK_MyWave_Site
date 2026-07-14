# Release S1 — Online Coaching copy and pricing

**Status:** ready for PR / Owner GO for deploy  
**Base SHA (production pin):** `d9b68b75c81fd256da13fcde5756d17594bb56fa`  
**Rollback SHA:** `d9b68b75c81fd256da13fcde5756d17594bb56fa` (same until S1 deployed)  
**Branch:** `release/s1-oc-copy-pricing`  
**Scope:** Online Coaching public copy/pricing + P0 rate-limit fix. No YClients, Camp, Blog, Parser, `.env`.

## P0 rate-limit (included in unified release)

- Removed hardcoded global `200/day` + `50/hour` Flask-Limiter defaults.
- Public GET (HTML, `/health`, `/static`, `/robots.txt`, `/sitemap.xml`) are not throttled by a small global bucket.
- Endpoint-specific limits remain for login, booking, forms, chat, payment, admin auth (env-configurable).
- Production expects `RATELIMIT_STORAGE_URI=redis://127.0.0.1:6379/0` and `TRUST_PROXY=1` behind Nginx.

## Changes

1. «Эффективный месяц»: **12 000 ₽ / месяц** (was erroneously «/ сет» on public page).
2. `#oc-film`: first tip → «Из катера снимать на 1х.»; removed tripod/lighting bullet.
3. Canonical `format_service_price()` in `online_coaching_schema.py` for T-Bank description and Telegram payment hints.
4. Product spec aligned: `docs/products/ONLINE_COACHING_SPEC.md`.

## Anti-scope (explicitly NOT in S1)

- YClients / booking
- Camp
- Blog
- ParserNews
- Mobile polish / chat overlap (→ Release S2)
- `.env` / production flags

## Tests

```bash
pytest tests/unit/test_online_coaching_schema.py tests/unit/test_online_coaching_public_copy.py tests/unit/test_rate_limit_p0.py -q
```

## Deploy (only after Owner GO)

| Field | Value |
|---|---|
| Проект | Site MyWave (`mywavewake.ru`) |
| Сервер | `4169037-ep26382` |
| IP/hostname | `62.113.42.227` |
| Терминал | SSH session as deploy user |
| Рабочая директория | `/var/www/mywave` |
| Сервис (можно перезапускать) | `mywave-site.service` |
| Сервисы (запрещено трогать) | `mywave-node`, `mywave-telegram-bot`, TGbotAdmin |
| Rollback SHA | `d9b68b75c81fd256da13fcde5756d17594bb56fa` |

```bash
cd /var/www/mywave
git fetch origin release/s1-oc-copy-pricing
git checkout release/s1-oc-copy-pricing
git pull --ff-only origin release/s1-oc-copy-pricing
# verify HEAD matches release commit SHA from PR
sudo systemctl restart mywave-site.service
sleep 15
curl -fsS https://mywavewake.ru/health
curl -fsS https://mywavewake.ru/services/online-coaching | grep -F "12 000 ₽ / месяц"
```

**Rollback:**

```bash
cd /var/www/mywave
git checkout d9b68b75c81fd256da13fcde5756d17594bb56fa
sudo systemctl restart mywave-site.service
curl -fsS https://mywavewake.ru/health
```

**Ожидаемый результат:** health PASS; на `/services/online-coaching` цена «Эффективный месяц» = «12 000 ₽ / месяц»; в блоке «Как снять видео» первый пункт — «Из катера снимать на 1х.»
