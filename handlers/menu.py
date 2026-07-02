from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.astrology import ZODIAC_SIGNS_RU

router = Router()


def main_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="🔮 Таро", callback_data="menu_to_taro")
    b.button(text="🌙 Толкование снов", callback_data="menu_dream")
    b.button(text="⭐ Астрология", callback_data="menu_to_astro")
    b.button(text="💬 Чат со Златой", callback_data="menu_chat")
    b.button(text="✳️ Матрица Судьбы", callback_data="menu_matrix")
    b.button(text="💎 Премиум", callback_data="menu_buy")
    b.button(text="👤 Мой профиль", callback_data="menu_profile")
    b.adjust(1)
    return b.as_markup()


def taro_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="🃏 Карта дня", callback_data="menu_card")
    b.button(text="🎴 Расклад на 3 карты", callback_data="menu_spread_type")
    b.button(text="🔯 Расклад на 7 карт", callback_data="menu_spread_7")
    b.button(text="✳️ Матрица Судьбы", callback_data="menu_matrix")
    b.button(text="↩️ Назад", callback_data="menu_main")
    b.adjust(1)
    return b.as_markup()


def astro_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="♈ Гороскоп", callback_data="menu_horoscope")
    b.button(text="🌝 Луна сегодня", callback_data="menu_moon")
    b.button(text="🟢 Благоприятные дни", callback_data="menu_favorable")
    b.button(text="🪐 Натальная карта", callback_data="menu_natal")
    b.button(text="💫 Совместимость", callback_data="menu_compat")
    b.button(text="🌟 Личный гороскоп", callback_data="menu_personal_horo")
    b.button(text="📅 Прогноз на месяц", callback_data="menu_monthly")
    b.button(text="💞 Глубокая совместимость", callback_data="menu_deep_compat")
    b.button(text="🔭 Звёздное небо", callback_data="menu_to_stars")
    b.button(text="↩️ Назад", callback_data="menu_main")
    b.adjust(1)
    return b.as_markup()


def spread_type_kb():
    b = InlineKeyboardBuilder()
    b.button(text="🌅 На сегодня", callback_data="menu_spread_today")
    b.button(text="🌄 На завтра", callback_data="menu_spread_tomorrow")
    b.button(text="🎯 Под ситуацию", callback_data="menu_spread_situation")
    b.button(text="↩️ Назад", callback_data="menu_to_taro")
    b.adjust(1)
    return b.as_markup()





def _sign_select_kb():
    b = InlineKeyboardBuilder()
    for code, name in ZODIAC_SIGNS_RU.items():
        b.button(text=name, callback_data=f"horo_{code}")
    b.adjust(3)
    b.button(text="↩️ Назад", callback_data="menu_to_astro")
    return b.as_markup()


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer(
        "🌟 <b>Злата</b> — выбери, что тебе нужно:",
        reply_markup=main_menu_kb(),
    )


async def _nav(callback: CallbackQuery, text: str, kb):
    """Delete old message and send new one."""
    try:
        await callback.answer()
    except Exception:
        pass
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(text, reply_markup=kb)


async def _go(callback: CallbackQuery):
    """Delete menu message before executing action."""
    await callback.answer()
    await callback.message.delete()


async def _build_menu_message(user_id: int) -> str:
    from models.user import is_premium, is_trial, get_connection
    conn = get_connection()
    row = conn.execute(
        "SELECT name, birth_date, subscription_status, subscription_end FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()

    if is_premium(user_id):
        end_str = row["subscription_end"][:10] if row and row["subscription_end"] else "—"
        return (
            "🌟 <b>Злата</b> — выбери, что тебе нужно:\n\n"
            f"💎 Премиум активен до <b>{end_str}</b>\n\n"
            "📢 Больше астрологии — <b>@zlatazvezd</b>"
        )
    elif is_trial(user_id):
        end_str = row["subscription_end"][:10] if row and row["subscription_end"] else "—"
        return (
            "🌟 <b>Злата</b> — выбери, что тебе нужно:\n\n"
            f"🎁 Пробный период до <b>{end_str}</b>\n"
            "Все функции открыты, пробуй ✨\n\n"
            "📢 Больше астрологии — <b>@zlatazvezd</b>"
        )
    elif row and row["birth_date"]:
        return (
            "🌟 <b>Злата</b> — выбери, что тебе нужно:\n\n"
            "🎁 <b>Пробный период 3 дня</b> — все функции бесплатно!\n"
            "Оформи подписку в профиле 💎\n\n"
            "📢 Больше астрологии — <b>@zlatazvezd</b>"
        )
    else:
        return (
            "🌟 <b>Злата</b> — выбери, что тебе нужно:\n\n"
            "📢 Зарегистрируйся в профиле, чтобы открыть все возможности 👤\n\n"
            "📢 Больше астрологии — <b>@zlatazvezd</b>"
        )


@router.callback_query(F.data == "menu_main")
async def menu_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    msg = await _build_menu_message(callback.from_user.id)
    await callback.message.answer(msg, reply_markup=main_menu_kb())
    await state.clear()


@router.callback_query(F.data == "menu_to_taro")
async def menu_to_taro(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "🔮 <b>Таро</b> — выбери расклад:",
        reply_markup=taro_menu_kb(),
    )


@router.callback_query(F.data == "menu_to_astro")
async def menu_to_astro(callback: CallbackQuery):
    await _nav(callback, "⭐ <b>Астрология</b> — выбери раздел:", astro_menu_kb())


@router.callback_query(F.data == "menu_to_stars")
async def menu_to_stars(callback: CallbackQuery):
    await _go(callback)
    from handlers.starson import show_stars_showcase
    uid = callback.from_user.id
    from handlers.starson import FREE_IDS
    await show_stars_showcase(callback.message, uid in FREE_IDS)


@router.callback_query(F.data == "menu_spread_type")
async def menu_spread_type(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(prev_menu_message=callback.message.message_id)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "🔮 <b>Расклад на 3 карты</b>\n\nКакой расклад тебе нужен?",
        reply_markup=spread_type_kb(),
    )


@router.callback_query(F.data == "menu_spread_today")
async def menu_spread_today(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
    from handlers.tarot import cmd_spread_day
    await cmd_spread_day(callback.message, state=state, day_offset=0)


@router.callback_query(F.data == "menu_spread_tomorrow")
async def menu_spread_tomorrow(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
    from handlers.tarot import cmd_spread_day
    await cmd_spread_day(callback.message, state=state, day_offset=1)

@router.callback_query(F.data == "menu_spread_situation")
async def menu_spread_situation(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    from handlers.tarot import TarotForm
    await state.set_state(TarotForm.waiting_situation_3)
    b = InlineKeyboardBuilder()
    b.button(text="↩️ Назад", callback_data="spread_situation_back")
    await callback.message.answer(
        "🔮 <b>Расклад на 3 карты под ситуацию</b>\n\n"
        "Опиши свою ситуацию подробно — "
        "и я вытяну карты, которые помогут разобраться 🌟",
        reply_markup=b.as_markup(),
    )


@router.callback_query(F.data == "spread_situation_back")
async def spread_situation_back(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "🌟 <b>Злата</b> — выбери, что тебе нужно:",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "digest_card")
async def digest_card(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    from handlers.tarot import cmd_card_day
    await cmd_card_day(callback.message)


@router.callback_query(F.data == "menu_spread_7")
async def menu_spread_7_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    from handlers.tarot import TarotForm
    await state.set_state(TarotForm.waiting_situation_7)
    await callback.message.answer(
        "🔮 <b>Расклад на 7 карт</b>\n\n"
        "Это глубокий разбор ситуации. Опиши подробно, "
        "что происходит в твоей жизни — карты расскажут всю историю 🌟",
        reply_markup=InlineKeyboardBuilder()
        .button(text="📋 Меню", callback_data="menu_main")
        .as_markup(),
    )


@router.callback_query(F.data == "menu_horoscope")
async def menu_to_horoscope(callback: CallbackQuery):
    await _nav(callback, "Выбери свой знак:", _sign_select_kb())


@router.callback_query(F.data == "menu_card")
async def menu_to_card(callback: CallbackQuery):
    await _go(callback)
    from handlers.tarot import cmd_card_day
    await cmd_card_day(callback.message)


@router.callback_query(F.data == "menu_moon")
async def menu_to_moon(callback: CallbackQuery):
    await _go(callback)
    from handlers.moon import cmd_moon
    await cmd_moon(callback.message)


@router.callback_query(F.data == "menu_natal")
async def menu_to_natal(callback: CallbackQuery):
    await _go(callback)
    from handlers.natal import cmd_natal
    await cmd_natal(callback.message)


@router.callback_query(F.data == "menu_favorable")
async def menu_to_favorable(callback: CallbackQuery):
    await _go(callback)
    from handlers.favorable import cmd_favorable
    await cmd_favorable(callback.message)


@router.callback_query(F.data == "menu_compat")
async def menu_to_compat(callback: CallbackQuery, state: FSMContext):
    await _go(callback)
    from handlers.compatibility import cmd_compat
    await cmd_compat(callback.message, state)


@router.callback_query(F.data == "menu_profile")
async def menu_to_profile(callback: CallbackQuery):
    await _go(callback)
    from handlers.profile import cmd_profile
    await cmd_profile(callback.message)


@router.callback_query(F.data == "menu_chat")
async def menu_to_chat(callback: CallbackQuery, state: FSMContext):
    await _go(callback)
    from handlers.chat import cmd_chat
    await cmd_chat(callback.message, state)


@router.callback_query(F.data == "menu_dream")
async def menu_to_dream(callback: CallbackQuery, state: FSMContext):
    await _go(callback)
    from handlers.dreams import cmd_dream
    await cmd_dream(callback.message, state)


@router.callback_query(F.data == "menu_buy")
async def menu_to_buy(callback: CallbackQuery):
    await _go(callback)
    from handlers.payment import cmd_buy
    await cmd_buy(callback.message)
