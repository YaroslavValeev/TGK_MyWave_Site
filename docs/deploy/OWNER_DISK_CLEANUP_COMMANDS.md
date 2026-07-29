# Owner — диск prod (диагностика → safe clean)

**Сервер:** 4169037-ep26382 · `/` ~89% (44G/50G)  
**Цель:** освободить место **без** поломки Site / bot / Camp  

**Не трогать без отдельного GO:** `/opt/bot3`, `/opt/bot2`, `/opt/mywave-bot`, `/var/backups`, `mywave-node`, live DB/uploads.

---

## Phase 0 — что уже ясно

| Путь | ~размер | Роль |
|------|---------|------|
| `/var/www/mywave` | ~2.4–5G | **Site** (LIVE) |
| `/opt/mywave-bot` | ~0.6G | **Telegram bot** booking (LIVE) |
| `/opt/bot3` | **~9.9G** | другой бот/проект — не удалять вслепую |
| `/opt/bot2` | ~0.3G | другой бот |
| `/var/backups` | **~4.8G** | бэкапы — смотреть даты, не rm -rf |
| `/var/lib` | **~14G** | docker/db/apt и т.п. — сначала `du` |
| `/var/log` + journal | ~0.7–1G | можно vacuum |
| `/root/.cursor-server` | ~0.8G | IDE remote — можно позже |
| `/root/TGK_MyWave` | ~0.7G | копия репо? — проверить |

---

## Phase 1 — диагностика (только чтение) → пришлите вывод

```bash
df -h /

echo '=== /var/lib top ==='
sudo du -xh /var/lib --max-depth=2 2>/dev/null | sort -h | tail -20

echo '=== /var/backups ==='
sudo du -xh /var/backups --max-depth=2 2>/dev/null | sort -h | tail -15
sudo ls -lah /var/backups | head -40

echo '=== /opt ==='
sudo du -xh /opt --max-depth=2 2>/dev/null | sort -h | tail -20
sudo ls -lah /opt/bot3 2>/dev/null | head -20
sudo du -xh /opt/bot3 --max-depth=2 2>/dev/null | sort -h | tail -15

echo '=== systemd units (bots) ==='
systemctl list-units --type=service --all 'mywave*' 'bot*' 2>/dev/null | head -40
ls /etc/systemd/system/*bot* /etc/systemd/system/mywave* 2>/dev/null

echo '=== docker? ==='
command -v docker >/dev/null && sudo docker system df || echo 'no docker'
```

**PASS Phase 1:** есть картина `/var/lib`, `/var/backups`, `/opt/bot3`, какие unit’ы active.

---

## Phase 2 — SAFE clean (можно сразу после Phase 1 или параллельно)

Ничего из `/opt` / `/var/backups` / site uploads.

```bash
# до
df -h /

# journal → ~200M
sudo journalctl --vacuum-size=200M

# apt cache
sudo apt-get clean
sudo apt-get autoremove -y

# старые ротированные логи (только *.gz / уже закрытые)
sudo find /var/log -type f -name '*.gz' -mtime +14 -print
# если список ок — удалить:
sudo find /var/log -type f -name '*.gz' -mtime +14 -delete

# site: мусорные метрики (если gunicorn/prometheus multiprocess разросся)
# ОСТОРОЖНО: только при остановленном/рестартуемом site — делаем через restart
sudo systemctl stop mywave-site
sudo find /var/www/mywave/prometheus_multiproc -type f -delete 2>/dev/null || true
sudo systemctl start mywave-site
sleep 3
systemctl is-active mywave-site
curl -fsS https://mywavewake.ru/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status"))'

df -h /
```

**Ожидание:** +0.3–0.8G минимум (journal+apt); +~150M если multiproc чистили.

---

## Phase 3 — только после вашего GO (из вывода Phase 1)

Шаблоны (не запускать вслепую):

```bash
# A) старые .tar.gz в /var/backups старше 30 дней — ПОСЛЕ ls и вашего OK
# sudo find /var/backups -type f \( -name '*.tar.gz' -o -name '*.tgz' -o -name '*.sql.gz' \) -mtime +30 -ls
# sudo find /var/backups -type f \( -name '*.tar.gz' -o -name '*.tgz' -o -name '*.sql.gz' \) -mtime +30 -delete

# B) docker prune — только если docker есть и вы GO
# sudo docker system prune -af   # опасно для неиспользуемых образов

# C) /opt/bot3 — НЕ удалять; сначала: git remote, systemd unit, last modified
# ls -la /opt/bot3; systemctl status … ; du …
```

---

## Rollback / стоп

- Site не поднялся после multiproc clean → `sudo systemctl restart mywave-site` + `journalctl -u mywave-site -n 50`
- Лишнее удалили из backups → восстановление только если есть внешняя копия

---

## Критерий успеха

- `/` ≤ ~80–85% или ≥8G free  
- `mywave-site` + `mywave-telegram-bot` active · health ok · `/blog` 200  
- Camp cron не трогали  
