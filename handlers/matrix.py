from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from services.matrix import calculate_matrix
from services.personal_astro import get_natal_data

router = Router()


class MatrixForm(StatesGroup):
    waiting_date = State()


def _format_result(day: int, month: int, year: int) -> str:
    positions = calculate_matrix(day, month, year)
    lines = []
    for p in positions:
        lines.append(
            f"<b>{p['arcana']}. {p['name']}</b> — {p['position']}, {p['meaning']}\n"
            f"{p['description']}"
        )
    return (
        "✨ <b>Твоя Матрица Судьбы</b>\n\n"
        + "\n\n".join(lines)
        + "\n\n🌟 Это твои энергии на данный момент. "
        "Помни: арканы — не приговор, а подсказки. "
        "Что откликается — то твоё."
    )


@router.message(Command("myid"))
async def cmd_myid(message: Message):
    await message.answer(
        f"👤 Твой from_user.id: <code>{message.from_user.id}</code>\n"
        f"💬 chat.id: <code>{message.chat.id}</code>\n"
        f"🤖 bot.id: <code>{message.bot.id}</code>"
    )


@router.message(Command("matrix"))
async def cmd_matrix(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = get_natal_data(user_id)
    if data:
        bd = data["birth_date"]
        day, month, year = map(int, bd.split("."))
        await message.answer(_format_result(day, month, year))
        return

    await state.set_state(MatrixForm.waiting_date)
    await message.answer(
        "✨ <b>Матрица Судьбы</b>\n\n"
        "У тебя ещё не заполнен профиль.\n"
        "Напиши дату рождения в формате <b>ДД.ММ.ГГГГ</b>,\n"
        "я рассчитаю матрицу по 22 арканам."
    )


@router.message(MatrixForm.waiting_date, F.text)
async def handle_date(message: Message, state: FSMContext):
    text = message.text.strip()
    parts = text.replace(".", " ").replace("/", " ").replace("-", " ").split()
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        await message.answer(
            "Формат не подходит. Напиши дату так: <b>ДД.ММ.ГГГГ</b>\n"
            "Например: <b>15.03.1992</b>"
        )
        return

    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
    if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
        await message.answer("Дата выглядит неверно. Проверь и попробуй ещё раз.")
        return

    await state.clear()
    await message.answer(_format_result(day, month, year))


@router.callback_query(F.data == "menu_matrix")
async def callback_matrix(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await cmd_matrix(callback.message, state)
