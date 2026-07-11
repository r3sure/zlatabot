import asyncio
from datetime import date, timedelta

from services.ai import generate_text
from services.astrology import get_daily_context, get_moon_info


def _date_range(days: int = 10) -> list[str]:
    today = date.today()
    return [(today + timedelta(days=i)).strftime("%d.%m.%Y") for i in range(days)]


async def generate_favorable_days(days: int = 10) -> str:
    dates = _date_range(days)
    ctx = get_daily_context()
    moon = get_moon_info()
    dates_str = ", ".join(dates)

    prompt = (
        f"Ты — астролог Злата. Составь календарь благоприятных дней "
        f"на {days} дней: {dates_str}.\n\n"
        f"Астрологическая сводка на сегодня ({ctx['date']}):\n"
        f"- День недели: {ctx['day_of_week']}\n"
        f"- Сезон: {ctx['season']}\n"
        f"- Луна в фазе {ctx['moon_phase']}, в знаке {ctx['moon_sign']}\n"
        f"- Положение планет: {ctx['planets']}\n\n"
        f"Для каждого дня укажи:\n"
        f"📅 <b>ДД.ММ</b> — 🟢 благоприятный / 🟡 нейтральный / 🔴 неблагоприятный\n"
        f"Кратко почему (1 предложение).\n\n"
        f"Пример:\n"
        f"📅 <b>28.06</b> — 🟢 Благоприятный. Луна в Тельце, хороший день для финансовых решений.\n"
        f"📅 <b>29.06</b> — 🟡 Нейтральный. Без особых аспектов.\n\n"
        f"Охвати все {days} дней. В конце добавь совет на период. "
        f"Без подписи."
    )
    try:
        return await generate_text(prompt, temperature=0.8)
    except Exception:
        return "Звёзды пока не готовы открыть карту благоприятных дней. Попробуй позже ✨"
