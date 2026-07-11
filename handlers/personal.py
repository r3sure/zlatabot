import asyncio

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.personal_astro import (
    generate_personal_horoscope,
    generate_monthly_forecast,
    generate_deep_compatibility,
    get_natal_data,
)
from services.natal import validate_city, resolve_city_coords
from models.user import is_premium, has_premium_access

router = Router()


class DeepCompatForm(StatesGroup):
    mode = State()
    p_name = State()
    p_birth = State()
    p_time = State()
    p_city = State()
    question = State()


# ── helpers ──

def _person_label(data: dict) -> str:
    """Human label for which person we're collecting."""
    step = data.get("step", "p1")
    mode = data.get("mode", "self")
    if mode == "self":
        return "партнёра"
    return "первого человека" if step == "p1" else "второго человека"


def _make_astral_subject(name: str, birth: str, time: str, city: str):
    """Build a kerykeion AstrologicalSubject; safe."""
    from services.personal_astro import parse_db_date
    from kerykeion import AstrologicalSubject
    day, month, year = parse_db_date(birth)
    hour, minute = map(int, time.split(":"))
    coords = resolve_city_coords(city)
    return AstrologicalSubject(
        name, year, month, day, hour, minute,
        lng=coords["lng"], lat=coords["lat"],
        tz_str=coords.get("tz_str", "Europe/Moscow"),
        online=False,
    )


async def _ask_name(message: Message, state: FSMContext):
    data = await state.get_data()
    label = _person_label(data)
    await state.set_state(DeepCompatForm.p_name)
    await message.answer(
        f"💫 <b>Глубокая совместимость</b>\n\n"
        f"Как зовут {label}?"
    )


async def _ask_birth(message: Message, state: FSMContext):
    await state.set_state(DeepCompatForm.p_birth)
    await message.answer(
        "Введи дату рождения в формате <b>ДД.ММ.ГГГГ</b>\n"
        "Например: <code>15.03.1992</code>"
    )


async def _ask_time(message: Message, state: FSMContext):
    b = InlineKeyboardBuilder()
    b.button(text="12:00 (не знаю)", callback_data="deep_time_skip")
    b.button(text="Введу время", callback_data="deep_time_enter")
    await state.set_state(DeepCompatForm.p_time)
    await message.answer(
        "Знаешь время рождения? Мне хватит примерно.\n"
        "Если не знаешь — поставлю полдень.",
        reply_markup=b.as_markup(),
    )


async def _ask_city(message: Message, state: FSMContext):
    await state.set_state(DeepCompatForm.p_city)
    await message.answer(
        "Какой город рождения?\n"
        "Или /skip — будет Москва."
    )


async def _ask_question(message: Message, state: FSMContext):
    await state.set_state(DeepCompatForm.question)
    await message.answer(
        "Напиши <b>ситуацию или вопрос</b>, который хочешь прояснить "
        "в контексте этих отношений.\n\n"
        "Или /skip — я расскажу общую совместимость."
    )


# ── entrance ──

@router.message(Command("horoscope_personal"))
async def cmd_personal_horoscope(message: Message):
    user_id = message.chat.id
    if not has_premium_access(user_id):
        data = get_natal_data(user_id)
        if not data:
            b = InlineKeyboardBuilder()
            b.button(text="👤 Заполнить профиль", callback_data="menu_profile")
            b.button(text="📋 Меню", callback_data="menu_main")
            await message.answer(
                "🔮 <b>Личный гороскоп</b>\n\n"
                "Гороскоп, основанный на твоей натальной карте, — "
                "доступен подписчикам 💎\n\n"
                "А пока заполни профиль, и ты сможешь получать "
                "персонализированные прогнозы!",
                reply_markup=b.as_markup(),
            )
            return
        b = InlineKeyboardBuilder()
        b.button(text="💎 Оформить подписку", callback_data="menu_profile")
        b.button(text="📋 Меню", callback_data="menu_main")
        await message.answer(
            "🔮 <b>Личный гороскоп</b>\n\n"
            "Гороскоп, основанный на твоей натальной карте и текущих транзитах. "
            "Доступен подписчикам 💎\n\n"
            "Оформи подписку, чтобы получать прогнозы, "
            "созданные лично для тебя ✨",
            reply_markup=b.as_markup(),
        )
        return

    msg = await message.answer("🔮 Составляю личный гороскоп...")
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(2)

    text = await generate_personal_horoscope(user_id)
    await msg.delete()

    b = InlineKeyboardBuilder()
    b.button(text="📅 На месяц", callback_data="menu_monthly")
    b.button(text="📋 Меню", callback_data="menu_main")
    await message.answer(
        f"🔮 <b>Личный гороскоп на сегодня</b>\n\n{text}",
        reply_markup=b.as_markup(),
    )


@router.message(Command("monthly"))
async def cmd_monthly(message: Message):
    user_id = message.chat.id
    if not has_premium_access(user_id):
        b = InlineKeyboardBuilder()
        b.button(text="💎 Оформить подписку", callback_data="menu_profile")
        b.button(text="📋 Меню", callback_data="menu_main")
        await message.answer(
            "📅 <b>Прогноз на месяц</b>\n\n"
            "Астрологический прогноз на месяц, основанный на твоей натальной карте "
            "и планетарных транзитах. Доступен подписчикам 💎\n\n"
            "Узнай, какие сферы жизни будут особенно активны, "
            "когда начинать важные дела и в какие дни лучше отдыхать ✨",
            reply_markup=b.as_markup(),
        )
        return

    msg = await message.answer("📅 Составляю прогноз на месяц...")
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(2)

    text = await generate_monthly_forecast(user_id)
    await msg.delete()

    b = InlineKeyboardBuilder()
    b.button(text="🔮 На сегодня", callback_data="menu_personal_horo")
    b.button(text="📋 Меню", callback_data="menu_main")
    await message.answer(
        f"📅 <b>Прогноз на месяц</b>\n\n{text}",
        reply_markup=b.as_markup(),
    )


# ── deep compat: mode selection ──

@router.message(Command("deep_compat"))
async def cmd_deep_compat(message: Message, state: FSMContext):
    user_id = message.chat.id
    if not has_premium_access(user_id):
        b = InlineKeyboardBuilder()
        b.button(text="💎 Оформить подписку", callback_data="menu_profile")
        b.button(text="📋 Меню", callback_data="menu_main")
        await message.answer(
            "💫 <b>Глубокая совместимость</b>\n\n"
            "Синастрический анализ на основе натальных карт обоих партнёров:\n"
            "— Планетные аспекты между вашими картами\n"
            "— Эмоциональная, интеллектуальная и физическая совместимость\n"
            "— Сильные стороны и зоны роста\n\n"
            "Доступно подписчикам 💎",
            reply_markup=b.as_markup(),
        )
        return

    await state.set_state(DeepCompatForm.mode)
    b = InlineKeyboardBuilder()
    b.button(text="👤 С собой", callback_data="deep_mode_self")
    b.button(text="👥 С другим человеком", callback_data="deep_mode_other")
    await message.answer(
        "💫 <b>Глубокая совместимость</b>\n\n"
        "С кем сравниваем?",
        reply_markup=b.as_markup(),
    )


@router.callback_query(F.data.startswith("deep_mode_"), DeepCompatForm.mode)
async def deep_mode_chosen(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    mode = callback.data.split("_")[-1]  # "self" or "other"

    if mode == "self":
        # Check user has profile
        data = get_natal_data(callback.from_user.id)
        if not data:
            b = InlineKeyboardBuilder()
            b.button(text="👤 Заполнить профиль", callback_data="menu_profile")
            b.button(text="📋 Меню", callback_data="menu_main")
            await callback.message.edit_text(
                "💫 <b>Глубокая совместимость</b>\n\n"
                "Чтобы сравнить с собой, нужна твоя натальная карта. "
                "Заполни дату рождения в профиле!",
                reply_markup=b.as_markup(),
            )
            return
        await state.update_data(mode="self", step="partner")
        await _ask_name(callback.message, state)
    else:
        await state.update_data(mode="other", step="p1")
        await _ask_name(callback.message, state)


# ── deep compat: name ──

@router.message(DeepCompatForm.p_name)
async def deep_name(message: Message, state: FSMContext):
    data = await state.get_data()
    step = data.get("step", "p1")
    prefix = "p1" if step == "p1" else ("p2" if step == "p2" else "partner")
    await state.update_data({f"{prefix}_name": message.text.strip()})
    await _ask_birth(message, state)


# ── deep compat: birth date ──

@router.message(DeepCompatForm.p_birth)
async def deep_birth(message: Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        await message.answer("Неверный формат. Напиши как <code>15.03.1992</code>")
        return
    d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
    if not (1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= 2100):
        await message.answer("Дата выглядит нереальной. Попробуй ещё раз.")
        return
    data = await state.get_data()
    step = data.get("step", "p1")
    prefix = "p1" if step == "p1" else ("p2" if step == "p2" else "partner")
    await state.update_data({f"{prefix}_birth": text})
    await _ask_time(message, state)


# ── deep compat: birth time ──

@router.callback_query(F.data == "deep_time_skip", DeepCompatForm.p_time)
async def deep_time_skip(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    step = data.get("step", "p1")
    prefix = "p1" if step == "p1" else ("p2" if step == "p2" else "partner")
    await state.update_data({f"{prefix}_time": "12:00"})
    await _ask_city(callback.message, state)


@router.callback_query(F.data == "deep_time_enter", DeepCompatForm.p_time)
async def deep_time_ask(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "Напиши время в формате <b>ЧЧ:ММ</b>\nНапример: <code>14:30</code>"
    )


@router.message(DeepCompatForm.p_time)
async def deep_time(message: Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split(":")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await message.answer("Неверный формат. Напиши как <code>14:30</code>")
        return
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        await message.answer("Неверный формат. Часы 0-23, минуты 0-59.")
        return
    data = await state.get_data()
    step = data.get("step", "p1")
    prefix = "p1" if step == "p1" else ("p2" if step == "p2" else "partner")
    await state.update_data({f"{prefix}_time": text})
    await _ask_city(message, state)


# ── deep compat: city ──

@router.message(DeepCompatForm.p_city, Command("skip"))
async def deep_city_skip(message: Message, state: FSMContext):
    data = await state.get_data()
    step = data.get("step", "p1")
    prefix = "p1" if step == "p1" else ("p2" if step == "p2" else "partner")
    await state.update_data({f"{prefix}_city": "Москва"})
    await _after_city(message, state)


@router.message(DeepCompatForm.p_city)
async def deep_city(message: Message, state: FSMContext):
    raw = message.text.strip()
    if not raw:
        await message.answer("Напиши город или /skip.")
        return
    if not validate_city(raw):
        await message.answer("Не узнаю город. Попробуй иначе или /skip.")
        return
    data = await state.get_data()
    step = data.get("step", "p1")
    prefix = "p1" if step == "p1" else ("p2" if step == "p2" else "partner")
    await state.update_data({f"{prefix}_city": raw})
    await _after_city(message, state)


async def _after_city(message: Message, state: FSMContext):
    data = await state.get_data()
    mode = data.get("mode", "self")
    step = data.get("step", "p1")

    if mode == "other" and step == "p1":
        # Move to p2
        await state.update_data(step="p2")
        await _ask_name(message, state)
    else:
        # Done collecting people → ask question
        await _ask_question(message, state)


# ── deep compat: question ──

@router.message(DeepCompatForm.question, Command("skip"))
async def deep_question_skip(message: Message, state: FSMContext):
    await state.update_data(question="")
    await _run_deep_compat(message, state)


@router.message(DeepCompatForm.question)
async def deep_question(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("Напиши вопрос или /skip.")
        return
    await state.update_data(question=text)
    await _run_deep_compat(message, state)


# ── run deep compat ──

async def _run_deep_compat(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    mode = data.get("mode", "self")

    if mode == "self":
        p1_data = None  # will be fetched from DB
        p2_data = {
            "name": data["partner_name"],
            "birth": data["partner_birth"],
            "time": data.get("partner_time", "12:00"),
            "city": data.get("partner_city", "Москва"),
        }
    else:
        p1_data = {
            "name": data["p1_name"],
            "birth": data["p1_birth"],
            "time": data.get("p1_time", "12:00"),
            "city": data.get("p1_city", "Москва"),
        }
        p2_data = {
            "name": data["p2_name"],
            "birth": data["p2_birth"],
            "time": data.get("p2_time", "12:00"),
            "city": data.get("p2_city", "Москва"),
        }

    question = data.get("question", "")

    msg = await message.answer(
        f"💫 Рассчитываю синастрию <b>{p2_data['name']}</b>..."
    )
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(2)

    text = await generate_deep_compatibility(
        message.chat.id, p1_data, p2_data, question=question,
    )
    await msg.delete()

    # Build result header
    if mode == "self":
        header = f"С кем: {p2_data['name']} ({p2_data['birth']})"
    else:
        header = f"{p1_data['name']} и {p2_data['name']}"

    b = InlineKeyboardBuilder()
    b.button(text="📋 Меню", callback_data="menu_main")
    await message.answer(
        f"💫 <b>Глубокая совместимость</b>\n\n{header}\n\n{text}",
        reply_markup=b.as_markup(),
    )


# ── Хочу глубже from simple compat ──

@router.callback_query(F.data == "deep_from_compat")
async def deep_from_compat(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    if not has_premium_access(user_id):
        b = InlineKeyboardBuilder()
        b.button(text="💎 Оформить подписку", callback_data="menu_profile")
        b.button(text="📋 Меню", callback_data="menu_main")
        await callback.message.answer(
            "💫 <b>Глубокая совместимость</b> — для подписчиков 💎",
            reply_markup=b.as_markup(),
        )
        return

    # Open mode selection (no profile check — user can pick "other")
    await state.set_state(DeepCompatForm.mode)
    b = InlineKeyboardBuilder()
    b.button(text="👤 С собой", callback_data="deep_mode_self")
    b.button(text="👥 С другим человеком", callback_data="deep_mode_other")
    await callback.message.answer(
        "💫 <b>Глубокая совместимость</b>\n\n"
        "С кем сравниваем?",
        reply_markup=b.as_markup(),
    )


# ── menu callbacks ──

@router.callback_query(F.data == "menu_personal_horo")
async def menu_to_personal_horo(callback: CallbackQuery):
    await callback.answer()
    await cmd_personal_horoscope(callback.message)


@router.callback_query(F.data == "menu_monthly")
async def menu_to_monthly(callback: CallbackQuery):
    await callback.answer()
    await cmd_monthly(callback.message)


@router.callback_query(F.data == "menu_deep_compat")
async def menu_to_deep_compat(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await cmd_deep_compat(callback.message, state)
