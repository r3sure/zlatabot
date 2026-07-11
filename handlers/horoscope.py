import asyncio
from datetime import date

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.ai import generate_text
from services.astrology import ZODIAC_SIGNS_RU, SIGN_GENITIVE, get_moon_info, get_planets_summary

router = Router()

_cache = {}

SIGN_LIST = list(ZODIAC_SIGNS_RU.items())


def _sign_kb():
    b = InlineKeyboardBuilder()
    for code, name in SIGN_LIST:
        b.button(text=name, callback_data=f"horo_{code}")
    b.adjust(3)
    b.button(text="↩️ Назад", callback_data="menu_to_astro")
    return b.as_markup()


def _cache_key():
    return str(date.today())


@router.message(Command("horoscope"))
async def cmd_horoscope(message: Message):
    await message.answer("Выбери свой знак зодиака:", reply_markup=_sign_kb())


@router.callback_query(F.data.startswith("horo_"))
async def show_horoscope(callback: CallbackQuery):
    import random
    sign_code = callback.data.split("_", 1)[1]
    sign_ru = ZODIAC_SIGNS_RU.get(sign_code, sign_code)

    today_key = _cache_key()
    cache_key = f"{today_key}_{sign_code}"

    if cache_key in _cache:
        text = _cache[cache_key]
        b = InlineKeyboardBuilder()
        b.button(text="↩️ Назад", callback_data="menu_to_astro")
        await callback.message.edit_text(
            f"🔮 <b>Гороскоп для {SIGN_GENITIVE.get(sign_ru, sign_ru)}</b>\n\n{text}",
            reply_markup=b.as_markup(),
        )
        await callback.answer()
        return

    status = await callback.message.edit_text(
        random.choice([
            "Смотрю, что шепчут звёзды... ✨",
            "Читаю небесную карту... 🌌",
            "Планеты выстраиваются в линию... 🌟",
            "Слушаю космическую тишину... 🔮",
        ])
    )

    moon = get_moon_info()
    planets = get_planets_summary()

    prompt = (
        f"Ты — эзотерический астролог Злата. Напиши гороскоп на сегодня "
        f"({date.today().strftime('%d.%m.%Y')}) для знака {SIGN_GENITIVE.get(sign_ru, sign_ru)}.\n"
        f"Астрологическая сводка на сегодня:\n"
        f"- Положение планет: {planets}\n"
        f"- Луна в знаке {moon['sign']}, фаза: {moon['phase']}\n\n"
        f"Напиши в женском роде, вдохновляюще, 3-4 предложения, "
        f"с обращением по знаку. Без подписи."
    )

    try:
        text = await generate_text(prompt)
    except Exception:
        text = (
            f"✨ {sign_ru}, сегодня ({date.today().strftime('%d.%m.%Y')}) "
            f"звёзды благосклонны к тебе!\n"
            f"Луна в фазе {moon['phase'].lower()}, "
            f"энергия планет направлена на гармонию. "
            f"Доверься своей интуиции."
        )

    _cache[cache_key] = text

    b = InlineKeyboardBuilder()
    b.button(text="↩️ Назад", callback_data="menu_to_astro")
    await status.edit_text(
        f"🔮 <b>Гороскоп для {SIGN_GENITIVE.get(sign_ru, sign_ru)}</b>\n\n{text}",
        reply_markup=b.as_markup(),
    )
    await callback.answer()
