import asyncio
import random

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.ai import generate_text
from services.astrology import get_moon_info
from services.moon_img import get_moon_image_bytes

router = Router()

MOON_STATUSES = [
    "Смотрю на ночное небо... 🌙",
    "Луна сегодня особенно красива... ✨",
    "Чувствую лунную энергию... 🌕",
    "Слушаю шёпот луны... 🌌",
    "Планеты выстраиваются в лунный узор... 🔮",
]


@router.message(Command("moon"))
async def cmd_moon(message: Message):
    status = await message.answer(random.choice(MOON_STATUSES))

    moon = get_moon_info()
    emoji = moon["emoji"]

    prompt = (
        f"Ты — астролог Злата. Сегодня Луна в фазе {moon['phase']} "
        f"в знаке {moon['sign']}.\n\n"
        f"Напиши рекомендацию на сегодня, учитывая эту лунную фазу и знак — "
        f"3-4 предложения, вдохновляюще, с обращением на «ты». Без подписи."
    )

    try:
        text = await asyncio.to_thread(generate_text, prompt)
    except Exception:
        text = (
            f"Энергия луны в фазе {moon['phase'].lower()} направляет тебя "
            f"к гармонии. Прислушайся к своим чувствам."
        )

    await status.delete()

    img_bytes = get_moon_image_bytes()
    photo = BufferedInputFile(img_bytes.getvalue(), filename="moon.png")

    b = InlineKeyboardBuilder()
    b.button(text="📋 Меню", callback_data="menu_main")

    caption = (
        f"{emoji} <b>Луна сегодня</b>\n\n"
        f"🌙 Фаза: {moon['phase']}\n"
        f"🔭 Знак: <b>{moon['sign']}</b>\n\n"
        f"{text}"
    )

    await message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=b.as_markup(),
    )
