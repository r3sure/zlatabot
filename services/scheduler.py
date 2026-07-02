import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from services.ai import generate_text
from services.astrology import get_planets_summary, get_moon_info, ZODIAC_SIGNS_RU

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()

    def start(self):
        self.scheduler.add_job(self.morning_digest, "cron", hour=9, minute=0)
        # Channel auto-posting
        self.scheduler.add_job(self.channel_energy, "cron", hour=8, minute=0)
        self.scheduler.add_job(self.channel_horoscope_1, "cron", hour=10, minute=0)
        self.scheduler.add_job(self.channel_horoscope_2, "cron", hour=12, minute=0)
        self.scheduler.add_job(self.channel_horoscope_3, "cron", hour=14, minute=0)
        self.scheduler.add_job(self.channel_moon, "cron", hour=16, minute=0)
        self.scheduler.add_job(self.channel_horoscope_4, "cron", hour=18, minute=0)
        self.scheduler.add_job(self.rotate_signs, "cron", hour=0, minute=0)
        self.scheduler.add_job(self.sync_sheets, "cron", minute="*/5")
        self.scheduler.start()
        logger.info("Планировщик запущен (канал + рассылка + синхронизация)")

    async def stop(self):
        self.scheduler.shutdown(wait=False)

    def _all_users(self):
        from models.user import get_connection
        conn = get_connection()
        rows = conn.execute("SELECT user_id, zodiac_sign FROM users WHERE zodiac_sign IS NOT NULL").fetchall()
        conn.close()
        return rows

    async def morning_digest(self):
        users = await asyncio.to_thread(self._all_users)
        if not users:
            return

        planets = get_planets_summary()
        moon = get_moon_info()

        for row in users:
            user_id = row["user_id"]
            sign_ru = row["zodiac_sign"]

            sign_en = None
            for code, name in ZODIAC_SIGNS_RU.items():
                if name == sign_ru:
                    sign_en = code
                    break

            prompt = (
                f"Ты — астролог Злата. Напиши краткий гороскоп на сегодня "
                f"для знака {sign_ru} и один совет дня.\n"
                f"Планеты: {planets}\n"
                f"Луна: {moon['phase']} в знаке {moon['sign']}\n\n"
                f"Формат:\n"
                f"🔮 [гороскоп 2-3 предложения]\n"
                f"💫 [совет дня 1 предложение]\n\n"
                f"Без подписи, женский род."
            )

            try:
                text = await asyncio.to_thread(generate_text, prompt)
            except Exception:
                text = (
                    f"🔮 {sign_ru}, сегодня звёзды благосклонны к тебе.\n"
                    f"💫 Совет дня: доверься своей интуиции."
                )

            try:
                from aiogram.utils.keyboard import InlineKeyboardBuilder
                kb = InlineKeyboardBuilder()
                kb.button(text="🃏 Карта дня", callback_data="digest_card")
                kb.button(text="📋 Меню", callback_data="menu_main")
                await self.bot.send_message(
                    user_id,
                    f"☀️ <b>Доброе утро, {sign_ru}!</b>\n\n{text}\n\n{moon['emoji']} Сейчас Луна в знаке <b>{moon['sign']}</b> ({moon['phase']})",
                    reply_markup=kb.as_markup(),
                )
            except Exception as e:
                logger.warning("Ошибка отправки юзеру %s: %s", user_id, e)

            await asyncio.sleep(0.05)

    # ── Channel auto-posting ───────────────────────────────────

    _sign_batch = 0  # which 4 signs to post today (0, 1, 2)

    def _next_signs(self, count=4):
        from services.channel_poster import ALL_SIGNS
        offset = self._sign_batch * count
        signs = [ALL_SIGNS[(offset + i) % 12] for i in range(count)]
        return signs

    async def rotate_signs(self):
        self._sign_batch = (self._sign_batch + 1) % 3

    async def channel_energy(self):
        from services.channel_poster import post_energy_day
        try:
            await post_energy_day(self.bot)
        except Exception as e:
            logger.error("channel_energy: %s", e)

    async def channel_horoscope_1(self):
        from services.channel_poster import post_horoscope
        try:
            signs = self._next_signs(4)
            await post_horoscope(self.bot, signs[0])
        except Exception as e:
            logger.error("channel_horoscope_1: %s", e)

    async def channel_horoscope_2(self):
        from services.channel_poster import post_horoscope
        try:
            signs = self._next_signs(4)
            await post_horoscope(self.bot, signs[1])
        except Exception as e:
            logger.error("channel_horoscope_2: %s", e)

    async def channel_horoscope_3(self):
        from services.channel_poster import post_horoscope
        try:
            signs = self._next_signs(4)
            await post_horoscope(self.bot, signs[2])
        except Exception as e:
            logger.error("channel_horoscope_3: %s", e)

    async def channel_moon(self):
        from services.channel_poster import post_moon_day
        try:
            await post_moon_day(self.bot)
        except Exception as e:
            logger.error("channel_moon: %s", e)

    async def channel_horoscope_4(self):
        from services.channel_poster import post_horoscope
        try:
            signs = self._next_signs(4)
            await post_horoscope(self.bot, signs[3])
        except Exception as e:
            logger.error("channel_horoscope_4: %s", e)

    async def sync_sheets(self):
        from services.sheets import sync_all
        try:
            await asyncio.to_thread(sync_all)
        except Exception as e:
            logger.error("sync_sheets: %s", e)


