import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import BotCommand

from config import TELEGRAM_BOT_TOKEN, PROXY
from models.user import init_db
from handlers.start import router as start_router
from handlers.horoscope import router as horoscope_router
from handlers.tarot import router as tarot_router
from handlers.moon import router as moon_router
from handlers.menu import router as menu_router
from handlers.compatibility import router as compat_router
from handlers.natal import router as natal_router
from handlers.profile import router as profile_router
from handlers.chat import router as chat_router
from handlers.dreams import router as dreams_router
from handlers.favorable import router as favorable_router
from handlers.personal import router as personal_router
from handlers.payment import router as payment_router
from handlers.admin import router as admin_router
from handlers.starson import router as starson_router
from handlers.matrix import router as matrix_router
from aiohttp import web
from config import YOOMONEY_SECRET
from services.scheduler import SchedulerService
from services.yoomoney import create_webhook_app

logging.basicConfig(level=logging.INFO)

dp = Dispatcher()
dp.include_router(start_router)
dp.include_router(horoscope_router)
dp.include_router(tarot_router)
dp.include_router(moon_router)
dp.include_router(menu_router)
dp.include_router(compat_router)
dp.include_router(natal_router)
dp.include_router(profile_router)
dp.include_router(dreams_router)
dp.include_router(favorable_router)
dp.include_router(personal_router)
dp.include_router(payment_router)
dp.include_router(admin_router)
dp.include_router(starson_router)
dp.include_router(matrix_router)
dp.include_router(chat_router)

scheduler: SchedulerService | None = None


async def main():
    init_db()

    session = AiohttpSession(proxy=PROXY) if PROXY else AiohttpSession()
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    global scheduler
    scheduler = SchedulerService(bot)
    scheduler.start()

    # Start YooMoney webhook server
    if YOOMONEY_SECRET:
        web_app = create_webhook_app()
        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8080)
        await site.start()
        logging.info("YooMoney webhook server started on :8080")

    me = await bot.get_me()
    await bot.set_my_commands([
        BotCommand(command="menu", description="🌟 Главное меню"),
        BotCommand(command="card", description="🃏 Карта дня"),
        BotCommand(command="spread", description="🔮 Расклад на 3 карты"),
        BotCommand(command="horoscope_personal", description="🌟 Личный гороскоп"),
        BotCommand(command="moon", description="🌙 Луна сегодня"),
        BotCommand(command="natal", description="🪐 Натальная карта"),
        BotCommand(command="compatibility", description="💫 Совместимость"),
        BotCommand(command="dream", description="🌙 Толкование сна"),
        BotCommand(command="chat", description="💬 Чат со Златой"),
        BotCommand(command="favorable", description="📅 Благоприятные дни"),
        BotCommand(command="monthly", description="📅 Прогноз на месяц"),
        BotCommand(command="deep_compat", description="💞 Глубокая совместимость"),
        BotCommand(command="profile", description="👤 Мой профиль"),
        BotCommand(command="buy", description="💎 Премиум"),
        BotCommand(command="stars_on", description="🔭 Звёздное небо на дату"),
    ])
    logging.info(f"Бот @{me.username} запущен")
    logging.info(f"Команды: python main.py (бот), python main.py --test-posts (тест постов)")

    # Если передан флаг --test-posts, запускаем тестовый прогон и завершаемся
    import sys
    if "--test-posts" in sys.argv:
        from services.channel_poster import test_all_posts
        await test_all_posts(bot)
        if scheduler:
            await scheduler.stop()
        await bot.session.close()
        logging.info("Тестовый прогон завершён, бот остановлен")
        return

    await dp.start_polling(bot)


async def shutdown():
    if scheduler:
        await scheduler.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        asyncio.run(shutdown())
