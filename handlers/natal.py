import asyncio

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.ai import generate_text
from services.natal import generate_chart_png, get_natal_text_for_ai, get_user_birth_data
from models.user import get_connection

router = Router()


def _save_reading(user_id: int, interpretation: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO readings (user_id, type, interpretation) VALUES (?, ?, ?)",
        (user_id, "natal", interpretation),
    )
    conn.commit()
    conn.close()


@router.message(Command("natal"))
async def cmd_natal(message: Message):
    user_data = get_user_birth_data(message.chat.id)
    if not user_data:
        await message.answer(
            "У тебя ещё нет полного профиля.\n"
            "Напиши /start, чтобы я узнала твою дату рождения и город.",
        )
        return

    status_msg = await message.answer("🔮 Рассчитываю натальную карту...")

    png_bytes = await generate_chart_png(message.chat.id)
    if not png_bytes:
        await status_msg.edit_text("Что-то пошло не так. Попробуй позже.")
        return

    ai_context = get_natal_text_for_ai(message.chat.id)

    detail_prompt = (
        f"Ты — астролог Злата. Сделай расшифровку натальной карты.\n\n"
        f"Данные:\n{ai_context}\n\n"
        f"Ровно 7 строк. Каждая с новой строки, начинается с эмодзи и заголовка:\n"
        f"🌞 Солнце — 1 предложение о личности\n"
        f"🌙 Луна — 1 предложение об эмоциях\n"
        f"👤 Асцендент — 1 предложение\n"
        f"💫 Ключевые черты — 1 предложение\n"
        f"📈 Карьера — 1 предложение\n"
        f"💕 Отношения — 1 предложение\n"
        f"💡 Совет — 1 предложение\n\n"
        f"Коротко, ёмко, без лишних слов. Тёплый тон, обращение на «ты» в женском роде. Без подписи."
    )

    summary_prompt = (
        f"Ты — астролог Злата. Напиши ровно 1 предложение — квинтэссенцию "
        f"натальной карты человека.\n\n"
        f"Данные:\n{ai_context}\n\n"
        f"Одно ёмкое, вдохновляющее предложение. Тёплый тон, женский род."
    )

    try:
        text = await generate_text(detail_prompt)
    except Exception:
        text = (
            "🌞 Солнце — твоя стихия — интуиция.\n"
            "🌙 Луна — эмоциональная глубина.\n"
            "💫 Твой путь — доверять себе.\n"
            "💡 Совет: прислушайся к тишине внутри."
        )

    try:
        summary = await generate_text(summary_prompt)
    except Exception:
        summary = "Энергии планет указывают на сильную интуицию и творческий потенциал."

    _save_reading(message.chat.id, text)

    await status_msg.delete()

    await message.answer_photo(
        BufferedInputFile(png_bytes, filename="natal.png"),
        caption=f"🔮 <b>Натальная карта</b>\n\n<i>{summary}</i>",
    )

    b = InlineKeyboardBuilder()
    b.button(text="📋 Меню", callback_data="menu_main")

    await message.answer(
        f"📜 <b>Твоя натальная карта</b>\n\n{text}",
        reply_markup=b.as_markup(),
    )
