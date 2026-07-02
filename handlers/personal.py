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
from models.user import is_premium, has_premium_access

router = Router()


class DeepCompatForm(StatesGroup):
    name = State()
    birth_date = State()
    birth_time = State()


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


@router.message(Command("deep_compat"))
async def cmd_deep_compat(message: Message, state: FSMContext):
    user_id = message.chat.id
    if not has_premium_access(user_id):
        data = get_natal_data(user_id)
        if not data:
            b = InlineKeyboardBuilder()
            b.button(text="👤 Заполнить профиль", callback_data="menu_profile")
            b.button(text="📋 Меню", callback_data="menu_main")
            await message.answer(
                "💫 <b>Глубокая совместимость</b>\n\n"
                "Синастрический анализ на основе натальных карт обоих партнёров. "
                "Доступен подписчикам 💎\n\n"
                "Заполни свой профиль, чтобы получить возможность "
                "анализировать отношения на уровне планет ✨",
                reply_markup=b.as_markup(),
            )
            return
        b = InlineKeyboardBuilder()
        b.button(text="💎 Оформить подписку", callback_data="menu_profile")
        b.button(text="📋 Меню", callback_data="menu_main")
        await message.answer(
            "💫 <b>Глубокая совместимость</b>\n\n"
            "Синастрический анализ на основе натальных карт обоих партнёров:\n"
            "— Планетные аспекты между вашими картами\n"
            "— Эмоциональная, интеллектуальная и физическая совместимость\n"
            "— Сильные стороны и зоны роста\n\n"
            "Доступно подписчикам 💎\n"
            "А пока попробуй обычную совместимость по знакам зодиака!",
            reply_markup=b.as_markup(),
        )
        return

    data = get_natal_data(user_id)
    if not data:
        b = InlineKeyboardBuilder()
        b.button(text="👤 Заполнить профиль", callback_data="menu_profile")
        b.button(text="📋 Меню", callback_data="menu_main")
        await message.answer(
            "💫 <b>Глубокая совместимость</b>\n\n"
            "Чтобы я могла построить синастрию, нужна твоя натальная карта. "
            "Заполни дату рождения в профиле!",
            reply_markup=b.as_markup(),
        )
        return

    await message.answer(
        "💫 <b>Глубокая совместимость</b>\n\n"
        "Расскажи о человеке, с которым хочешь проверить совместимость.\n\n"
        "Как его зовут?"
    )
    await state.set_state(DeepCompatForm.name)


@router.message(DeepCompatForm.name)
async def deep_compat_name(message: Message, state: FSMContext):
    await state.update_data(partner_name=message.text.strip())
    await state.set_state(DeepCompatForm.birth_date)
    await message.answer(
        "Введи его дату рождения в формате <b>ДД.ММ.ГГГГ</b>\n"
        "Например: <code>15.03.1992</code>"
    )


@router.message(DeepCompatForm.birth_date)
async def deep_compat_birth(message: Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        await message.answer("Неверный формат. Напиши как <code>15.03.1992</code>")
        return
    d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
    if not (1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= 2100):
        await message.answer("Дата выглядит нереальной. Попробуй ещё раз.")
        return
    await state.update_data(partner_birth=text)

    b = InlineKeyboardBuilder()
    b.button(text="12:00 (не знаю)", callback_data="deep_time_skip")
    b.button(text="Введу время", callback_data="deep_time_enter")
    await state.set_state(DeepCompatForm.birth_time)
    await message.answer(
        "Знаешь время рождения? Мне хватит примерно.\n"
        "Если не знаешь — поставлю полдень.",
        reply_markup=b.as_markup(),
    )


@router.callback_query(F.data == "deep_time_skip", DeepCompatForm.birth_time)
async def deep_compat_time_skip(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(partner_time="12:00")
    await _run_deep_compat(callback.message, state)


@router.callback_query(F.data == "deep_time_enter", DeepCompatForm.birth_time)
async def deep_compat_time_ask(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "Напиши время в формате <b>ЧЧ:ММ</b>\nНапример: <code>14:30</code>"
    )


@router.message(DeepCompatForm.birth_time)
async def deep_compat_time(message: Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split(":")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        h, m = int(parts[0]), int(parts[1])
        if 0 <= h <= 23 and 0 <= m <= 59:
            await state.update_data(partner_time=text)
            await _run_deep_compat(message, state)
            return
    await message.answer("Неверный формат. Напиши как <code>14:30</code>")


async def _run_deep_compat(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    msg = await message.answer(
        f"💫 Рассчитываю синастрию с <b>{data['partner_name']}</b>..."
    )
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(2)

    text = await generate_deep_compatibility(
        message.chat.id,
        data["partner_name"],
        data["partner_birth"],
        data.get("partner_time", "12:00"),
    )
    await msg.delete()

    b = InlineKeyboardBuilder()
    b.button(text="📋 Меню", callback_data="menu_main")
    await message.answer(
        f"💫 <b>Глубокая совместимость</b>\n\n"
        f"С кем: {data['partner_name']} ({data['partner_birth']})\n\n"
        f"{text}",
        reply_markup=b.as_markup(),
    )


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
