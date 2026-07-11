import hashlib
import logging
import urllib.parse

from aiohttp import web

from config import YOOMONEY_WALLET, YOOMONEY_SECRET
from models.user import grant_premium, get_connection

logger = logging.getLogger(__name__)

_RUBLE_PLANS = {
    "1m":  {"months": 1,  "amount": 200,  "label": "1 месяц"},
    "3m":  {"months": 3,  "amount": 500,  "label": "3 месяца"},
    "6m":  {"months": 6,  "amount": 900,  "label": "6 месяцев"},
    "12m": {"months": 12, "amount": 1500, "label": "12 месяцев"},
}


def get_ruble_plans():
    return _RUBLE_PLANS


def payment_link(plan_key: str, user_id: int) -> str:
    plan = _RUBLE_PLANS[plan_key]
    label = f"premium_{plan_key}_{user_id}"
    params = urllib.parse.urlencode({
        "receiver": YOOMONEY_WALLET,
        "quickpay-form": "button",
        "targets": f"Премиум Злата {plan['label']}",
        "paymentType": "AC",
        "sum": plan["amount"],
        "label": label,
        "successURL": "https://t.me/Zlataesotericbot",
    })
    return f"https://yoomoney.ru/quickpay/confirm.xml?{params}"


async def webhook_handler(request: web.Request) -> web.Response:
    try:
        data = await request.post()
        logger.info("YooMoney webhook: %s", dict(data))

        notification_type = data.get("notification_type", "")
        operation_id = data.get("operation_id", "")
        amount = data.get("amount", "")
        currency = data.get("currency", "")
        dt = data.get("datetime", "")
        sender = data.get("sender", "")
        codepro = data.get("codepro", "false")
        label = data.get("label", "")
        sha1_hash = data.get("sha1_hash", "")

        # Accept test notifications
        if data.get("test_notification") == "true" or operation_id == "test-notification":
            logger.info("YooMoney: test notification accepted")
            return web.Response(text="OK")

        # Verify hash (real notifications use sha1_hash)
        raw = f"{notification_type}&{operation_id}&{amount}&{currency}&{dt}&{sender}&{codepro}&{YOOMONEY_SECRET}&{label}"
        expected = hashlib.sha1(raw.encode("utf-8")).hexdigest()
        if sha1_hash.lower() != expected.lower():
            logger.warning("YooMoney: hash mismatch (got=%s expected=%s)", sha1_hash, expected)
            return web.Response(text="Invalid hash", status=400)

        # Parse label: premium_{key}_{user_id}
        if not label.startswith("premium_"):
            return web.Response(text="Invalid label prefix", status=400)

        parts = label.split("_")
        if len(parts) < 3:
            return web.Response(text="Invalid label format", status=400)

        plan_key = parts[1]
        try:
            user_id = int(parts[2])
        except ValueError:
            return web.Response(text="Invalid user_id in label", status=400)

        plan = _RUBLE_PLANS.get(plan_key)
        if not plan:
            logger.warning("YooMoney: unknown plan key %s", plan_key)
            return web.Response(text="Unknown plan", status=400)

        # amount sanity check
        if abs(float(amount) - plan["amount"]) > 1:
            logger.warning("YooMoney: amount mismatch expected=%s got=%s", plan["amount"], amount)
            return web.Response(text="Amount mismatch", status=400)

        # user must exist
        conn = get_connection()
        exists = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()
        if not exists:
            logger.warning("YooMoney: user %s not found", user_id)
            return web.Response(text="User not found", status=404)

        end = grant_premium(user_id, plan["months"])
        logger.info("YooMoney: premium %s -> %s (%s months, until %s)", user_id, plan_key, plan["months"], end)
        return web.Response(text="OK")
    except Exception as e:
        logger.error("YooMoney webhook error: %s", e, exc_info=True)
        return web.Response(text="Internal error", status=500)


def create_webhook_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/yoomoney", webhook_handler)
    return app
