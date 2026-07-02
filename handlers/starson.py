import asyncio
import random
import re
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, BufferedInputFile, FSInputFile, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.stars import generate_star_chart_svg

router = Router()

STARS_PRICE = 100
FREE_IDS = {453933675, 799895805, 902330773, 953575668, 1259760101, 428268964, 1206730610, 8674107250}
STANDARD_PHRASES = [
    "ПОД ЭТИМ ЗВЁЗДНЫМ НЕБОМ",
    "В ЭТОТ ДЕНЬ ЗВЁЗДЫ\nОСВЕТИЛИ ПУТЬ",
    "ТАМ, ГДЕ ЗАЖИГАЮТСЯ ЗВЁЗДЫ,\nРОЖДАЮТСЯ МЕЧТЫ",
    "САМЫЕ ВАЖНЫЕ МГНОВЕНИЯ\nПРОИСХОДЯТ ПОД ЗВЁЗДАМИ",
    "ВСЕЛЕННАЯ СЛЫШИТ\nКАЖДОЕ ТВОЁ ЖЕЛАНИЕ",
    "ПУСТЬ ЗВЁЗДЫ ОСВЕЩАЮТ\nТВОЙ ПУТЬ",
    "ЭТОТ МИГ НАВСЕГДА\nВ ЗВЁЗДНОЙ ПАМЯТИ",
    "ЗВЕЗДА ЗАЖГЛАСЬ\nВ ЧЕСТЬ ЭТОГО ДНЯ",
]

EXAMPLE_PATH = Path("assets") / "example_stars.png"

MONTHS_NOM = {
    "1": "январь", "2": "февраль", "3": "март", "4": "апрель",
    "5": "май", "6": "июнь", "7": "июль", "8": "август",
    "9": "сентябрь", "10": "октябрь", "11": "ноябрь", "12": "декабрь",
}
MONTHS_GEN = {
    "1": "января", "2": "февраля", "3": "марта", "4": "апреля",
    "5": "мая", "6": "июня", "7": "июля", "8": "августа",
    "9": "сентября", "10": "октября", "11": "ноября", "12": "декабря",
}
MONTH_ALIASES = {}
for k, nom in MONTHS_NOM.items():
    MONTH_ALIASES[nom] = k
for k, gen in MONTHS_GEN.items():
    MONTH_ALIASES[gen] = k
for k, nom in MONTHS_NOM.items():
    MONTH_ALIASES[nom[:3]] = k


KNOWN_CITIES = {
    "москва": (55.75, 37.62),
    "спб": (59.93, 30.31),
    "санкт-петербург": (59.93, 30.31),
    "сочи": (43.58, 39.72),
    "казань": (55.79, 49.10),
    "екатеринбург": (56.84, 60.65),
    "новосибирск": (55.01, 82.93),
    "краснодар": (45.04, 38.98),
    "ростов-на-дону": (47.23, 39.72),
    "самара": (53.20, 50.14),
    "минск": (53.90, 27.56),
    "киев": (50.45, 30.52),
    "алматы": (43.22, 76.85),
    "астана": (51.13, 71.43),
    "лондон": (51.51, -0.13),
    "париж": (48.86, 2.35),
    "берлин": (52.52, 13.40),
    "нью-йорк": (40.71, -74.01),
    "дубай": (25.20, 55.27),
    "токио": (35.68, 139.69),
}


class StarsForm(StatesGroup):
    waiting_payment = State()
    waiting_date = State()
    waiting_text = State()
    waiting_location = State()


# ─── public helper: show showcase (used by menu) ───

async def show_stars_showcase(message: Message, is_free: bool):
    """Send example image + description + order button."""
    b = InlineKeyboardBuilder()
    if is_free:
        b.button(text="🌟 Создать карту", callback_data="stars_order")
    else:
        b.button(text="🌟 Купить за 100⭐", callback_data="stars_order")
    b.button(text="📋 Меню", callback_data="menu_main")

    desc = (
        "🔭 <b>Звёздное небо на дату</b>\n\n"
        "Персонализированная карта звёздного неба:\n"
        "• Созвездия и планеты на твою дату\n"
        "• Твоя фраза внизу\n"
        "• Дата, время и место\n\n"
        "Стоимость: <b>100⭐</b>"
    )
    if is_free:
        desc += "\n\n🎁 Для тебя — бесплатно!"

    if EXAMPLE_PATH.exists():
        await message.answer_photo(
            FSInputFile(str(EXAMPLE_PATH)),
            caption=desc,
            reply_markup=b.as_markup(),
        )
    else:
        await message.answer(desc, reply_markup=b.as_markup())


# ─── callback: order button pressed ───

@router.callback_query(F.data == "stars_order")
async def stars_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    uid = callback.from_user.id

    if uid in FREE_IDS:
        await state.set_state(StarsForm.waiting_date)
        await callback.message.answer(
            "🎁 У тебя бесплатная генерация!\n\n"
            "Напиши <b>дату и время</b> в формате:\n"
            "<code>16.03.2018 05:00</code>\n\n"
            "Можно только дату — время будет 23:00."
        )
        return

    # Paying user — send invoice
    prices = [LabeledPrice(label="Звёздное небо", amount=STARS_PRICE)]
    await state.set_state(StarsForm.waiting_payment)
    await callback.message.answer_invoice(
        title="🔭 Звёздное небо",
        description="Персонализированная карта звёздного неба.",
        provider_token="",
        currency="XTR",
        prices=prices,
        payload=f"stars_custom_{uid}",
    )


@router.message(F.successful_payment, StarsForm.waiting_payment)
async def stars_paid(message: Message, state: FSMContext):
    await state.set_state(StarsForm.waiting_date)
    await message.answer(
        "✅ Оплачено!\n\n"
        "Теперь напиши <b>дату и время</b> в формате:\n"
        "<code>16.03.2018 05:00</code>\n\n"
        "Можно только дату — время будет 23:00."
    )


# ─── date input ───

@router.message(StarsForm.waiting_date)
async def stars_date_received(message: Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split()
    date_part = parts[0] if parts else ""
    time_part = parts[1] if len(parts) > 1 else "23:00"

    if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", date_part):
        await message.answer(
            "Неверный формат даты. Нужно: <b>ДД.ММ.ГГГГ</b>\n"
            "Пример: <code>16.03.2018 05:00</code>"
        )
        return
    if not re.match(r"^\d{2}:\d{2}$", time_part):
        await message.answer(
            "Неверный формат времени. Нужно: <b>ЧЧ:ММ</b>\n"
            "Пример: <code>16.03.2018 05:00</code>"
        )
        return

    await state.update_data(stars_date=date_part, stars_time=time_part)
    await state.set_state(StarsForm.waiting_text)
    await message.answer(
        "Отлично! Теперь напиши <b>текст</b>, который будет на карте.\n\n"
        "Фраза, строка из песни, признание — что угодно (макс. 140 символов).\n\n"
        "Или /skip — я выберу красивую фразу сама 🌟"
    )


# ─── text input ───

@router.message(StarsForm.waiting_text, Command("skip"))
async def stars_skip_text(message: Message, state: FSMContext):
    phrase = random.choice(STANDARD_PHRASES)
    await state.update_data(stars_caption=phrase)
    await _ask_location(message, state)


@router.message(StarsForm.waiting_text)
async def stars_caption_received(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Напиши текст или отправь /skip.")
        return
    if len(text) > 140:
        await message.answer("Слишком длинный текст (макс. 140 символов). Сократи немного.")
        return
    await state.update_data(stars_caption=text)
    await _ask_location(message, state)


# ─── location input ───

async def _ask_location(message: Message, state: FSMContext):
    await state.set_state(StarsForm.waiting_location)
    await message.answer(
        "Теперь укажи <b>город и страну</b>:\n"
        "<i>Сочи, Россия</i>\n\n"
        "Или /skip — будет Москва."
    )


@router.message(StarsForm.waiting_location, Command("skip"))
async def stars_skip_location(message: Message, state: FSMContext):
    await state.update_data(stars_location="Москва", stars_lat=55.75, stars_lon=37.62)
    await _do_generate(message, state)


@router.message(StarsForm.waiting_location)
async def stars_location_received(message: Message, state: FSMContext):
    raw = (message.text or "").strip()
    if not raw:
        await message.answer("Напиши город или отправь /skip.")
        return

    loc_lower = raw.lower()
    for key, (lat, lon) in KNOWN_CITIES.items():
        if key in loc_lower:
            await state.update_data(stars_location=raw, stars_lat=lat, stars_lon=lon)
            await _do_generate(message, state)
            return

    # Try geocoding
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="ZlataStarBot/1.0")
        geo = await asyncio.to_thread(geolocator.geocode, raw, timeout=5)
        if geo and geo.latitude and geo.longitude:
            await state.update_data(
                stars_location=geo.address,
                stars_lat=geo.latitude,
                stars_lon=geo.longitude,
            )
            await _do_generate(message, state)
            return
    except Exception:
        pass

    await message.answer(
        f"Не удалось найти «{raw}». Попробуй иначе, например:\n"
        "<i>Сочи, Россия</i>\n"
        "Или /skip для Москвы."
    )


# ─── generate ───

async def _do_generate(message: Message, state: FSMContext):
    data = await state.get_data()
    date_str = data.get("stars_date", "")
    time_str = data.get("stars_time", "23:00")
    caption = data.get("stars_caption", "")
    raw_location = data.get("stars_location", "Москва")
    lat = data.get("stars_lat", 55.75)
    lon = data.get("stars_lon", 37.62)
    await state.clear()

    if not date_str:
        await message.answer("❌ Ошибка: дата не найдена. Попробуй ещё раз.")
        return

    status = await message.answer("🔭 Строю звёздное небо...")
    try:
        svg = await asyncio.to_thread(
            generate_star_chart_svg, date_str, caption, time_str, raw_location, lat, lon
        )
        temp_svg = Path("data") / f"stars_{date_str.replace('.', '_')}.svg"
        temp_svg.write_text(svg, encoding="utf-8")

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 2381, "height": 3368})
            html = f'<html><body style="margin:0;background:#000005">{svg}</body></html>'
            await page.set_content(html)
            png_bytes = await page.screenshot(full_page=True)
            await browser.close()
    except Exception as e:
        await status.edit_text(f"❌ Ошибка при генерации: {e}")
        return

    await status.delete()

    b = InlineKeyboardBuilder()
    b.button(text="📋 Меню", callback_data="menu_main")

    await message.answer_photo(
        BufferedInputFile(png_bytes, filename="stars.png"),
        caption=f"🔭 <b>Звёздное небо — {date_str} {time_str}</b>",
        reply_markup=b.as_markup(),
    )


# ─── keep /stars_on command for direct access ───

@router.message(Command("stars_on"))
async def cmd_stars_on(message: Message, command: CommandObject, state: FSMContext):
    """Direct command — go straight to showcase."""
    await show_stars_showcase(message, message.chat.id in FREE_IDS)
