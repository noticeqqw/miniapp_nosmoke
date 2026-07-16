from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from app.config import settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Открыть трекер", web_app=WebAppInfo(url=settings.webapp_url))]]
    )
    await message.answer(
        "Привет! Это трекер отказа от вейпа/сигарет.\n\n"
        "Он показывает, сколько времени прошло с момента отказа, "
        "сколько денег и затяжек ты уже сэкономил, и помогает вести ежедневные отметки самочувствия.\n\n"
        "Нажми кнопку ниже, чтобы открыть приложение.",
        reply_markup=keyboard,
    )


def create_bot_dispatcher() -> tuple[Bot, Dispatcher]:
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    return bot, dp
