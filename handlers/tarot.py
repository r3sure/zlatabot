import asyncio
import random
from datetime import date, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.ai import generate_text
from services.tarot_deck import TAROT_DECK, card_by_seed, card_image_path, random_card
from services.astrology import get_moon_info, get_daily_context
from models.user import get_connection, is_premium, has_premium_access

router = Router()


class TarotForm(StatesGroup):
    waiting_situation_3 = State()
    waiting_situation_7 = State()


# ── Layouts ──
DAY_LAYOUT = ("🌅 Энергия дня", "🎯 Фокус внимания", "⭐ Совет звёзд")
DEFAULT_LAYOUT = ("Ситуация", "Препятствие", "Совет")





# ── Helpers ──
async def _typing_delay(message: Message, seconds: int):
    end = asyncio.get_event_loop().time() + seconds
    while asyncio.get_event_loop().time() < end:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        await asyncio.sleep(min(4, end - asyncio.get_event_loop().time()))


def _daily_context() -> str:
    ctx = get_daily_context()
    return (
        f"Сегодня {ctx['day_of_week']}, {ctx['date']}. "
        f"На дворе {ctx['season']}. "
        f"Луна в фазе {ctx['moon_phase']}, в знаке {ctx['moon_sign']}."
    )


# ── Card of the day ──
async def _card_of_the_day_text(card_num: int, card_name: str) -> str:
    prompt = (
        f"Ты — таролог Злата. Выпала карта дня: {card_name}.\n"
        f"{_daily_context()}\n\n"
        f"Напиши значение этой карты как карты дня — 3-4 предложения, "
        f"вдохновляюще, с обращением на «ты». Без подписи."
    )
    try:
        return await asyncio.to_thread(generate_text, prompt)
    except Exception:
        return "Сегодня звёзды и карты подготовили для тебя важный урок. Доверься потоку."


async def _card_detailed_text(card_num: int, card_name: str) -> str:
    prompt = (
        f"Ты — таролог Злата. Карта дня — {card_name}.\n"
        f"{_daily_context()}\n\n"
        f"Сделай глубокое, подробное толкование этой карты — "
        f"7-10 предложений. Распиши влияние на разные сферы жизни: "
        f"отношения, карьеру, самочувствие, финансы. "
        f"Вдохновляюще, с обращением на «ты». Без подписи."
    )
    try:
        return await asyncio.to_thread(generate_text, prompt, temperature=0.85)
    except Exception:
        return "Карта несёт глубокий смысл. Попробуй позже вернуться к ней."


@router.message(Command("card"))
async def cmd_card_day(message: Message):
    today = str(date.today())
    card_num, card_name = card_by_seed(today)

    status_text = random.choice([
        "Смотрю, что говорят карты... 🃏",
        "Карты уже готовятся открыть тайну... ✨",
        "Чувствую сегодняшнюю энергию... 🌟",
        "Слушаю шёпот Вселенной... 🌌",
        "Собираю звёздную пыль для тебя... 🌙",
        "Карты скользят в моих руках... 🔮",
    ])
    status = await message.answer(status_text)
    await _typing_delay(message, 5)
    text = await _card_of_the_day_text(card_num, card_name)
    await status.delete()

    b = InlineKeyboardBuilder()
    b.button(text="🔮 Подробнее", callback_data="card_detail")
    b.button(text="📋 Меню", callback_data="menu_main")

    img_path = card_image_path(card_num)
    if img_path:
        photo = FSInputFile(img_path)
        await message.answer_photo(
            photo=photo,
            caption=f"🃏 <b>Карта дня</b>\n\n{card_name}\n\n{text}",
            reply_markup=b.as_markup(),
        )
    else:
        await message.answer(
            f"🃏 <b>Карта дня</b>\n\n{card_name}\n\n{text}",
            reply_markup=b.as_markup(),
        )


@router.callback_query(F.data == "card_detail")
async def card_detail(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    if not has_premium_access(user_id):
        await callback.message.answer(
            "💎 <b>Подробный разбор карты</b> — для подписчиков.\n\n"
            "Оформи подписку, чтобы получать глубокие толкования 🔮"
        )
        return

    today = str(date.today())
    card_num, card_name = card_by_seed(today)
    status = await callback.message.answer(
        random.choice([
            "Открываю глубинный смысл карты... 🔮",
            "Карта раскрывает свои тайны... ✨",
            "Читаю знаки и символы... 🌟",
            "Слушаю, что говорит карта... 🌌",
        ])
    )
    text = await _card_detailed_text(card_num, card_name)
    await status.delete()
    b = InlineKeyboardBuilder()
    b.button(text="📋 Меню", callback_data="menu_main")
    await callback.message.answer(
        f"🔮 <b>Подробный разбор: {card_name}</b>\n\n{text}",
        reply_markup=b.as_markup(),
    )


# ── 3-card spread ──
SPREAD3_STATUSES = [
    "Чувствую энергию карт... 🌌",
    "Карты уже готовятся открыть тайны... 🔮",
    "Слушаю тишину между мирами... ✨",
    "Собираю звёздную пыль для твоего расклада... 🌙",
    "Карты скользят в моих руках... 🃏",
]


async def _spread3_text(cards: list[tuple[int, str]], positions: tuple[str, str, str],
                        situation: str | None = None, user_sign: str | None = None,
                        day_offset: int = -1) -> str:
    cards_desc = "\n".join(
        f"{p}: {name}" for p, (_, name) in zip(positions, cards)
    )
    situation_part = (
        f"Ситуация от пользователя: {situation}\n\n"
        if situation else ""
    )
    sign_part = (
        f"Знак пользователя: {user_sign}\n\n"
        if user_sign else ""
    )

    if day_offset >= 0:
        day_label = "сегодняшнего" if day_offset == 0 else "завтрашнего"
        prompt = (
            f"Ты — таролог и астролог Злата. Делаю персонализированный расклад на {day_label} день.\n\n"
            f"{sign_part}"
            f"Карты:\n{cards_desc}\n\n"
            f"Позиции: 1 — {positions[0]}, 2 — {positions[1]}, 3 — {positions[2]}.\n"
            f"{_daily_context()}\n\n"
            f"Напиши разбор в таком формате — каждую секцию с новой строки:\n"
            f"🌅 <b>{positions[0]}</b>\n"
            f"[3-4 предложения об энергии {day_label} дня, "
            f"что несёт утро, на что обратить внимание с учётом фазы Луны]\n\n"
            f"☀️ <b>{positions[1]}</b>\n"
            f"[3-4 предложения о главной задаче дня, "
            f"на чём сосредоточиться, чего избегать]\n\n"
            f"⭐ <b>{positions[2]}</b>\n"
            f"[3-4 предложения итогового совета с учётом фазы Луны и твоего знака]\n\n"
            f"Красиво, вдохновляюще, с обращением на «ты». Без подписи."
        )
    else:
        prompt = (
            f"Ты — таролог Злата. Делаю расклад на 3 карты.\n\n"
            f"{situation_part}{sign_part}"
            f"Карты:\n{cards_desc}\n\n"
            f"Позиции: 1 — {positions[0]}, 2 — {positions[1]}, 3 — {positions[2]}.\n"
            f"{_daily_context()}\n\n"
            f"Напиши разбор в таком формате — каждую секцию с новой строки:\n"
            f"📌 <b>[Позиция] — [Карта]</b>\n"
            f"[2-3 предложения, что значит эта карта именно в этой позиции]\n\n"
            f"🔗 <b>Как карты пересекаются</b>\n"
            f"[3-4 предложения о связи карт]\n\n"
            f"💎 <b>Совет</b>\n"
            f"[2-3 предложения итогового совета]\n\n"
            f"Красиво, вдохновляюще, с обращением на «ты». Без подписи. Без лишних слов."
        )
    try:
        return await asyncio.to_thread(generate_text, prompt, temperature=0.85)
    except Exception:
        return (
            "Карты показывают глубокую взаимосвязь событий в твоей жизни. "
            "Каждая карта — это часть большого пазла. "
            "Доверься потоку — ответы уже рядом."
        )


async def _send_3_spread(message: Message, cards: list, positions: tuple[str, str, str], text: str,
                         state: FSMContext | None = None, source: str = "simple",
                         date_str: str | None = None):
    # Send 3 cards as media group (informative → stays)
    media = []
    for i, (num, name) in enumerate(cards):
        img_path = card_image_path(num)
        if img_path:
            media.append(
                InputMediaPhoto(
                    media=FSInputFile(img_path),
                    caption=f"<b>{i+1}. {positions[i]}</b> — {name}",
                    parse_mode="HTML",
                )
            )
    media_msg_ids = []
    if media:
        msgs = await message.answer_media_group(media)
        media_msg_ids = [m.message_id for m in msgs]

    # Send interpretation WITHOUT buttons (informative → stays)
    if date_str:
        text = f"📅 <b>{date_str}</b>\n\n{text}"
    text_msg = await message.answer(text, parse_mode="HTML")

    # Send action buttons as a separate message (menu-related → disappears)
    b = InlineKeyboardBuilder()
    if source != "day":
        b.button(text="🔄 Перетянуть", callback_data="spread3_regen")
    b.button(text="❌ Отмена", callback_data="spread3_delete")
    b.button(text="📋 Меню", callback_data="spread3_menu")
    b.adjust(2, 1) if source != "day" else b.adjust(1, 2)
    header = f"📅 {date_str} — " if date_str else ""
    buttons_msg = await message.answer(f"{header}🔮 Выбери действие:", reply_markup=b.as_markup())

    if state:
        await state.update_data(spread3_cards=cards, spread3_positions=positions,
                                 spread3_text=text, spread3_source=source,
                                 spread3_media_ids=media_msg_ids,
                                 spread3_text_msg_id=text_msg.message_id,
                                 spread3_buttons_msg_id=buttons_msg.message_id)


def _save_spread3(user_id: int, cards: list, text: str):
    conn = get_connection()
    cards_json = ", ".join(name for _, name in cards)
    conn.execute(
        "INSERT INTO readings (user_id, type, cards, interpretation, created_at) VALUES (?, 'spread', ?, ?, datetime('now'))",
        (user_id, cards_json, text),
    )
    conn.commit()
    conn.close()


@router.callback_query(F.data == "spread3_delete")
async def spread3_delete(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Расклад удалён")
    data = await state.get_data()
    chat_id = callback.message.chat.id

    # Delete cards (media group)
    for mid in data.get("spread3_media_ids", []):
        try:
            await callback.bot.delete_message(chat_id, mid)
        except Exception:
            pass
    # Delete interpretation text
    tid = data.get("spread3_text_msg_id")
    if tid:
        try:
            await callback.bot.delete_message(chat_id, tid)
        except Exception:
            pass

    # Delete buttons message
    try:
        await callback.message.delete()
    except Exception:
        pass

    await state.clear()

    from handlers.menu import main_menu_kb
    await callback.message.answer(
        "🌟 <b>Злата</b> — выбери, что тебе нужно:",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "spread3_menu")
async def spread3_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    # Delete only the buttons message (informative messages stay)
    try:
        await callback.message.delete()
    except Exception:
        pass
    from handlers.menu import main_menu_kb, _build_menu_message
    msg = await _build_menu_message(callback.from_user.id)
    await callback.message.answer(msg, reply_markup=main_menu_kb())


@router.callback_query(F.data == "spread3_regen")
async def spread3_regen(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    chat_id = callback.message.chat.id

    # Delete old cards (media group)
    for mid in data.get("spread3_media_ids", []):
        try:
            await callback.bot.delete_message(chat_id, mid)
        except Exception:
            pass
    # Delete old interpretation text
    tid = data.get("spread3_text_msg_id")
    if tid:
        try:
            await callback.bot.delete_message(chat_id, tid)
        except Exception:
            pass

    # Delete old buttons message (the one that triggered the callback)
    try:
        await callback.message.delete()
    except Exception:
        pass

    positions = data.get("spread3_positions", DEFAULT_LAYOUT)
    source = data.get("spread3_source", "simple")
    situation = data.get("spread3_situation", "")
    day_offset = data.get("spread3_day_offset", -1)

    user_id = callback.message.chat.id
    user_sign = _get_user_sign(user_id)
    status_text = random.choice(SPREAD3_STATUSES)
    status = await callback.message.answer(status_text)
    await _typing_delay(callback.message, 10)
    cards = [random_card() for _ in range(3)]
    if day_offset >= 0:
        text = await _spread3_text(cards, positions, user_sign=user_sign, day_offset=day_offset)
    elif source == "situation" and situation:
        text = await _spread3_text(cards, positions, situation, user_sign)
    else:
        text = await _spread3_text(cards, positions, user_sign=user_sign)
    await status.delete()
    await _send_3_spread(callback.message, cards, positions, text, state=state, source=source)


def _get_user_sign(user_id: int) -> str | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT zodiac_sign FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row["zodiac_sign"] if row and row["zodiac_sign"] else None


def _has_ever_done_spread(user_id: int) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM readings WHERE user_id = ? AND type = 'spread' LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return row is not None


def _seeded_cards(seed: str, count: int = 3) -> list:
    """Deterministic cards: same seed → same cards."""
    rng = random.Random(seed)
    deck = list(TAROT_DECK.items())
    return rng.sample(deck, count)


@router.message(Command("spread"))
async def cmd_spread_command(message: Message, state: FSMContext):
    await cmd_spread(message, state=state)


async def cmd_spread_day(message: Message, state: FSMContext | None = None, day_offset: int = 0):
    """Personalized day-forecast spread — uses DAY_LAYOUT + special prompt.
    day_offset=0 → сегодня, day_offset=1 → завтра.
    Cards are deterministic: same user + same target date → same cards."""
    user_id = message.chat.id
    is_prem = has_premium_access(user_id)
    if not is_prem:
        if _has_ever_done_spread(user_id):
            b = InlineKeyboardBuilder()
            b.button(text="💎 Оформить подписку", callback_data="menu_profile")
            b.button(text="📋 Меню", callback_data="menu_main")
            await message.answer(
                "🔮 <b>Прогноз на день</b> — для подписчиков 💎\n\n"
                "Ты уже использовала пробный расклад. Оформи подписку:\n"
                "— Персонализированный прогноз на каждый день\n"
                "— С учётом фазы Луны и твоего знака\n"
                "— Расклад на 3 карты под ситуацию\n"
                "— Расклад на 7 карт",
                reply_markup=b.as_markup(),
            )
            return
        await message.answer(
            "🔮 <b>Пробный прогноз на день</b>\n\n"
            "Это твой первый расклад — он бесплатно! 🌟\n"
            "Оцени глубину и точность, а потом реши, "
            "нужна ли тебе подписка 💎"
        )

    if state:
        await state.update_data(spread3_day_offset=day_offset)

    user_sign = _get_user_sign(user_id)
    target_date = date.today() + timedelta(days=day_offset)
    date_str = target_date.strftime("%d.%m")
    seed = f"{target_date.isoformat()}_{user_id}"
    status_text = random.choice(SPREAD3_STATUSES)
    status = await message.answer(status_text)
    await _typing_delay(message, 10)
    cards = _seeded_cards(seed, 3)
    text = await _spread3_text(cards, DAY_LAYOUT, user_sign=user_sign, day_offset=day_offset)
    await status.delete()
    await _send_3_spread(message, cards, DAY_LAYOUT, text, state=state, source="day", date_str=date_str)


async def cmd_spread(message: Message, positions: tuple[str, str, str] = DEFAULT_LAYOUT,
                     state: FSMContext | None = None, source: str = "simple"):
    user_id = message.chat.id
    is_prem = has_premium_access(user_id)
    if not is_prem:
        # Allow 1 free trial spread if never done before
        if _has_ever_done_spread(user_id):
            b = InlineKeyboardBuilder()
            b.button(text="💎 Оформить подписку", callback_data="menu_profile")
            b.button(text="📋 Меню", callback_data="menu_main")
            await message.answer(
                "🔮 <b>Расклад на 3 карты</b> — для подписчиков 💎\n\n"
                "Ты уже использовала пробный расклад. Оформи подписку:\n"
                "— Любые позиции расклада\n"
                "— Разбор под ситуацию\n"
                "— Связь карт и глубокий совет\n"
                "— Расклад на 7 карт",
                reply_markup=b.as_markup(),
            )
            return
        # First spread — free trial
        await message.answer(
            "🔮 <b>Пробный расклад на 3 карты</b>\n\n"
            "Это твой первый расклад — он бесплатно! 🌟\n"
            "Оцени глубину и точность, а потом реши, "
            "нужна ли тебе подписка 💎"
        )

    user_sign = _get_user_sign(user_id)
    status_text = random.choice(SPREAD3_STATUSES)
    status = await message.answer(status_text)
    await _typing_delay(message, 10)
    cards = [random_card() for _ in range(3)]
    text = await _spread3_text(cards, positions, user_sign=user_sign)
    await status.delete()
    await _send_3_spread(message, cards, positions, text, state=state, source=source)


@router.message(TarotForm.waiting_situation_3)
async def cmd_spread_3_situation(message: Message, state: FSMContext):
    user_id = message.chat.id
    if not has_premium_access(user_id):
        await message.answer("💎 <b>Расклад на 3 карты</b> — для подписчиков.")
        await state.clear()
        return

    situation = message.text.strip()
    if not situation:
        await message.answer("Напиши свою ситуацию, и я вытяну карты 🌟")
        return

    data = await state.get_data()
    positions = tuple(data.get("positions", DEFAULT_LAYOUT))

    await state.update_data(spread3_situation=situation)

    user_sign = _get_user_sign(user_id)
    status_text = random.choice(SPREAD3_STATUSES)
    status = await message.answer(status_text)
    await _typing_delay(message, 10)
    cards = [random_card() for _ in range(3)]
    text = await _spread3_text(cards, positions, situation, user_sign)
    await status.delete()
    await _send_3_spread(message, cards, positions, text, state=state, source="situation")


# ── Layout selection callbacks (removed — only default layout used) ──


# ── 7-card spread ──
SPREAD7_POSITIONS = [
    "Прошлое", "Настоящее", "Будущее",
    "Причина", "Препятствие", "Совет", "Итог",
]

SPREAD7_STATUSES = [
    "Карты выстраиваются в судьбоносный узор... 🌌",
    "Глубокий расклад требует тишины. Слушаю твою историю... 🃏",
    "Звёзды и карты сплетаются в единое полотно... ✨",
    "Чувствую мощный поток энергии. Раскладываю... 🔮",
    "Семь карт — семь ключей к твоей судьбе... 🌙",
]


async def _spread7_text(cards: list[tuple[int, str]], situation: str) -> str:
    cards_desc = "\n".join(
        f"{p}: {name}" for p, (_, name) in zip(SPREAD7_POSITIONS, cards)
    )
    positions_desc = ", ".join(f"{i+1} — {p}" for i, p in enumerate(SPREAD7_POSITIONS))
    prompt = (
        f"Ты — таролог Злата. Делаю глубокий расклад на 7 карт.\n\n"
        f"Ситуация от пользователя: {situation}\n\n"
        f"Карты:\n{cards_desc}\n\n"
        f"Позиции: {positions_desc}.\n"
        f"{_daily_context()}\n\n"
        f"Напиши ПОДРОБНЫЙ разбор:\n"
        f"1. Значение каждой карты в её позиции (1-2 предложения на каждую)\n"
        f"2. Как карты складываются в общую картину (4-5 предложений)\n"
        f"3. Главный вывод и совет (3-4 предложения)\n\n"
        f"Красиво, вдохновляюще, с обращением на «ты». Без подписи."
    )
    try:
        return await asyncio.to_thread(generate_text, prompt, temperature=0.85)
    except Exception:
        fallback = "\n".join(
            f"<b>{p}:</b> {name}" for p, (_, name) in zip(SPREAD7_POSITIONS, cards)
        )
        return (
            f"Вот какие карты выпали:\n\n{fallback}\n\n"
            f"Каждая из них несёт свой смысл в твоей ситуации. "
            f"Попробуй заглянуть в себя — "
            f"какая карта откликается больше всего? "
            f"Доверься своей интуиции 🌟"
        )


@router.message(TarotForm.waiting_situation_7)
async def cmd_spread_7(message: Message, state: FSMContext):
    user_id = message.chat.id
    if not has_premium_access(user_id):
        await message.answer("💎 <b>Расклад на 7 карт</b> — для подписчиков.")
        await state.clear()
        return

    situation = message.text.strip()
    if not situation:
        await message.answer("Опиши свою ситуацию, и я вытяну карты 🌟")
        return

    status_text = random.choice(SPREAD7_STATUSES)
    status = await message.answer(status_text)
    await _typing_delay(message, 15)
    cards = [random_card() for _ in range(7)]
    text = await _spread7_text(cards, situation)

    await status.delete()

    media = []
    for i, (num, name) in enumerate(cards):
        img_path = card_image_path(num)
        if img_path:
            media.append(
                InputMediaPhoto(
                    media=FSInputFile(img_path),
                    caption=f"<b>{i+1}. {SPREAD7_POSITIONS[i]}</b> — {name}",
                    parse_mode="HTML",
                )
            )
    if media:
        await message.answer_media_group(media)

    b = InlineKeyboardBuilder()
    b.button(text="📋 Меню", callback_data="menu_main")
    await message.answer(
        f"🔮 <b>Расклад на 7 карт</b>\n\n{text}",
        reply_markup=b.as_markup(),
    )
    await state.clear()
    await callback.message.answer(msg, reply_markup=main_menu_kb())
