import asyncio
from datetime import date

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.ai import generate_text
from services.astrology import ZODIAC_SIGNS_RU
from models.user import get_connection, has_premium_access

router = Router()

SIGN_LIST = list(ZODIAC_SIGNS_RU.items())
COMPAT_LIMIT = 2


class CompatForm(StatesGroup):
    sign1 = State()
    name1 = State()
    age1 = State()
    day1 = State()
    month1 = State()
    sign2 = State()
    name2 = State()
    age2 = State()
    day2 = State()
    month2 = State()


def _signs_kb(prefix: str, exclude: str = ""):
    b = InlineKeyboardBuilder()
    for code, name in SIGN_LIST:
        if code == exclude:
            continue
        b.button(text=name, callback_data=f"{prefix}_{code}")
    b.adjust(3)
    return b.as_markup()


def _user_compat_count(user_id: int) -> int:
    today = str(date.today())
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM readings WHERE user_id = ? AND type = 'compat' AND date(created_at) = ?",
        (user_id, today),
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


def _save_compat(user_id: int, data: dict, text: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO readings (user_id, type, cards, interpretation) VALUES (?, ?, ?, ?)",
        (user_id, "compat", str(data), text),
    )
    conn.commit()
    conn.close()


@router.message(Command("compatibility"))
async def cmd_compat(message: Message, state: FSMContext):
    user_id = message.chat.id
    used = _user_compat_count(user_id)
    if not has_premium_access(user_id) and used >= COMPAT_LIMIT:
        await message.answer(
            "💫 На сегодня лимит бесплатных проверок совместимости исчерпан "
            "(2/2). Возвращайся завтра или оформи премиум!"
        )
        return

    remaining = "∞" if has_premium_access(user_id) else str(COMPAT_LIMIT - used)
    await state.set_state(CompatForm.sign1)
    await message.answer(
        "💫 <b>Совместимость</b>\n\n"
        "Простой разбор по знакам, имени и возрасту.\n"
        "Хочешь настоящую астрологию? 🙌\n"
        "💞 <b>Глубокая совместимость</b> — синастрия по натальным картам, "
        "реальные планетные аспекты. Доступна в меню 🔽\n\n"
        f"Осталось проверок сегодня: {remaining}\n\n"
        "<b>Шаг 1 из 2</b> — расскажи о первом человеке.\n"
        "Выбери его знак зодиака:",
        reply_markup=_signs_kb("compat1"),
    )


@router.callback_query(F.data.startswith("compat1_"))
async def compat_sign1(callback: CallbackQuery, state: FSMContext):
    code1 = callback.data.split("_", 1)[1]
    await state.update_data(sign1_code=code1, sign1_name=ZODIAC_SIGNS_RU.get(code1, code1))
    await state.set_state(CompatForm.name1)
    await callback.message.edit_text(
        f"Знак: <b>{ZODIAC_SIGNS_RU.get(code1, code1)}</b>\n\n"
        "Как зовут этого человека?"
    )
    await callback.answer()


@router.message(CompatForm.name1)
async def compat_name1(message: Message, state: FSMContext):
    await state.update_data(name1=message.text.strip())
    await state.set_state(CompatForm.age1)
    await message.answer("Сколько ему/ей лет? Напиши число.")


@router.message(CompatForm.age1)
async def compat_age1(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Напиши возраст числом, например: 25")
        return
    await state.update_data(age1=text)
    await state.set_state(CompatForm.day1)
    await message.answer("Какого числа он/она родился? (1–31)")


@router.message(CompatForm.day1)
async def compat_day1(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or not (1 <= int(text) <= 31):
        await message.answer("Напиши число от 1 до 31.")
        return
    await state.update_data(day1=text)
    await state.set_state(CompatForm.month1)
    await message.answer("Какого месяца? Напиши номер (1–12) или название.")


MONTHS_NOM = {
    "1": "январь", "2": "февраль", "3": "март", "4": "апрель",
    "5": "май", "6": "июнь", "7": "июль", "8": "август",
    "9": "сентябрь", "10": "октябрь", "11": "ноябрь", "12": "декабрь",
}
MONTHS_GEN = {
    "1": "января", "2": "февраля", "3": "марта", "4": "апреля",
    "5": "мая", "6": "июня", "7": "июля", "8": "августа",
    "9": "сентября", "10": "октября", "11": "ноября", "12": "декабря",
}
_MONTH_ALIASES = {}
for k, nom in MONTHS_NOM.items():
    _MONTH_ALIASES[nom] = k
for k, gen in MONTHS_GEN.items():
    _MONTH_ALIASES[gen] = k
# Short 3-letter forms
for k, nom in MONTHS_NOM.items():
    _MONTH_ALIASES[nom[:3]] = k


def _parse_month(text: str) -> str | None:
    """Return month number ('1'..'12') or None."""
    # Already a number
    if text in MONTHS_NOM:
        return text
    # Zero-padded number
    if len(text) == 2 and text[0] == "0":
        stripped = text.lstrip("0") or "0"
        if stripped in MONTHS_NOM:
            return stripped
    # Try to parse as int
    try:
        n = int(text)
        if 1 <= n <= 12:
            return str(n)
    except ValueError:
        pass
    # Look up in aliases (nom, gen, short)
    return _MONTH_ALIASES.get(text)


@router.message(CompatForm.month1)
async def compat_month1(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    month_num = _parse_month(text)
    if not month_num:
        await message.answer("Не поняла месяц. Напиши номер (1–12) или название.")
        return
    await state.update_data(month1=MONTHS_GEN[month_num])
    await state.set_state(CompatForm.sign2)
    await message.answer(
        f"Отлично! Запомнила.\n\n"
        "<b>Шаг 2 из 2</b> — теперь расскажи о втором человеке.\n"
        "Выбери его знак зодиака:",
        reply_markup=_signs_kb("compat2"),
    )


@router.callback_query(F.data.startswith("compat2_"))
async def compat_sign2(callback: CallbackQuery, state: FSMContext):
    code2 = callback.data.split("_", 1)[1]
    await state.update_data(sign2_code=code2, sign2_name=ZODIAC_SIGNS_RU.get(code2, code2))
    await state.set_state(CompatForm.name2)
    await callback.message.edit_text(
        f"Знак: <b>{ZODIAC_SIGNS_RU.get(code2, code2)}</b>\n\n"
        "Как зовут этого человека?"
    )
    await callback.answer()


@router.message(CompatForm.name2)
async def compat_name2(message: Message, state: FSMContext):
    await state.update_data(name2=message.text.strip())
    await state.set_state(CompatForm.age2)
    await message.answer("Сколько ему/ей лет?")


@router.message(CompatForm.age2)
async def compat_age2(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Напиши возраст числом.")
        return
    await state.update_data(age2=text)
    await state.set_state(CompatForm.day2)
    await message.answer("Какого числа он/она родился? (1–31)")


@router.message(CompatForm.day2)
async def compat_day2(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or not (1 <= int(text) <= 31):
        await message.answer("Напиши число от 1 до 31.")
        return
    await state.update_data(day2=text)
    await state.set_state(CompatForm.month2)
    await message.answer("Какого месяца? (1–12 или название)")


@router.message(CompatForm.month2)
async def compat_month2(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    month_num = _parse_month(text)
    if not month_num:
        await message.answer("Не поняла месяц. Напиши номер (1–12) или название.")
        return
    await state.update_data(month2=MONTHS_GEN[month_num])

    data = await state.get_data()
    await state.clear()

    msg = await message.answer(f"💫 Рассчитываю совместимость <b>{data['name1']}</b> и <b>{data['name2']}</b>...")

    prompt = (
        f"Ты — астролог Злата. Сделай подробный разбор совместимости двух людей.\n\n"
        f"Человек 1:\n"
        f"  Имя: {data['name1']}\n"
        f"  Знак: {data['sign1_name']}\n"
        f"  Возраст: {data['age1']}\n"
        f"  День рождения: {data['day1']} {data['month1']}\n\n"
        f"Человек 2:\n"
        f"  Имя: {data['name2']}\n"
        f"  Знак: {data['sign2_name']}\n"
        f"  Возраст: {data['age2']}\n"
        f"  День рождения: {data['day2']} {data['month2']}\n\n"
        f"Формат ответа (строго соблюдай):\n"
        f"💕 Общая совместимость (2-3 предложения)\n"
        f"🔥 Что их объединяет (2 предложения)\n"
        f"💔 Что может мешать (2 предложения)\n"
        f"💫 Совет для пары (1-2 предложения)\n\n"
        f"Пиши в женском роде, тепло и вдохновляюще. Без подписи."
    )

    try:
        text = await asyncio.to_thread(generate_text, prompt)
    except Exception:
        text = (
            f"💕 Общая совместимость: {data['name1']} и {data['name2']} — "
            f"интересное сочетание, полное взаимного притяжения.\n"
            f"🔥 Что их объединяет: вы способны вдохновлять друг друга "
            f"на новые свершения.\n"
            f"💔 Что может мешать: иногда вам сложно понять "
            f"чувства партнёра.\n"
            f"💫 Совет для пары: доверяйте своей интуиции "
            f"и говорите друг с другом открыто."
        )

    _save_compat(message.chat.id, data, text)

    b = InlineKeyboardBuilder()
    b.button(text="🔄 Ещё пару", callback_data="compat_again")
    b.button(text="💞 Хочу глубже", callback_data="menu_deep_compat")
    b.button(text="📋 Меню", callback_data="menu_main")
    b.adjust(1)
    await msg.edit_text(
        f"💫 <b>Совместимость</b>\n\n"
        f"{data['name1']} ({data['sign1_name']}, {data['age1']} лет, "
        f"род. {data['day1']} {data['month1']})\n"
        f"{data['name2']} ({data['sign2_name']}, {data['age2']} лет, "
        f"род. {data['day2']} {data['month2']})\n\n"
        f"{text}",
        reply_markup=b.as_markup(),
    )


@router.callback_query(F.data == "compat_again")
async def compat_again(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not has_premium_access(user_id):
        used = _user_compat_count(user_id)
        if used >= COMPAT_LIMIT:
            await callback.message.answer(
                "💫 На сегодня лимит бесплатных проверок исчерпан (2/2). "
                "Возвращайся завтра или оформи премиум!"
            )
            await callback.answer()
            return

    await callback.message.answer(
        "💫 <b>Новая проверка совместимости</b>\n\n"
        "Выбери знак первого человека:",
        reply_markup=_signs_kb("compat1"),
    )
    await callback.answer()
