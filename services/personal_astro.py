import asyncio
from datetime import datetime

from kerykeion import AstrologicalSubject

from services.ai import generate_text
from services.astrology import get_daily_context, get_moon_info, ZODIAC_SIGNS_RU
from models.user import get_connection


def parse_db_date(date_str: str) -> tuple[int, int, int]:
    """Parse birth_date from DB — supports DD.MM.YYYY and YYYY-MM-DD."""
    parts = date_str.replace("-", ".").split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid date: {date_str}")
    if len(parts[0]) == 4:  # YYYY-MM-DD
        return int(parts[2]), int(parts[1]), int(parts[0])
    return int(parts[0]), int(parts[1]), int(parts[2])  # DD.MM.YYYY


def get_natal_data(user_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT name, birth_date, birth_time, birth_city, lat, lng, tz_str, zodiac_sign "
        "FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    if not row or not row["birth_date"]:
        return None
    return dict(row)


def _make_subject(data: dict) -> AstrologicalSubject | None:
    try:
        bd = data["birth_date"]
        bt = data.get("birth_time", "12:00") or "12:00"
        day, month, year = parse_db_date(bd)
        hour, minute = map(int, bt.split(":"))
        return AstrologicalSubject(
            data.get("name", "User"),
            year, month, day, hour, minute,
            lng=data.get("lng", 37.62),
            lat=data.get("lat", 55.75),
            tz_str=data.get("tz_str", "Europe/Moscow"),
            online=False,
        )
    except Exception:
        return None


def _natal_summary(data: dict) -> str:
    s = _make_subject(data)
    if not s:
        return f"Знак: {data.get('zodiac_sign', '—')}, город: {data.get('birth_city', '—')}"
    m = s.model()
    planets = []
    for p in [m.sun, m.moon, m.mercury, m.venus, m.mars,
              m.jupiter, m.saturn, m.uranus, m.neptune, m.pluto]:
        sign_ru = ZODIAC_SIGNS_RU.get(p.sign, p.sign)
        retro = " (ретроградный)" if p.retrograde else ""
        planets.append(f"{p.name} в {sign_ru}{retro}")
    asc_sign_code = getattr(m.ascendant, 'sign', '')
    asc_sign = ZODIAC_SIGNS_RU.get(asc_sign_code, asc_sign_code or '—')
    return f"{data.get('name', 'Пользователь')}, {data['zodiac_sign']}, Асцендент в {asc_sign}\n" + "\n".join(planets)


async def generate_personal_horoscope(user_id: int) -> str:
    data = get_natal_data(user_id)
    if not data:
        return "Нет данных для персонализированного гороскопа. Заполни профиль в /profile"

    natal = _natal_summary(data)
    ctx = get_daily_context()
    prompt = (
        f"Ты — астролог Злата. Составь персонализированный гороскоп на сегодня ({ctx['date']}) "
        f"для этого человека на основе его натальной карты.\n\n"
        f"Натальная карта:\n{natal}\n\n"
        f"Текущая астрологическая обстановка:\n"
        f"- {ctx['day_of_week']}, {ctx['season']}\n"
        f"- Луна в {ctx['moon_phase']}, в знаке {ctx['moon_sign']}\n"
        f"- Планеты: {ctx['planets']}\n\n"
        f"Напиши 5-7 предложений. Свяжи положение планет в натальной карте "
        f"с текущими транзитами. Какие сферы жизни особенно активны сегодня. "
        f"Совет на день. Вдохновляюще, с обращением на «ты». Без подписи."
    )
    try:
        return await asyncio.to_thread(generate_text, prompt, temperature=0.85)
    except Exception:
        return "Звёзды сегодня не спешат открывать карты. Попробуй позже ✨"


async def generate_monthly_forecast(user_id: int) -> str:
    data = get_natal_data(user_id)
    if not data:
        return "Нет данных для прогноза. Заполни профиль в /profile"

    natal = _natal_summary(data)
    from datetime import date, timedelta
    today = date.today()
    months = ["январь", "февраль", "март", "апрель", "май", "июнь",
              "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]
    current_month = months[today.month - 1]
    next_month = months[today.month % 12] if today.month < 12 else months[0]

    prompt = (
        f"Ты — астролог Злата. Составь астрологический прогноз "
        f"на месяц ({current_month}) для этого человека.\n\n"
        f"Натальная карта:\n{natal}\n\n"
        f"Напиши подробный прогноз на месяц (7-10 предложений):\n"
        f"— Какие планеты будут активны в этом месяце и как это влияет на натальную карту\n"
        f"— Какие сферы жизни (карьера, отношения, финансы, здоровье) будут особенно значимы\n"
        f"— Благоприятные и напряжённые периоды в течение месяца\n"
        f"— Рекомендации: что начинать, от чего лучше воздержаться\n"
        f"— Пару благоприятных дней для важных дел\n\n"
        f"Вдохновляюще, с обращением на «ты». Без подписи."
    )
    try:
        return await asyncio.to_thread(generate_text, prompt, temperature=0.85)
    except Exception:
        return "Звёзды пока не готовы открыть карту месяца. Попробуй позже ✨"


async def generate_deep_compatibility(user_id: int, partner_name: str,
                                       partner_birth: str, partner_time: str = "12:00") -> str:
    data = get_natal_data(user_id)
    if not data:
        return "Нет данных. Заполни профиль в /profile"

    natal1 = _natal_summary(data)

    try:
        day, month, year = parse_db_date(partner_birth)
        hour, minute = map(int, partner_time.split(":"))
        subj2 = AstrologicalSubject(
            partner_name, year, month, day, hour, minute,
            lng=37.62, lat=55.75,
            tz_str="Europe/Moscow", online=False,
        )
        m2 = subj2.model()
        planets2 = []
        for p in [m2.sun, m2.moon, m2.mercury, m2.venus, m2.mars,
                  m2.jupiter, m2.saturn]:
            s = ZODIAC_SIGNS_RU.get(p.sign, p.sign)
            retro = " (р)" if p.retrograde else ""
            planets2.append(f"{p.name} в {s}{retro}")
        natal2 = f"{partner_name}, {ZODIAC_SIGNS_RU.get(m2.sun.sign, m2.sun.sign)}\n" + "\n".join(planets2)
    except Exception:
        return "Не удалось построить карту партнёра. Проверь формат даты."

    prompt = (
        f"Ты — астролог Злата. Сделай синастрический анализ совместимости двух людей.\n\n"
        f"Натальная карта пользователя:\n{natal1}\n\n"
        f"Натальная карта партнёра ({partner_name}):\n{natal2}\n\n"
        f"Напиши разбор (7-10 предложений):\n"
        f"— Сильные стороны союза (какие планеты в гармонии)\n"
        f"— Сложные аспекты и зоны роста\n"
        f"— Эмоциональная, интеллектуальная и физическая совместимость\n"
        f"— Итоговая рекомендация\n\n"
        f"С обращением на «ты». Без подписи."
    )
    try:
        return await asyncio.to_thread(generate_text, prompt, temperature=0.8)
    except Exception:
        return "Карты не спешат открывать эту связь. Попробуй позже ✨"
