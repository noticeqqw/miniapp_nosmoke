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
   Для локальной разработки удобно прокинуть домен через ngrok/cloudflared на порт `8000`.
3. Поднимите стек:
   ```
   docker compose up -d --build
   ```
4. В BotFather пропишите этот же URL в настройках Menu Button / Mini App (или бот
   сам выставит кнопку меню при старте, `set_chat_menu_button`).
5. Откройте бота в Telegram и нажмите кнопку — приложение откроется и начнёт
   синхронизировать данные с PostgreSQL.

## Локальная отладка без Telegram

Установите `DEV_MODE=true` в `.env` — API начнёт принимать заголовок
`X-Debug-User-Id: <любое число>` вместо проверки `initData`. Не включайте это в проде.

## Разработка

- Бэкенд: `backend/app/` — `web.py` (REST), `bot.py` (aiogram), `models.py` (SQLAlchemy),
  `telegram_auth.py` (проверка подписи initData), `main.py` (точка входа).
- Таблицы создаются автоматически при старте (`Base.metadata.create_all`).
- Фронтенд синхронизирует поля `quitDate`, `vapePrice`, `vapeDays`, `vapePuffs`, `checkins`
  один в один с бэкендом — эти же имена используются в JSON-ответах API.
