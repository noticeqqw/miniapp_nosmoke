import asyncio
import logging

from aiohttp import web

from app.bot import create_bot_dispatcher
from app.config import settings
from app.db import init_models
from app.web import create_app

logger = logging.getLogger(__name__)


async def _set_menu_button(bot) -> None:
    from aiogram.types import MenuButtonWebApp, WebAppInfo

    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Открыть", web_app=WebAppInfo(url=settings.webapp_url))
        )
    except Exception:  # noqa: BLE001
        logger.warning("Could not set chat menu button", exc_info=True)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    await init_models()

    bot, dp = create_bot_dispatcher()
    await _set_menu_button(bot)

    app = create_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.port)
    await site.start()
    logger.info("API listening on 0.0.0.0:%s", settings.port)

    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
