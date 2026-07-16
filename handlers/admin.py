import asyncio
import io
import sys
import traceback

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from config import ADMIN_IDS
from models.user import grant_premium, get_connection

router = Router()


def _is_admin(msg: Message) -> bool:
    return msg.chat.id in ADMIN_IDS


@router.message(Command("grant"))
async def cmd_grant(message: Message, command: CommandObject):
    if not _is_admin(message):
        return
    args = command.args
    if not args:
        await message.answer("Формат: /grant <user_id> <months>")
        return
    parts = args.strip().split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await message.answer("Формат: /grant <user_id> <months>")
        return
    uid, months = int(parts[0]), int(parts[1])
    end = grant_premium(uid, months)
    await message.answer(f"✅ Премиум {months} мес. → {uid} до {end[:10]}")



@router.message(Command("users"))
async def cmd_users(message: Message):
    if not _is_admin(message):
        return
    conn = get_connection()
    rows = conn.execute(
        "SELECT user_id, name, subscription_status, created_at FROM users ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    if not rows:
        await message.answer("Пользователей нет")
        return
    lines = [
        f"{r['user_id']} | {r['name'] or '—'} | "
        f"{r['subscription_status'] or 'free'} | "
        f"{r['created_at'][:10] if r['created_at'] else '—'}"
        for r in rows
    ]
    await message.answer("📋 <b>Пользователи:</b>\n\n" + "\n".join(lines[:30]))


@router.message(Command("userinfo"))
async def cmd_userinfo(message: Message, command: CommandObject):
    if not _is_admin(message):
        return
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Формат: /userinfo <user_id>")
        return
    uid = int(command.args.strip())
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE user_id = ?", (uid,)
    ).fetchone()
    if not row:
        conn.close()
        await message.answer(f"❌ Пользователь {uid} не найден.")
        return
    kv = dict(row)
    conn.close()
    text = "\n".join(f"<b>{k}:</b> {v}" for k, v in kv.items() if v)
    await message.answer(f"📋 <b>Инфо {uid}:</b>\n\n{text}")


@router.message(Command("refund"))
async def cmd_refund(message: Message, command: CommandObject):
    if not _is_admin(message):
        return
    args = command.args
    if not args:
        await message.answer("Формат: /refund <user_id> [причина]")
        return
    parts = args.strip().split(maxsplit=1)
    if not parts[0].isdigit():
        await message.answer("Формат: /refund <user_id> [причина]")
        return
    uid = int(parts[0])
    reason = parts[1] if len(parts) > 1 else "—"
    conn = get_connection()
    conn.execute("UPDATE users SET subscription_end = NULL, subscription_status = 'free' WHERE user_id = ?", (uid,))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Возврат для {uid}. Причина: {reason}")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, command: CommandObject):
    if not _is_admin(message):
        return
    text = command.args
    if not text:
        await message.answer("Формат: /broadcast <текст>")
        return

    bot = message.bot
    conn = get_connection()
    uids = [r[0] for r in conn.execute("SELECT user_id FROM users").fetchall()]
    conn.close()

    ok = fail = 0
    status = await message.answer(f"📨 Рассылка {len(uids)} пользователям...")
    for uid in uids:
        try:
            await bot.send_message(uid, text, disable_notification=True)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
    await status.edit_text(f"✅ Разослано: {ok}, ошибок: {fail}")


@router.message(Command("exec"))
async def cmd_exec(message: Message, command: CommandObject):
    if not _is_admin(message):
        return
    code = command.args
    if not code:
        await message.answer("Формат: /exec <python_code>")
        return

    old_stdout = sys.stdout
    sys.stdout = captured = io.StringIO()
    try:
        exec(code, {"__builtins__": __builtins__, "message": message})
        result = captured.getvalue() or "✅ OK (no output)"
    except Exception:
        result = traceback.format_exc()
    finally:
        sys.stdout = old_stdout

    if len(result) > 3000:
        result = result[:3000] + "\n\n... (truncated)"
    await message.answer(f"<b>Результат:</b>\n<code>{result}</code>")
