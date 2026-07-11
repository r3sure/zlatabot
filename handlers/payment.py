from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import YOOMONEY_WALLET
from handlers.menu import main_menu_kb
from models.user import grant_premium, is_premium, get_connection, was_deleted
from services.yoomoney import get_ruble_plans, payment_link

router = Router()

PLANS = {
    "1m": {"label": "1 месяц", "stars": 150, "months": 1},
    "3m": {"label": "3 месяца", "stars": 375, "months": 3},
    "6m": {"label": "6 месяцев", "stars": 750, "months": 6},
    "12m": {"label": "12 месяцев", "stars": 1400, "months": 12},
}
RUBLE_PLANS = get_ruble_plans()


@router.message(Command("buy"))
async def cmd_buy(message: Message):
    uid = message.chat.id
    if was_deleted(uid):
        await message.answer(
            "Твой аккаунт был удалён. Если хочешь восстановиться — напиши /start",
            reply_markup=main_menu_kb(),
        )
        return
    if is_premium(uid):
        conn = get_connection()
        row = conn.execute(
            "SELECT subscription_end FROM users WHERE user_id = ?", (uid,)
        ).fetchone()
        conn.close()
        end = row["subscription_end"][:10] if row and row["subscription_end"] else "—"
        header = f"💎 У тебя уже есть премиум до <b>{end}</b>!\nМожешь продлить или увеличить срок:\n\n"
    else:
        header = ""

    b = InlineKeyboardBuilder()
    for key, plan in PLANS.items():
        b.button(
            text=f"{plan['label']} — {plan['stars']} ⭐",
            callback_data=f"buy_{key}",
        )
    if YOOMONEY_WALLET:
        b.button(text="💳 Оплатить рублями", callback_data="buy_ruble_menu")
    b.button(text="↩️ Назад", callback_data="menu_main")
    b.adjust(1)

    await message.answer(
        f"{header}"
        "💎 <b>Премиум-подписка</b>\n\n"
        "Открой все возможности Златы:\n\n"
        "🔮 Расклад на 7 карт\n"
        "📅 Прогноз на месяц\n"
        "💞 Глубокая совместимость\n"
        "🟢 Благоприятные дни\n"
        "🌙 Сны без лимита\n"
        "💬 Чат без ограничений\n"
        "🔮 Расклады с выбором позиций\n\n"
        "Выбери способ оплаты:",
        reply_markup=b.as_markup(),
    )


@router.callback_query(F.data == "buy_ruble_menu")
async def buy_ruble_menu(callback: CallbackQuery):
    await callback.answer()
    b = InlineKeyboardBuilder()
    for key, plan in RUBLE_PLANS.items():
        b.button(text=f"{plan['label']} — {plan['amount']}₽", callback_data=f"rpay_{key}")
    b.button(text="↩️ Назад", callback_data="menu_buy")
    b.adjust(1)
    await callback.message.edit_text(
        "💎 <b>Премиум — оплата рублями</b>\n\n"
        "После оплаты премиум активируется автоматически.",
        reply_markup=b.as_markup(),
    )


@router.callback_query(F.data.startswith("rpay_"))
async def buy_ruble(callback: CallbackQuery):
    await callback.answer()
    key = callback.data.split("_", 1)[1]
    plan = RUBLE_PLANS.get(key)
    if not plan:
        await callback.answer("План не найден")
        return

    uid = callback.from_user.id
    link = payment_link(key, uid)

    b = InlineKeyboardBuilder()
    b.button(text=f"💳 Оплатить {plan['amount']}₽", url=link)
    b.button(text="↩️ Назад", callback_data="buy_ruble_menu")
    b.adjust(1)

    await callback.message.edit_text(
        f"💎 <b>Премиум — {plan['label']}</b>\n\n"
        f"Стоимость: <b>{plan['amount']}₽</b>\n\n"
        f"После оплаты премиум активируется автоматически.",
        reply_markup=b.as_markup(),
    )


@router.callback_query(F.data.startswith("buy_"))
async def buy_plan(callback: CallbackQuery):
    key = callback.data.split("_", 1)[1]
    plan = PLANS.get(key)
    if not plan:
        await callback.answer("План не найден")
        return

    await callback.answer()

    b = InlineKeyboardBuilder()
    b.button(text=f"⭐ {plan['stars']} Stars", callback_data=f"pay_{key}")
    if YOOMONEY_WALLET:
        b.button(text=f"💵 {RUBLE_PLANS[key]['amount']}₽", callback_data=f"rpay_{key}")
    b.button(text="↩️ Назад", callback_data="menu_buy")
    b.adjust(2, 1)

    await callback.message.edit_text(
        f"💎 <b>Премиум — {plan['label']}</b>\n\n"
        f"Срок: <b>{plan['label']}</b>\n"
        f"Выбери способ оплаты:",
        reply_markup=b.as_markup(),
    )


@router.callback_query(F.data.startswith("pay_"))
async def pay_plan(callback: CallbackQuery):
    key = callback.data.split("_", 1)[1]
    plan = PLANS.get(key)
    if not plan:
        await callback.answer("План не найден")
        return

    uid = callback.from_user.id
    payload = f"premium_{key}_{uid}"
    prices = [LabeledPrice(label=plan["label"], amount=plan["stars"])]

    await callback.message.delete()
    await callback.message.answer_invoice(
        title=f"💎 Премиум — {plan['label']}",
        description=(
            f"Подписка на {plan['label']} ко всем премиум-функциям Златы.\n\n"
            f"После оплаты премиум активируется автоматически."
        ),
        provider_token="",
        currency="XTR",
        prices=prices,
        payload=payload,
    )


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    uid = pre_checkout_query.from_user.id
    payload: str = pre_checkout_query.invoice_payload or ""
    if was_deleted(uid):
        await pre_checkout_query.answer(ok=False, error_message="Аккаунт удалён. Обратись в поддержку.")
        return
    if not any(payload.startswith(f"premium_{key}_{uid}") for key in PLANS):
        await pre_checkout_query.answer(ok=False, error_message="Некорректный платёж.")
        return
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    payment = message.successful_payment
    payload: str = payment.invoice_payload or ""
    uid = message.chat.id

    # Handle star chart payments separately in stars_on.py
    if payload.startswith("stars_"):
        return

    months = 1
    for key, plan in PLANS.items():
        if payload.startswith(f"premium_{key}_{uid}"):
            months = plan["months"]
            break

    end = grant_premium(uid, months)
    try:
        end_dt = datetime.fromisoformat(end)
        end_str = end_dt.strftime("%d.%m.%Y")
    except Exception:
        end_str = end[:10]

    await message.answer(
        f"💎 <b>Премиум активирован!</b>\n\n"
        f"Срок: <b>{months} мес.</b>\n"
        f"Действует до <b>{end_str}</b>\n\n"
        "Спасибо за доверие! Теперь тебе доступно всё ✨\n\n"
        "🌟 <b>Что теперь доступно:</b>\n"
        "🔮 Расклад на 7 карт\n"
        "📅 Прогноз на месяц\n"
        "💞 Глубокая совместимость\n"
        "🟢 Благоприятные дни\n"
        "🌙 Сны без лимита\n"
        "💬 Чат без ограничений",
        reply_markup=main_menu_kb(),
    )
