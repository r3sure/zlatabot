import asyncio
import re

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from handlers.menu import main_menu_kb
from models.user import get_connection, mark_user_deleted
from services.astrology import ZODIAC_SIGNS_RU
from services.natal import resolve_city_coords, validate_city

router = Router()


class EditProfile(StatesGroup):
    field = State()
    value = State()


def _calc_sign_from_date(date_str: str) -> str:
    try:
        parts = date_str.split(".")
        day, month = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return ""
    if (month == 3 and day >= 21) or (month == 4 and day <= 19):
        code = "Ari"
    elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
        code = "Tau"
    elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
        code = "Gem"
    elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
        code = "Can"
    elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
        code = "Leo"
    elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
        code = "Vir"
    elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
        code = "Lib"
    elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
        code = "Sco"
    elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
        code = "Sag"
    elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
        code = "Cap"
    elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
        code = "Aqu"
    else:
        code = "Pis"
    return ZODIAC_SIGNS_RU.get(code, "")


def _get_profile(user_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT name, birth_date, birth_time, birth_city, zodiac_sign, gender, "
        "subscription_status, subscription_end FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    profile = _get_profile(message.chat.id)
    if not profile:
        await message.answer(
            "У тебя ещё нет профиля.\nНапиши /start, чтобы создать.",
            reply_markup=main_menu_kb(),
        )
        return

    sub_status = profile.get("subscription_status", "free")
    sub_end = profile.get("subscription_end", "")

    if sub_status == "premium":
        end_str = sub_end[:10] if sub_end else "—"
        sub_line = f"💎 <b>Премиум</b> (до {end_str})"
    elif sub_status == "trial":
        end_str = sub_end[:10] if sub_end else "—"
        sub_line = f"🎁 <b>Пробный</b> (до {end_str})"
    else:
        sub_line = "🔓 <b>Бесплатный</b>"

    b = InlineKeyboardBuilder()
    b.button(text="✏️ Имя", callback_data="edit_name")
    b.button(text="👤 Пол", callback_data="edit_gender")
    b.button(text="📅 Дата", callback_data="edit_birth_date")
    b.button(text="🕐 Время", callback_data="edit_birth_time")
    b.button(text="🏙️ Город", callback_data="edit_birth_city")
    b.button(text="📖 Мои расклады", callback_data="my_readings")
    b.button(text="💬 История чата", callback_data="my_chat")
    b.button(text="🗑️ Удалить данные", callback_data="delete_data")
    if sub_status == "free":
        b.button(text="💎 Премиум", callback_data="menu_buy")
    b.button(text="📋 Меню", callback_data="menu_main")
    b.adjust(2)

    gender_label = "Мужской" if profile.get("gender") == "male" else "Женский"

    await message.answer(
        f"👤 <b>Твой профиль</b>\n\n"
        f"Имя: {profile['name'] or '—'}\n"
        f"Пол: {gender_label}\n"
        f"Дата рождения: {profile['birth_date'] or '—'}\n"
        f"Знак: {profile['zodiac_sign'] or '—'}\n"
        f"Время рождения: {profile['birth_time'] or '—'}\n"
        f"Город: {profile['birth_city'] or '—'}\n\n"
        f"Статус: {sub_line}\n\n"
        "Что хочешь изменить?",
        reply_markup=b.as_markup(),
    )


EDIT_LABELS = {
    "edit_name": ("name", "Напиши новое имя (или псевдоним):"),
    "edit_gender": ("gender", None),
    "edit_birth_date": ("birth_date", "Напиши новую дату рождения в формате ДД.ММ.ГГГГ:"),
    "edit_birth_time": ("birth_time", "Напиши новое время рождения в формате ЧЧ:ММ:"),
    "edit_birth_city": ("birth_city", "Напиши новый город рождения:"),
}

FIELDS_RU = {
    "name": "Имя",
    "birth_date": "Дата рождения",
    "birth_time": "Время рождения",
    "birth_city": "Город",
}


@router.callback_query(F.data.startswith("edit_"))
async def edit_start(callback: CallbackQuery, state: FSMContext):
    cb = callback.data
    if cb not in EDIT_LABELS:
        await callback.answer("Что-то не так")
        return

    field, question = EDIT_LABELS[cb]

    if field == "gender":
        await state.set_state(EditProfile.field)
        await state.update_data(field=field)
        b = InlineKeyboardBuilder()
        b.button(text="👩 Женский", callback_data="edit_gender_female")
        b.button(text="👨 Мужской", callback_data="edit_gender_male")
        await callback.message.edit_text("Выбери пол:", reply_markup=b.as_markup())
        await callback.answer()
        return

    await state.set_state(EditProfile.field)
    await state.update_data(field=field)
    await callback.message.edit_text(question)
    await callback.answer()


@router.callback_query(F.data.startswith("edit_gender_"), EditProfile.field)
async def edit_gender_cb(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    chosen = callback.data.split("_")[-1]  # "female" or "male"
    uid = callback.from_user.id
    conn = get_connection()
    conn.execute("UPDATE users SET gender = ? WHERE user_id = ?", (chosen, uid))
    conn.commit()
    conn.close()
    await state.clear()
    await callback.message.edit_text(
        f"✅ Пол обновлён!",
        reply_markup=main_menu_kb(),
    )


@router.message(EditProfile.field)
async def edit_value(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data["field"]
    value = message.text.strip()

    if field == "birth_date":
        if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", value):
            await message.answer("Неправильный формат. Напиши как ДД.ММ.ГГГГ")
            return
        sign = _calc_sign_from_date(value)
    else:
        sign = None

    if field == "name" and (not value or len(value) > 50):
        await message.answer("Имя должно быть от 1 до 50 символов.")
        return

    conn = get_connection()

    if field == "birth_city":
        if not validate_city(value):
            await message.answer(
                "🤷 Я не знаю такого города. Попробуй ещё раз."
            )
            return
        coords = resolve_city_coords(value)
        conn.execute(
            "UPDATE users SET birth_city = ?, lat = ?, lng = ?, tz_str = ?, nation = ? WHERE user_id = ?",
            (value, coords["lat"], coords["lng"], coords["tz_str"], coords.get("nation", "RU"), message.chat.id),
        )
    elif field == "birth_date":
        conn.execute(
            "UPDATE users SET birth_date = ?, zodiac_sign = ? WHERE user_id = ?",
            (value, sign, message.chat.id),
        )
    else:
        conn.execute(
            f"UPDATE users SET {field} = ? WHERE user_id = ?",
            (value, message.chat.id),
        )

    conn.commit()
    conn.close()

    await state.clear()
    await message.answer(
        f"✅ {FIELDS_RU.get(field, field)} обновлено!",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "delete_data")
async def delete_confirm(callback: CallbackQuery):
    b = InlineKeyboardBuilder()
    b.button(text="✅ Да, удалить", callback_data="delete_yes")
    b.button(text="❌ Нет, оставить", callback_data="delete_no")
    await callback.message.edit_text(
        "🗑️ <b>Точно удалить все данные?</b>\n\n"
        "Вся твоя информация исчезнет: профиль, история чтений, сны, расклады.\n"
        "Это действие нельзя отменить.",
        reply_markup=b.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "delete_yes")
async def delete_execute(callback: CallbackQuery):
    uid = callback.from_user.id
    conn = get_connection()
    conn.execute("DELETE FROM readings WHERE user_id = ?", (uid,))
    conn.execute("DELETE FROM dreams WHERE user_id = ?", (uid,))
    conn.commit()
    conn.close()
    mark_user_deleted(uid)

    await callback.message.edit_text(
        "✅ Все данные удалены.\n\n"
        "Если захочешь вернуться — напиши /start, и я с радостью встречу тебя заново 💫",
    )
    await callback.answer()


@router.callback_query(F.data == "delete_no")
async def delete_cancel(callback: CallbackQuery):
    await callback.answer("Данные сохранены")
    await cmd_profile(callback.message)


@router.callback_query(F.data == "my_readings")
async def my_readings(callback: CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    conn = get_connection()
    rows = conn.execute(
        "SELECT type, cards, interpretation, created_at FROM readings "
        "WHERE user_id = ? AND type IN ('card', 'spread', 'chat') "
        "ORDER BY created_at DESC LIMIT 10",
        (uid,),
    ).fetchall()
    conn.close()

    if not rows:
        await callback.message.answer(
            "📖 У тебя пока нет сохранённых раскладов.\n"
            "Загляни в 🔮 Таро, чтобы сделать первый!",
            reply_markup=main_menu_kb(),
        )
        return

    lines = []
    for r in rows:
        t = r["type"]
        label = {"card": "🃏 Карта дня", "spread": "🔮 Расклад", "chat": "💬 Чат"}.get(t, t)
        date_str = r["created_at"][:10] if r["created_at"] else ""
        lines.append(f"{label} — {date_str}")
    text = "📖 <b>Последние расклады</b>\n\n" + "\n".join(lines)

    b = InlineKeyboardBuilder()
    b.button(text="📋 Меню", callback_data="menu_main")
    await callback.message.answer(text, reply_markup=b.as_markup())


@router.callback_query(F.data == "my_chat")
async def my_chat(callback: CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    conn = get_connection()
    row = conn.execute(
        "SELECT interpretation, created_at FROM readings "
        "WHERE user_id = ? AND type = 'chat' "
        "ORDER BY created_at DESC LIMIT 1",
        (uid,),
    ).fetchone()
    conn.close()

    if not row or not row["interpretation"]:
        await callback.message.answer(
            "💬 У тебя пока нет истории чата со Златой.\n"
            "Напиши /chat, чтобы начать разговор!",
            reply_markup=main_menu_kb(),
        )
        return

    import json
    try:
        history = json.loads(row["interpretation"])
    except Exception:
        history = []

    if not history:
        await callback.message.answer("💬 История чата пуста.", reply_markup=main_menu_kb())
        return

    # Show last 6 exchanges
    recent = history[-12:]  # 6 exchanges = 12 messages
    lines = []
    for msg in recent:
        role = "👤 Ты" if msg["role"] == "user" else "🌟 Злата"
        content = msg["content"][:80] + ("..." if len(msg["content"]) > 80 else "")
        lines.append(f"{role}: {content}")

    text = "💬 <b>Последние сообщения из чата</b>\n\n" + "\n\n".join(lines[-8:])

    b = InlineKeyboardBuilder()
    b.button(text="💬 Продолжить чат", callback_data="menu_chat")
    b.button(text="📋 Меню", callback_data="menu_main")
    b.adjust(1)
    await callback.message.answer(text, reply_markup=b.as_markup())
