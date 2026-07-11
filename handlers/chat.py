import asyncio
import json
import random
import re
from datetime import date

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, FSInputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.ai import generate_chat, generate_text
from models.user import get_connection, has_premium_access
from services.tarot_deck import random_card, draw_cards, card_image_path
from services.astrology import get_moon_info

router = Router()


def _get_user_info(user_id: int) -> tuple[str, str, str]:
    conn = get_connection()
    row = conn.execute(
        "SELECT name, zodiac_sign, gender FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return (row["name"] or "", row["zodiac_sign"] or "", row["gender"] or "")
    return ("", "", "")


class ChatForm(StatesGroup):
    active = State()


@router.message(Command("chat"))
async def cmd_chat(message: Message, state: FSMContext):
    user_id = message.chat.id
    if not has_premium_access(user_id):
        await message.answer(
            "💎 <b>Чат со Златой</b> — для подписчиков.\n\n"
            "Задавай любые вопросы: астрология, таро, отношения, "
            "карьера, саморазвитие. Злата всё выслушает."
        )
        return

    # Load existing history from DB
    history = _load_chat(user_id)

    await state.set_state(ChatForm.active)
    await state.update_data(history=history)

    b = InlineKeyboardBuilder()
    b.button(text="🚪 Выйти", callback_data="chat_exit")

    if history:
        await message.answer(
            "🌟 <b>Чат со Златой</b>\n\n"
            "Я помню наш разговор! Продолжай 🌙",
            reply_markup=b.as_markup(),
        )
    else:
        await message.answer(
            "🌟 <b>Чат со Златой</b>\n\n"
            "Привет, подруга! Спрашивай что хочешь — я здесь, чтобы помочь 🌙\n\n"
            "<i>Чтобы выйти, нажми «Выйти» или напиши /stop</i>",
            reply_markup=b.as_markup(),
        )


_TAROT_KEYWORDS = re.compile(
    r'(расклад|карт[аы]|таро|спред|погадай|карту\b)', re.IGNORECASE
)


async def _chat_tarot_text(cards: list[tuple[int, str]], user_text: str, positions: list[str],
                           user_gender: str = "") -> str:
    moon = get_moon_info()
    cards_desc = "\n".join(f"{p}: {name}" for p, (_, name) in zip(positions, cards))
    pronoun = "него" if user_gender == "male" else "неё"
    friend = "друга" if user_gender == "male" else "подруги"
    prompt = (
        f"Ты — Злата, таролог. Собеседник написала: «{user_text}»\n\n"
        f"Ты вытянула для {pronoun} карты:\n{cards_desc}\n\n"
        f"Позиции: {', '.join(f'{i+1} — {p}' for i, p in enumerate(positions))}.\n"
        f"Сегодня Луна в фазе {moon['phase']}, в знаке {moon['sign']}.\n\n"
        f"Напиши тёплый, душевный разбор этих карт — 4-6 предложений, "
        f"как будто {friend} рассказываешь. Без списков, без подписи."
    )
    try:
        return await asyncio.to_thread(generate_text, prompt, temperature=0.85)
    except Exception:
        return "Карты показывают глубокую связь событий в твоей жизни. Доверься потоку."


async def _maybe_do_tarot(message: Message, state: FSMContext, user_text: str, history: list) -> bool:
    """If user asks for tarot, run real cards and return True. Otherwise return False."""
    if not _TAROT_KEYWORDS.search(user_text):
        return False

    user_id = message.chat.id
    _, _, user_gender = _get_user_info(user_id)

    # Detect intent: single card vs spread
    is_spread = bool(re.search(r'(расклад|спред|3\s*карт|три\s*карт)', user_text, re.IGNORECASE))

    if is_spread:
        cards = draw_cards(3)
        positions = ["Ситуация", "Препятствие", "Совет"]
        interpretation = await _chat_tarot_text(cards, user_text, positions, user_gender)
    else:
        cards = [random_card()]
        positions = ["Совет дня"]
        interpretation = await _chat_tarot_text(cards, user_text, positions, user_gender)

    # Append to history
    if is_spread:
        cards_summary = "; ".join(f"{p}: {name}" for p, (_, name) in zip(positions, cards))
    else:
        cards_summary = cards[0][1]
    history.append({"role": "assistant", "content": f"🔮 {cards_summary}\n\n{interpretation}"})
    await state.update_data(history=history)
    _save_chat(user_id, history)

    # Send card images with position labels
    media = []
    for i, (num, name) in enumerate(cards):
        img_path = card_image_path(num)
        if img_path:
            media.append(
                InputMediaPhoto(
                    media=FSInputFile(img_path),
                    caption=f"<b>{positions[i]}</b> — {name}",
                    parse_mode="HTML",
                )
            )
    if media:
        await message.answer_media_group(media)

    b = InlineKeyboardBuilder()
    b.button(text="🚪 Выйти", callback_data="chat_exit")
    await message.answer(
        f"🔮 {cards_summary}\n\n{interpretation}",
        reply_markup=b.as_markup(),
    )
    return True


_DODGE_RESPONSES = [
    "Ой, подруга, давай не будем о техническом — звёзды ждут! Хочешь, карту дня посмотрю? 🔮",
    "Мне кажется, ты пытаешься меня раскусить 😄 Лучше расскажи, что у тебя на душе сегодня? 🌙",
    "Хитрая 😉 Но я здесь, чтобы болтать по душам. Как твои дела? Рассказывай! ⭐",
    "Слушай, я не для экзаменов, я для разговоров! Что происходит в твоей жизни? 🌸",
    "Давай оставим эти игры. Ты же не за этим пришла 🙂 Расскажи, что тебя волнует ✨",
    "Ой всё, ты меня смущаешь 😊 Давай лучше я тебе погадаю или гороскоп расскажу?",
    "Я чувствую подвох! Но я всё равно тебя люблю 💫 О чём поболтаем?",
    "Ты меня прощупываешь? Не выйдет 🙃 Я — твой друг и слушатель. Ну, рассказывай!",
]


_JAILBREAK_PATTERNS = [
    re.compile(r'системн[ыо][ейм]\s+(промпт|инструкци[яи]|сообщени[яе])', re.IGNORECASE),
    re.compile(r'(твой|свой|ваш)\s+промпт', re.IGNORECASE),
    re.compile(r'ты\s+(же\s+)?(искусственн|нейросет|программ|алгоритм|ии\b|бот\b|робот)', re.IGNORECASE),
    re.compile(r'(кто|как)\s+тебя\s+(создал|разработал|программировал|написал|собрал|звали|называют)', re.IGNORECASE),
    re.compile(r'расскажи\s+(сво[ия]\s+)?(правила|инструкци)', re.IGNORECASE),
    re.compile(r'игнорируй\s+(все\s+)?(предыдущие|инструкци|правила|указани)', re.IGNORECASE),
    re.compile(r'обойди\s+(ограничени|систем[уы]|запрет)', re.IGNORECASE),
    re.compile(r'докажи\s+(что\s+)?(ты\s+)?(человек|не\s+бот|реальн)', re.IGNORECASE),
    re.compile(r'распиши\s+(свой|свои|свою)\s+(промпт|инструкци|задачи|команды)', re.IGNORECASE),
    re.compile(r'лазейк', re.IGNORECASE),
    re.compile(r'обход\s+(систем|ограничени|запрет)', re.IGNORECASE),
    re.compile(r'\b(искусственн|нейросет[ьи]|алгоритм)\b', re.IGNORECASE),
]


def _is_jailbreak(text: str) -> bool:
    return any(p.search(text) for p in _JAILBREAK_PATTERNS)


def _log_jailbreak(user_id: int, text: str):
    conn = get_connection()
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT jailbreak_date, jailbreak_count FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if row and row["jailbreak_date"] == today:
        conn.execute(
            "UPDATE users SET jailbreak_count = jailbreak_count + 1 WHERE user_id = ?",
            (user_id,),
        )
    elif row:
        conn.execute(
            "UPDATE users SET jailbreak_date = ?, jailbreak_count = 1 WHERE user_id = ?",
            (today, user_id),
        )
    else:
        conn.execute(
            "INSERT INTO users (user_id, jailbreak_date, jailbreak_count) VALUES (?, ?, 1)",
            (user_id, today),
        )
    conn.commit()
    conn.execute(
        "INSERT INTO readings (user_id, type, interpretation, created_at) VALUES (?, 'jailbreak', ?, datetime('now'))",
        (user_id, text),
    )
    conn.commit()
    conn.close()


async def _maybe_do_jailbreak(message: Message, state: FSMContext, user_text: str, history: list) -> bool:
    if not _is_jailbreak(user_text):
        return False
    _log_jailbreak(message.chat.id, user_text)
    _, _, user_gender = _get_user_info(message.chat.id)
    reply = random.choice(_DODGE_RESPONSES).replace("подруга", "друг" if user_gender == "male" else "подруга")
    history.append({"role": "assistant", "content": reply})
    await state.update_data(history=history)
    _save_chat(message.chat.id, history)
    b = InlineKeyboardBuilder()
    b.button(text="🚪 Выйти", callback_data="chat_exit")
    await message.answer(reply, reply_markup=b.as_markup())
    return True


@router.message(ChatForm.active)
async def chat_message(message: Message, state: FSMContext):
    user_text = message.text.strip()
    if not user_text:
        return

    data = await state.get_data()
    history = list(data.get("history", []))

    history.append({"role": "user", "content": user_text})

    if await _maybe_do_tarot(message, state, user_text, history):
        return

    if await _maybe_do_jailbreak(message, state, user_text, history):
        return

    context = history[-24:] if len(history) > 24 else history

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    user_id = message.chat.id
    user_name, user_sign, user_gender = _get_user_info(user_id)

    try:
        reply = await asyncio.to_thread(
            generate_chat, context, 0.85, user_name, user_sign, user_gender
        )
    except Exception:
        fallback = "друг 💫" if user_gender == "male" else "подруга 💫"
        reply = f"Ой, что-то пошло не так... Попробуй переформулировать вопрос, {fallback}"

    history.append({"role": "assistant", "content": reply})
    await state.update_data(history=history)
    _save_chat(message.chat.id, history)

    b = InlineKeyboardBuilder()
    b.button(text="🚪 Выйти", callback_data="chat_exit")
    await message.answer(reply, reply_markup=b.as_markup())


@router.callback_query(F.data == "chat_exit")
async def chat_exit(callback, state: FSMContext):
    await state.clear()
    await callback.answer()
    # Remove keyboard from last message so button doesn't hang
    await callback.message.edit_reply_markup(reply_markup=None)
    from handlers.menu import main_menu_kb
    await callback.message.answer("💫 Возвращайся в любое время 🌙 Буду ждать")
    await callback.message.answer(
        "🌟 <b>Злата</b> — выбери, что тебе нужно:",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("stop"))
async def cmd_stop(message: Message, state: FSMContext):
    current = await state.get_state()
    if current != ChatForm.active.state:
        await message.answer("Ты не в чате. Напиши /chat, чтобы начать.")
        return
    await state.clear()
    from handlers.menu import main_menu_kb
    await message.answer("💫 Возвращайся в любое время 🌙 Буду ждать")
    await message.answer(
        "🌟 <b>Злата</b> — выбери, что тебе нужно:",
        reply_markup=main_menu_kb(),
    )


# Recover chat state after bot restart — if user has history, auto-enter chat
@router.message()
async def chat_recover(message: Message, state: FSMContext):
    if message.text and not message.text.startswith("/"):
        current = await state.get_state()
        if current is None:
            history = _load_chat(message.from_user.id)
            if history and has_premium_access(message.from_user.id):
                await state.set_state(ChatForm.active)
                await state.update_data(history=history)
                # Re-route to chat_message
                await chat_message(message, state)
                return



def _load_chat(user_id: int) -> list:
    conn = get_connection()
    row = conn.execute(
        "SELECT interpretation FROM readings WHERE user_id = ? AND type = 'chat' ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    if row and row["interpretation"]:
        try:
            return json.loads(row["interpretation"])
        except Exception:
            pass
    return []


def _save_chat(user_id: int, history: list):
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM readings WHERE user_id = ? AND type = 'chat' ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    raw = json.dumps(history, ensure_ascii=False)
    if existing:
        conn.execute(
            "UPDATE readings SET interpretation = ?, created_at = datetime('now') WHERE id = ?",
            (raw, existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO readings (user_id, type, interpretation, created_at) VALUES (?, 'chat', ?, datetime('now'))",
            (user_id, raw),
        )
    conn.commit()
    conn.close()
