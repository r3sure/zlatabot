import asyncio
from datetime import date

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.ai import generate_text
from services.astrology import get_moon_info, get_daily_context
from models.user import get_connection, has_premium_access

router = Router()


class DreamForm(StatesGroup):
    waiting_dream = State()


MONTHLY_LIMIT_FREE = 1


def get_monthly_dream_count(user_id: int) -> int:
    conn = get_connection()
    month_start = date.today().replace(day=1).isoformat()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM dreams WHERE user_id = ? AND created_at >= ?",
        (user_id, month_start),
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


async def _dream_text(dream: str) -> str:
    moon = get_moon_info()
    ctx = get_daily_context()
    prompt = (
        f"Ты — Злата, толкователь снов и эзотерик. "
        f"Тебе приснился сон.\n\n"
        f"Сон: {dream}\n\n"
        f"{ctx['day_of_week']}, {ctx['date']}. "
        f"Луна в фазе {ctx['moon_phase']}, в знаке {ctx['moon_sign']}.\n\n"
        f"Растолкуй этот сон — 5-7 предложений. "
        f"Свяжи с текущим положением луны и сезоном ({ctx['season']}). "
        f"Напиши, какие знаки и символы несут ключевой смысл. "
        f"Заверши советом. Вдохновляюще, с обращением на «ты». Без подписи."
    )
    try:
        return await asyncio.to_thread(generate_text, prompt, temperature=0.85)
    except Exception:
        return (
            "Твой сон наполнен глубокими символами, "
            "которые говорят о внутренних процессах. "
            "Прислушайся к своей интуиции."
        )


@router.message(Command("dream"))
async def cmd_dream(message: Message, state: FSMContext):
    user_id = message.chat.id
    count = get_monthly_dream_count(user_id)

    if not has_premium_access(user_id) and count >= MONTHLY_LIMIT_FREE:
        b = InlineKeyboardBuilder()
        b.button(text="💎 Оформить подписку", callback_data="menu_profile")
        b.button(text="📋 Меню", callback_data="menu_main")
        await message.answer(
            "🌙 <b>Толкование снов</b>\n\n"
            "Этот месяц ты уже использовала бесплатное толкование снов.\n\n"
            "💎 <b>Оформи подписку</b> и получай:\n"
            "— Безлимитное толкование снов\n"
            "— Чат со Златой\n"
            "— Расклады Таро\n"
            "— Глубокие разборы\n\n"
            "Сны — это голос твоего подсознания. "
            "Не оставляй их без ответа 🌙",
            reply_markup=b.as_markup(),
        )
        return

    remaining = MONTHLY_LIMIT_FREE - count if not has_premium_access(user_id) else "∞"
    await state.set_state(DreamForm.waiting_dream)
    b = InlineKeyboardBuilder()
    b.button(text="↩️ Назад", callback_data="dream_back")
    await message.answer(
        "🌙 <b>Толкование снов</b>\n\n"
        "Опиши свой сон — даже самые странные детали важны.\n"
        "Я растолкую знаки и символы, которые тебе прислало подсознание ✨\n\n"
        f"{'📊 Бесплатных толкований в этом месяце: ' + str(remaining) if remaining != '∞' else ''}",
        reply_markup=b.as_markup(),
    )


@router.callback_query(F.data == "dream_back")
async def dream_back(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    from handlers.menu import main_menu_kb
    await callback.message.answer(
        "🌟 <b>Злата</b> — выбери, что тебе нужно:",
        reply_markup=main_menu_kb(),
    )


@router.message(DreamForm.waiting_dream)
async def dream_received(message: Message, state: FSMContext):
    dream = message.text.strip()
    if not dream or len(dream) < 10:
        await message.answer("Опиши сон подробнее — минимум 10 символов 🌙")
        return

    await state.clear()
    status = await message.answer("🌙 Толкую твой сон...")
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    interpretation = await _dream_text(dream)
    await status.delete()

    user_id = message.chat.id
    conn = get_connection()
    conn.execute(
        "INSERT INTO dreams (user_id, dream_text, interpretation, created_at) VALUES (?, ?, ?, datetime('now'))",
        (user_id, dream, interpretation),
    )
    conn.commit()
    conn.close()

    b = InlineKeyboardBuilder()
    if not has_premium_access(user_id):
        remaining = MONTHLY_LIMIT_FREE - get_monthly_dream_count(user_id) - 1
        if remaining <= 0:
            b.button(text="💎 Безлимит снов", callback_data="menu_profile")
    b.button(text="📋 Меню", callback_data="menu_main")

    await message.answer(
        f"🌙 <b>Толкование сна</b>\n\n{interpretation}",
        reply_markup=b.as_markup(),
    )
