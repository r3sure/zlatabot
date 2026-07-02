from datetime import datetime
from kerykeion import AstrologicalSubject

ZODIAC_SIGNS_RU = {
    "Ari": "Овен", "Tau": "Телец", "Gem": "Близнецы",
    "Can": "Рак", "Leo": "Лев", "Vir": "Дева",
    "Lib": "Весы", "Sco": "Скорпион", "Sag": "Стрелец",
    "Cap": "Козерог", "Aqu": "Водолей", "Pis": "Рыбы",
}

SIGN_PREPOSITIONAL = {
    "Овен": "Овне", "Телец": "Тельце", "Близнецы": "Близнецах",
    "Рак": "Раке", "Лев": "Льве", "Дева": "Деве",
    "Весы": "Весах", "Скорпион": "Скорпионе", "Стрелец": "Стрельце",
    "Козерог": "Козероге", "Водолей": "Водолее", "Рыбы": "Рыбах",
}

SIGN_GENITIVE = {
    "Овен": "Овна", "Телец": "Тельца", "Близнецы": "Близнецов",
    "Рак": "Рака", "Лев": "Льва", "Дева": "Девы",
    "Весы": "Весов", "Скорпион": "Скорпиона", "Стрелец": "Стрельца",
    "Козерог": "Козерога", "Водолей": "Водолея", "Рыбы": "Рыб",
}

SIGN_DATIVE = {
    "Овен": "Овну", "Телец": "Тельцу", "Близнецы": "Близнецам",
    "Рак": "Раку", "Лев": "Льву", "Дева": "Деве",
    "Весы": "Весам", "Скорпион": "Скорпиону", "Стрелец": "Стрельцу",
    "Козерог": "Козерогу", "Водолей": "Водолею", "Рыбы": "Рыбам",
}

MOON_PHASES_RU = {
    "New Moon": "Новолуние",
    "Waxing Crescent": "Растущий серп",
    "First Quarter": "Первая четверть",
    "Waxing Gibbous": "Растущая Луна",
    "Full Moon": "Полнолуние",
    "Waning Gibbous": "Убывающая Луна",
    "Last Quarter": "Последняя четверть",
    "Waning Crescent": "Убывающий серп",
}


SEASONS_RU = {1: "зима", 2: "зима", 3: "весна", 4: "весна",
              5: "весна", 6: "лето", 7: "лето", 8: "лето",
              9: "осень", 10: "осень", 11: "осень", 12: "зима"}

DAYS_RU = ["понедельник", "вторник", "среда", "четверг",
           "пятница", "суббота", "воскресенье"]


def _now_subject():
    now = datetime.utcnow()
    return AstrologicalSubject(
        "Now", now.year, now.month, now.day,
        now.hour, now.minute,
        lng=37.62, lat=55.75,
        tz_str="Europe/Moscow",
        online=False,
    )


def get_moon_info() -> dict:
    s = _now_subject()
    phase_name = s.lunar_phase.moon_phase_name
    moon_sign = s.moon.sign
    sign_ru = ZODIAC_SIGNS_RU.get(moon_sign, moon_sign)
    return {
        "emoji": s.lunar_phase.moon_emoji,
        "phase": MOON_PHASES_RU.get(phase_name, phase_name),
        "phase_en": phase_name,
        "sign": sign_ru,
        "sign_prep": SIGN_PREPOSITIONAL.get(sign_ru, sign_ru),
        "sign_en": moon_sign,
    }


def get_horoscope_data() -> dict:
    s = _now_subject()
    m = s.model()
    planets = []
    for p in [m.sun, m.moon, m.mercury, m.venus, m.mars,
              m.jupiter, m.saturn, m.uranus, m.neptune, m.pluto]:
        planets.append({
            "name": p.name,
            "sign": ZODIAC_SIGNS_RU.get(p.sign, p.sign),
            "house": p.house,
        })
    return {
        "planets": planets,
        "ascendant": m.ascendant,
    }


def get_planets_summary() -> str:
    data = get_horoscope_data()
    return ", ".join(f"{p['name']} в знаке {p['sign']}" for p in data["planets"])


def get_daily_context() -> dict:
    now = datetime.now()
    moon = get_moon_info()
    return {
        "day_of_week": DAYS_RU[now.weekday()],
        "season": SEASONS_RU[now.month],
        "date": now.strftime("%d.%m.%Y"),
        "moon_phase": moon["phase"],
        "moon_sign": moon["sign"],
        "planets": get_planets_summary(),
    }
