import asyncio

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models.user import is_premium
from services.favorable_days import generate_favorable_days

router = Router()


@router.message(Command("favorable"))
async def cmd_favorable(message: Message):
    user_id = message.chat.id
    if not is_premium(user_id):
        b = InlineKeyboardBuilder()
        b.button(text="💎 Оформить подписку", callback_data="menu_profile")
        b.button(text="📋 Меню", callback_data="menu_main")
        await message.answer(
            "📅 <b>Благоприятные дни</b>\n\n"
            "Этот раздел доступен только подписчикам 💎\n\n"
            "Календарь благоприятных дней покажет:\n"
            "— 🟢 Когда начинать новые дела\n"
            "— 🟡 Нейтральные дни для текущих задач\n"
            "— 🔴 Дни, когда лучше отдохнуть и не рисковать\n\n"
            "Оформи подписку, чтобы планировать жизнь по звёздам ✨",
            reply_markup=b.as_markup(),
        )
        return

    status = await message.answer("📅 Составляю календарь благоприятных дней...")
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(2)

    text = await generate_favorable_days(10)
    await status.delete()

    b = InlineKeyboardBuilder()
    b.button(text="📋 Меню", callback_data="menu_main")
    await message.answer(
        f"📅 <b>Благоприятные дни</b>\n\n{text}",
        reply_markup=b.as_markup(),
    )
