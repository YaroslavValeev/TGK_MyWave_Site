# SpotMap на проде — команды для сервера

Цель: `https://map.mywavewake.ru/embed?host=mywave` → iframe на `https://mywavewake.ru/projects`.

Код SpotMap **не** копировать в Site_MyWave. На сайте уже iframe + CSP.

---

## 0) DNS (панель Timeweb / регистратор)

Создать A-запись:

```text
map.mywavewake.ru  →  <IP_вашего_VPS>
```

Подождать 5–15 минут. Проверка:

```bash
dig +short map.mywavewake.ru
```

---

## 1) Каталог и код SpotMap

Подставьте свой путь к репозиторию SpotMap (`REPO_URL`).

```bash
sudo mkdir -p /var/www/spotmap
sudo chown "$USER":"$USER" /var/www/spotmap
cd /var/www/spotmap
git clone REPO_URL .
# или: git pull, если уже склонирован
```

---

## 2) `.env` SpotMap (на сервере, не в Git)

```bash
cd /var/www/spotmap
cp .env.example .env   # если есть; иначе создайте файл
nano .env
```

Минимум в `.env`:

```bash
EMBED_ALLOWED_HOSTS=localhost,127.0.0.1,mywavewake.ru,www.mywavewake.ru
# ключ Яндекс.Карт и остальные секреты SpotMap — только здесь
```

---

## 3) Зависимости / PostGIS / запуск API

Повторите штатный prod-запуск из README SpotMap. Если локально карта слушает `18080`, на сервере тоже держите **127.0.0.1:18080**.

Пример systemd (имя сервиса/ExecStart поправьте под ваш стек):

```bash
sudo tee /etc/systemd/system/spotmap.service >/dev/null <<'EOF'
[Unit]
Description=SpotMap API
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/spotmap
EnvironmentFile=/var/www/spotmap/.env
ExecStart=/var/www/spotmap/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 18080
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now spotmap
sudo systemctl status spotmap --no-pager
curl -sI http://127.0.0.1:18080/embed?host=mywave | head
```

Если entrypoint другой — замените только строку `ExecStart=`.

---

## 4) Nginx + HTTPS для поддомена

С машины разработки (Windows, из корня Site_MyWave) можно залить конфиг, либо на сервере:

```bash
sudo cp /var/www/mywave/deploy/nginx/map.mywavewake.ru.conf /etc/nginx/sites-available/map.mywavewake.ru
# если deploy ещё не на сервере — создайте файл тем же содержимым из репозитория Site_MyWave

sudo ln -sf /etc/nginx/sites-available/map.mywavewake.ru /etc/nginx/sites-enabled/map.mywavewake.ru
sudo nginx -t
sudo systemctl reload nginx

# сертификат (после того как DNS уже указывает на VPS)
sudo certbot --nginx -d map.mywavewake.ru
sudo nginx -t && sudo systemctl reload nginx
```

Проверка с сервера:

```bash
curl -sI https://map.mywavewake.ru/embed?host=mywave | head
curl -s https://map.mywavewake.ru/embed?host=mywave | head -c 200
```

Ожидание: HTTP 200 и HTML embed (не 502).

---

## 5) Яндекс.Карты (кабинет, не shell)

В HTTP-рефереры добавить:

- `https://map.mywavewake.ru/*`
- при необходимости `https://mywavewake.ru/*`

---

## 6) Сайт MyWave (iframe уже в коде)

На сервере сайта:

```bash
cd /var/www/mywave
git pull
# при необходимости в /var/www/mywave/.env:
# SPOTMAP_EMBED_ENABLED=1
# SPOTMAP_EMBED_URL=https://map.mywavewake.ru/embed?host=mywave
# SPOTMAP_EMBED_ORIGIN=https://map.mywavewake.ru

sudo systemctl restart mywave-site
# или ваш unit: mywave / gunicorn

curl -s https://mywavewake.ru/projects | grep -o 'map.mywavewake.ru/embed[^"]*' | head
```

В браузере: `https://mywavewake.ru/projects` → блок SpotMap → DevTools без CSP `frame-src` violation.

---

## Rollback

```bash
# выключить iframe на сайте
sudo sed -i 's/^SPOTMAP_EMBED_ENABLED=.*/SPOTMAP_EMBED_ENABLED=0/' /var/www/mywave/.env
# если строки не было:
echo 'SPOTMAP_EMBED_ENABLED=0' | sudo tee -a /var/www/mywave/.env
sudo systemctl restart mywave-site

# остановить карту
sudo systemctl stop spotmap
sudo rm -f /etc/nginx/sites-enabled/map.mywavewake.ru
sudo nginx -t && sudo systemctl reload nginx
```
