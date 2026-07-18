# Не парю / Не курю — Telegram Mini App

Трекер времени без вейпа/сигарет: показывает, сколько времени прошло с момента отказа,
сколько денег и затяжек сэкономлено, ведёт ежедневные отметки самочувствия.

## Структура

```
frontend/        статический Mini App (HTML + React через CDN), отдаётся nginx
backend/          Python-бэкенд: aiogram-бот + aiohttp REST API + SQLAlchemy/PostgreSQL
nginx/            конфиг реверс-прокси (раздаёт frontend/, проксирует /api/ на backend)
docker-compose.yml
```

## Как это работает

- `frontend/index.html` — Mini App. При открытии внутри Telegram она инициализирует
  `Telegram.WebApp`, забирает `initData` и синхронизирует состояние (дату отказа,
  настройки, чек-ины) с бэкендом через `/api/*`. localStorage используется как
  мгновенный кэш/офлайн-фоллбек — если бэкенд недоступен, приложение продолжает
  работать локально.
- `backend` — один Python-процесс, в котором одновременно крутятся:
  - aiogram-бот (`/start` присылает кнопку с Mini App, плюс кнопка меню чата);
  - aiohttp REST API (`/api/state`, `/api/onboard`, `/api/settings`, `/api/checkin`, `/api/reset`).
  - Авторизация запросов — через проверку подписи `Telegram.WebApp.initData`
    (заголовок `Authorization: tma <initData>`), без паролей/токенов на клиенте.
- PostgreSQL хранит пользователей (`users`) и ежедневные отметки (`checkins`).

## Запуск

1. Создайте бота через [@BotFather](https://t.me/BotFather), получите токен.
2. Скопируйте `.env.example` в `.env` и заполните:
   ```
   BOT_TOKEN=<токен от BotFather>
   WEBAPP_URL=https://<ваш-публичный-https-домен>
   ```
   `WEBAPP_URL` обязательно должен быть **https** — Telegram не откроет Mini App по http.
   Для локальной разработки удобно прокинуть домен через ngrok/cloudflared на порт `HTTP_PORT`
   (по умолчанию `8010`, см. `.env.example`).
3. Поднимите стек:
   ```
   docker compose up -d --build
   ```
4. В BotFather пропишите этот же URL в настройках Menu Button / Mini App (или бот
   сам выставит кнопку меню при старте, `set_chat_menu_button`).
5. Откройте бота в Telegram и нажмите кнопку — приложение откроется и начнёт
   синхронизировать данные с PostgreSQL.

## Деплой на сервер, где уже крутится несколько ботов/доменов

Контейнерный `nginx` этого проекта **не занимает 80/443** — он слушает только
`127.0.0.1:${HTTP_PORT}` (по умолчанию `8010`). Наружу домен отдаёт уже существующий
на сервере системный nginx, как и остальные сайты/боты. Ничего в чужих стеках
трогать не нужно.

1. **Скопируйте проект на сервер**, например в `/opt/nosmoke_tg_miniapp`, и зайдите в папку.
2. **Проверьте, что порт свободен** (чтобы не столкнуться с другим проектом):
   ```
   ss -ltn | grep 8010
   ```
   Если занят — возьмите другой (например 8011) и укажите его в `.env` как `HTTP_PORT`.
3. **Заполните `.env`** (`cp .env.example .env`): `BOT_TOKEN`, `WEBAPP_URL=https://<новый домен>`,
   `HTTP_PORT`. `POSTGRES_*` можно оставить как есть — это изолированная БД только для
   этого проекта, наружу не смотрит (в `docker-compose.yml` у `db` нет `ports:`, только
   внутренняя docker-сеть), так что с другими Postgres на сервере не конфликтует.
4. **DNS**: на третьем домене создайте A/AAAA-запись на IP сервера (поддомен, как вы и
   планировали, например `nosmoke.ваш-домен.ру`).
5. **Добавьте vhost в системный nginx** — используйте
   [`deploy/nginx-vhost.example.conf`](deploy/nginx-vhost.example.conf) как шаблон:
   скопируйте в `/etc/nginx/sites-available/`, замените `server_name` и порт (`8010`)
   на свои, включите так же, как остальные сайты (`sites-enabled` симлинк или ваш
   принятый способ), `nginx -t && systemctl reload nginx`.
6. **Получите сертификат** тем же способом, что и для остальных доменов на сервере
   (обычно `certbot --nginx -d nosmoke.ваш-домен.ру`).
7. **Поднимите стек** (у compose-проекта фиксированное имя `nosmoke-tg-miniapp` в
   `docker-compose.yml`, поэтому имена контейнеров/сети не пересекутся с другими стеками):
   ```
   docker compose up -d --build
   ```
8. Проверьте `curl -I https://nosmoke.ваш-домен.ру/api/health` и откройте бота в Telegram.

aiogram-бот работает через polling (long polling к Telegram API) — это отдельное
исходящее соединение по токену конкретного бота, оно никак не пересекается с
другими ботами на том же сервере, даже если они тоже на polling.

## Локальная отладка без Telegram

Установите `DEV_MODE=true` в `.env` — API начнёт принимать заголовок
`X-Debug-User-Id: <любое число>` вместо проверки `initData`. Не включайте это в проде.

## Разработка

- Бэкенд: `backend/app/` — `web.py` (REST), `bot.py` (aiogram), `models.py` (SQLAlchemy),
  `telegram_auth.py` (проверка подписи initData), `main.py` (точка входа).
- Таблицы создаются автоматически при старте (`Base.metadata.create_all`).
- Фронтенд синхронизирует поля `quitDate`, `vapePrice`, `vapeDays`, `vapePuffs`, `checkins`
  один в один с бэкендом — эти же имена используются в JSON-ответах API.
