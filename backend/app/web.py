import json
import logging
from datetime import date, datetime, timezone

from aiohttp import web
from sqlalchemy import select

from app.config import settings
from app.db import async_session
from app.models import CheckIn, User
from app.telegram_auth import TelegramAuthError, validate_init_data

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()

PRICE_MIN, PRICE_MAX = 100, 10000
DAYS_MIN, DAYS_MAX = 1, 60
PUFFS_MIN, PUFFS_MAX = 50, 3000


def _clamp(value, lo, hi) -> int:
    return max(lo, min(hi, int(value)))


def _to_ms(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    return int(dt.timestamp() * 1000)


def _from_ms(ms) -> datetime:
    return datetime.fromtimestamp(float(ms) / 1000, tz=timezone.utc)


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        resp = web.Response()
    else:
        resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Telegram-Init-Data, X-Debug-User-Id"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
    return resp


@web.middleware
async def auth_middleware(request: web.Request, handler):
    if request.path == "/api/health" or request.method == "OPTIONS":
        return await handler(request)

    tg_id = None
    auth_header = request.headers.get("Authorization", "")
    init_data = auth_header[4:] if auth_header.startswith("tma ") else request.headers.get("X-Telegram-Init-Data")

    if init_data:
        try:
            result = validate_init_data(init_data, settings.bot_token, settings.init_data_max_age)
        except TelegramAuthError as exc:
            return web.json_response({"error": str(exc)}, status=401)
        user = result.get("user") or {}
        tg_id = user.get("id")

    if tg_id is None and settings.dev_mode:
        debug_id = request.headers.get("X-Debug-User-Id")
        if debug_id:
            tg_id = int(debug_id)

    if tg_id is None:
        return web.json_response({"error": "unauthorized"}, status=401)

    request["tg_id"] = int(tg_id)
    return await handler(request)


async def _get_or_create_user(session, tg_id: int) -> User:
    user = await session.get(User, tg_id)
    if user is None:
        user = User(tg_id=tg_id)
        session.add(user)
        await session.flush()
    return user


async def _serialize_state(session, user: User) -> dict:
    result = await session.execute(select(CheckIn).where(CheckIn.user_id == user.tg_id))
    checkins = {c.date.isoformat(): c.mood for c in result.scalars()}
    return {
        "onboarded": user.onboarded,
        "quitDate": _to_ms(user.quit_date),
        "vapePrice": user.vape_price,
        "vapeDays": user.vape_days,
        "vapePuffs": user.vape_puffs,
        "checkins": checkins,
    }


async def _read_json(request: web.Request) -> dict:
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return {}
    return body if isinstance(body, dict) else {}


@routes.get("/api/health")
async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


@routes.get("/api/state")
async def get_state(request: web.Request) -> web.Response:
    tg_id = request["tg_id"]
    async with async_session() as session:
        user = await _get_or_create_user(session, tg_id)
        await session.commit()
        state = await _serialize_state(session, user)
    return web.json_response(state)


@routes.post("/api/onboard")
async def onboard(request: web.Request) -> web.Response:
    tg_id = request["tg_id"]
    body = await _read_json(request)

    quit_date_ms = body.get("quitDate")
    if not isinstance(quit_date_ms, (int, float)):
        return web.json_response({"error": "quitDate is required"}, status=400)

    async with async_session() as session:
        user = await _get_or_create_user(session, tg_id)
        user.onboarded = True
        user.quit_date = _from_ms(quit_date_ms)
        if "vapePrice" in body:
            user.vape_price = _clamp(body["vapePrice"], PRICE_MIN, PRICE_MAX)
        if "vapeDays" in body:
            user.vape_days = _clamp(body["vapeDays"], DAYS_MIN, DAYS_MAX)
        if "vapePuffs" in body:
            user.vape_puffs = _clamp(body["vapePuffs"], PUFFS_MIN, PUFFS_MAX)
        await session.commit()
        state = await _serialize_state(session, user)
    return web.json_response(state)


@routes.patch("/api/settings")
async def update_settings(request: web.Request) -> web.Response:
    tg_id = request["tg_id"]
    body = await _read_json(request)

    async with async_session() as session:
        user = await _get_or_create_user(session, tg_id)
        if "vapePrice" in body:
            user.vape_price = _clamp(body["vapePrice"], PRICE_MIN, PRICE_MAX)
        if "vapeDays" in body:
            user.vape_days = _clamp(body["vapeDays"], DAYS_MIN, DAYS_MAX)
        if "vapePuffs" in body:
            user.vape_puffs = _clamp(body["vapePuffs"], PUFFS_MIN, PUFFS_MAX)
        await session.commit()
        state = await _serialize_state(session, user)
    return web.json_response(state)


@routes.post("/api/checkin")
async def checkin(request: web.Request) -> web.Response:
    tg_id = request["tg_id"]
    body = await _read_json(request)

    date_str = body.get("date")
    mood = body.get("mood")
    if not isinstance(date_str, str) or not isinstance(mood, int) or not (1 <= mood <= 5):
        return web.json_response({"error": "date and mood(1-5) are required"}, status=400)

    try:
        checkin_date = date.fromisoformat(date_str)
    except ValueError:
        return web.json_response({"error": "invalid date"}, status=400)

    async with async_session() as session:
        user = await _get_or_create_user(session, tg_id)
        result = await session.execute(
            select(CheckIn).where(CheckIn.user_id == user.tg_id, CheckIn.date == checkin_date)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.mood = mood
        else:
            session.add(CheckIn(user_id=user.tg_id, date=checkin_date, mood=mood))
        await session.commit()
        state = await _serialize_state(session, user)
    return web.json_response(state)


@routes.post("/api/reset")
async def reset(request: web.Request) -> web.Response:
    tg_id = request["tg_id"]
    async with async_session() as session:
        user = await _get_or_create_user(session, tg_id)
        user.onboarded = False
        user.quit_date = None
        await session.execute(CheckIn.__table__.delete().where(CheckIn.user_id == user.tg_id))
        await session.commit()
        state = await _serialize_state(session, user)
    return web.json_response(state)


def create_app(bot) -> web.Application:
    app = web.Application(middlewares=[cors_middleware, auth_middleware])
    app.add_routes(routes)
    app["bot"] = bot
    return app
