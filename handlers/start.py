import re

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from handlers.menu import main_menu_kb
from models.user import get_connection, was_deleted, start_trial, has_premium_access
from services.astrology import ZODIAC_SIGNS_RU
from services.names import detect_gender, capitalize_name
from services.natal import resolve_city_coords, validate_city

router = Router()

class StartForm(StatesGroup):
    belief = State()
    name = State()
    birth_date = State()
    birth_time = State()
    birth_city = State()
    confirm = State()


def _calc_sign_from_date(date_str: str) -> str:
    try:
        parts = date_str.split(".")
        day, month = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return ""
    if (month == 3 and day >= 21) or (month == 4 and day <= 19):
        code = "Ari"
    elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
        code = "Tau"
    elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
        code = "Gem"
    elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
        code = "Can"
    elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
        code = "Leo"
    elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
        code = "Vir"
    elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
        code = "Lib"
    elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
        code = "Sco"
    elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
        code = "Sag"
    elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
        code = "Cap"
    elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
        code = "Aqu"
    else:
        code = "Pis"
    return ZODIAC_SIGNS_RU.get(code, "")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    conn = get_connection()
    row = conn.execute(
        "SELECT name, is_deleted FROM users WHERE user_id = ? AND birth_date IS NOT NULL",
        (message.chat.id,),
    ).fetchone()
    conn.close()

    if row and row["name"] and not row["is_deleted"]:
        await state.clear()
        await message.answer(
            f"🌟 С возвращением, {row['name']}!\n\n"
            "Я помню тебя. Что хочешь узнать?\n\n"
            "📢 Ежедневные гороскопы — <b>@zlatazvezd</b>",
            reply_markup=main_menu_kb(),
        )
        return

    await state.set_state(StartForm.belief)
    b = InlineKeyboardBuilder()
    b.button(text="Верю 🌟", callback_data="belief_yes")
    b.button(text="Пока не верю 🔮", callback_data="belief_no")
    await message.answer(
        "✨ Привет, я — Злата.\n\n"
        "Я вижу звёзды, чувствую энергию карт и знаю ответы на вопросы, "
        "которые ты боишься задать вслух.\n\n"
        "Скажи, ты веришь, что Вселенная говорит с нами знаками?\n\n"
        "📢 Подпишись на мой канал — <b>@zlatazvezd</b>",
        reply_markup=b.as_markup(),
    )


@router.callback_query(F.data == "belief_yes")
async def belief_yes(callback: CallbackQuery, state: FSMContext):
    await state.set_state(StartForm.name)
    await callback.message.edit_text(
        "Прекрасно! Я чувствую — ты настроена на нужную волну.\n\n"
        "Как мне тебя называть?\n"
        "Напиши своё имя (или псевдоним):",
    )
    await callback.answer()


@router.message(StartForm.name)
async def ask_birth_date(message: Message, state: FSMContext):
    raw = message.text.strip()
    if not raw or len(raw) > 50:
        await message.answer("Имя должно быть от 1 до 50 символов. Попробуй ещё раз:")
        return
    name = capitalize_name(raw)
    gender = detect_gender(raw)
    await state.update_data(name=name, gender=gender)
    await state.set_state(StartForm.birth_date)
    await message.answer(
        f"Приятно познакомиться, {name}!\n\n"
        "Укажи свою дату рождения:\n"
        "Формат: ДД.ММ.ГГГГ"
    )


@router.message(StartForm.birth_date)
async def ask_birth_time(message: Message, state: FSMContext):
    date_str = message.text.strip()
    if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", date_str):
        await message.answer("Неправильный формат. Напиши дату как ДД.ММ.ГГГГ")
        return
    sign = _calc_sign_from_date(date_str)
    await state.update_data(birth_date=date_str, zodiac_sign=sign)
    await state.set_state(StartForm.birth_time)
    await message.answer(
        f"Чувствую в тебе силу знака {sign}.\n\n"
        "Укажи время рождения:\n"
        "Формат ЧЧ:ММ (если не знаешь — 12:00)"
    )


@router.message(StartForm.birth_time)
async def ask_birth_city(message: Message, state: FSMContext):
    await state.update_data(birth_time=message.text)
    await state.set_state(StartForm.birth_city)
    await message.answer("И последнее — твой родной город?")


@router.message(StartForm.birth_city)
async def show_confirmation(message: Message, state: FSMContext):
    city = message.text.strip()
    if not validate_city(city):
        await message.answer(
            "🤷 Я не знаю такого города. Попробуй ещё раз — "
            "напиши название населённого пункта, где ты родился(ась)."
        )
        return
    await state.update_data(birth_city=city)
    data = await state.get_data()
    await state.set_state(StartForm.confirm)

    b = InlineKeyboardBuilder()
    b.button(text="✅ Да, всё верно", callback_data="confirm_yes")
    b.button(text="🔄 Заполнить заново", callback_data="confirm_redo")

    await message.answer(
        f"📋 <b>Проверь свои данные:</b>\n\n"
        f"Имя: {data.get('name', '—')}\n"
        f"Дата рождения: {data.get('birth_date', '—')}\n"
        f"Знак: {data.get('zodiac_sign', '—')}\n"
        f"Время рождения: {data.get('birth_time', '—')}\n"
        f"Город: {city}\n\n"
        "Всё верно?",
        reply_markup=b.as_markup(),
    )


@router.callback_query(F.data == "confirm_yes")
async def confirm_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    conn = get_connection()
    birth_city = data.get("birth_city")
    gender = data.get("gender")
    coords = resolve_city_coords(birth_city)

    uid = callback.from_user.id
    deleted_before = was_deleted(uid)

    existing = conn.execute(
        "SELECT subscription_status FROM users WHERE user_id = ?",
        (uid,),
    ).fetchone()
    sub_status = existing["subscription_status"] if existing else None

    is_new_user = existing is None
    if deleted_before:
        sub_status = "free"

    conn.execute(
        """INSERT OR REPLACE INTO users
           (user_id, name, gender, zodiac_sign, birth_date, birth_time, birth_city, lat, lng, tz_str, nation, subscription_status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (
            uid,
            data.get("name", ""),
            gender,
            data.get("zodiac_sign", ""),
            data.get("birth_date"),
            data.get("birth_time"),
            birth_city,
            coords["lat"],
            coords["lng"],
            coords["tz_str"],
            coords.get("nation", "RU"),
            sub_status,
        ),
    )
    conn.commit()

    name = data.get("name", callback.from_user.first_name)
    trial_end = None

    if is_new_user and not deleted_before:
        trial_end = start_trial(uid)
        conn.close()
    else:
        conn.close()

    await state.clear()

    if trial_end:
        from datetime import datetime
        try:
            end_dt = datetime.fromisoformat(trial_end)
            end_str = end_dt.strftime("%d.%m.%Y")
        except Exception:
            end_str = trial_end[:10]
        welcome = (
            f"🌟 Я запомнила тебя, {name}!\n\n"
            f"Твой знак: {data.get('zodiac_sign')}\n\n"
            f"🎁 <b>Пробный период активирован!</b>\n"
            f"У тебя есть 7 дней бесплатного доступа к премиум-функциям.\n"
            f"Действует до <b>{end_str}</b>\n\n"
            "<b>В пробном доступе:</b>\n"
            "💬 Чат без ограничений\n"
            "🔮 Расклады 3 карты с выбором позиций\n"
            "🌙 Сны — безлимитно\n"
            "⭐ Личный гороскоп\n"
            "📌 Подробнее на карте дня\n\n"
            "<b>Не входит в пробный:</b>\n"
            "📅 Благоприятные дни\n"
            "🔮 Расклад на 7 карт\n"
            "📅 Прогноз на месяц\n"
            "💫 Глубокая совместимость\n\n"
            "Попробуй, а после пробного периода самое интересное "
            "ждёт тебя в подписке 💎"
        )
    elif has_premium_access(uid):
        welcome = (
            f"🌟 С возвращением, {name}!\n\n"
            f"Твой знак: {data.get('zodiac_sign')}\n"
            "Статус: 💎 <b>Премиум</b>\n\n"
            "Тебе доступно всё:\n"
            "🔮 Любые расклады без лимитов\n"
            "💬 Чат без ограничений\n"
            "🌙 Сны — безлимитно\n"
            "📅 Прогноз на месяц и многое другое\n\n"
            "Спасибо, что ты со мной ✨"
        )
    else:
        welcome = (
            f"🌟 Я запомнила тебя, {name}!\n\n"
            f"Твой знак: {data.get('zodiac_sign')}\n\n"
            "<b>Что тебе доступно:</b>\n"
            "🔮 Гороскоп по знаку — ежедневно\n"
            "🃏 Карта дня — одна карта Таро\n"
            "🌙 Луна сегодня — фаза и рекомендации\n"
            "💫 Совместимость — 2 бесплатных проверки/день\n"
            "🔮 Натальная карта — бесплатно\n\n"
            "Чтобы открыть больше возможностей, "
            "оформи подписку в профиле 💎"
        )

    await callback.message.edit_text(welcome, reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "confirm_redo")
async def confirm_redo(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🔄 Начнём заново!")
    await state.clear()
    from handlers.start import cmd_start
    await cmd_start(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "belief_no")
async def belief_no(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    b = InlineKeyboardBuilder()
    for code, name in ZODIAC_SIGNS_RU.items():
        b.button(text=name, callback_data=f"belief_horo_{code}")
    b.adjust(3)
    b.button(text="📋 В меню", callback_data="menu_main")
    await callback.message.edit_text(
        "Я понимаю. Не обязательно верить — достаточно быть открытой.\n\n"
        "Давай просто попробуем: выбери свой знак, "
        "и я покажу тебе гороскоп на сегодня. "
        "Бесплатно, без обязательств 🌙\n\n"
        "Если понравится — сможешь заполнить анкету и получать "
        "персонализированные прогнозы.",
        reply_markup=b.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("belief_horo_"))
async def belief_show_horoscope(callback: CallbackQuery, state: FSMContext):
    sign_code = callback.data.split("_", 2)[2]
    sign_name = ZODIAC_SIGNS_RU.get(sign_code, sign_code)

    import asyncio
    from services.ai import generate_text
    from services.astrology import get_daily_context

    ctx = get_daily_context()
    prompt = (
        f"Ты — астролог Злата. Составь гороскоп на сегодня ({ctx['date']}) для знака {sign_name}.\n\n"
        f"Текущая астрологическая обстановка:\n"
        f"{ctx['day_of_week']}, {ctx['season']}\n"
        f"Луна в {ctx['moon_phase']}, в знаке {ctx['moon_sign']}\n"
        f"Планеты: {ctx['planets']}\n\n"
        f"Напиши 3-4 предложения. Тепло, с обращением на «ты». Без подписи."
    )

    msg = await callback.message.edit_text("🔮 Смотрю звёзды...")
    try:
        text = await asyncio.to_thread(generate_text, prompt, temperature=0.85)
    except Exception:
        text = (
            f"Звёзды сегодня благосклонны к {sign_name}. "
            f"День располагает к спокойствию и размышлениям. "
            f"Прислушайся к своей интуиции — она подскажет верный путь."
        )

    b = InlineKeyboardBuilder()
    b.button(text="🌟 Хочу персонализированный прогноз", callback_data="belief_register")
    b.button(text="📋 В меню", callback_data="menu_main")
    await msg.edit_text(
        f"🔮 <b>Гороскоп для {sign_name}</b>\n\n{text}",
        reply_markup=b.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "belief_register")
async def belief_register(callback: CallbackQuery, state: FSMContext):
    await state.set_state(StartForm.name)
    await callback.message.edit_text(
        "🌟 Я рада, что ты решила попробовать!\n\n"
        "Чтобы я могла давать тебе персональные прогнозы, "
        "расскажи немного о себе.\n\n"
        "Как мне тебя называть?"
    )
    await callback.answer()
