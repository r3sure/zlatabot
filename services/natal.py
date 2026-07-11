import re
from datetime import datetime

from kerykeion import AstrologicalSubject, KerykeionChartSVG
from playwright.async_api import async_playwright

from models.user import get_connection
from services.astrology import ZODIAC_SIGNS_RU

CHARTS_DIR = __import__("config").BASE_DIR / "assets" / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_LNG = 37.62
DEFAULT_LAT = 55.75

CITY_COORDS = {
    # === RUSSIA ===
    "москва": (37.62, 55.75, "Europe/Moscow", "RU"),
    "санкт-петербург": (30.31, 59.94, "Europe/Moscow", "RU"),
    "новосибирск": (82.92, 55.03, "Asia/Novosibirsk", "RU"),
    "екатеринбург": (60.61, 56.84, "Asia/Yekaterinburg", "RU"),
    "казань": (49.12, 55.79, "Europe/Moscow", "RU"),
    "нижний новгород": (44.00, 56.33, "Europe/Moscow", "RU"),
    "челябинск": (61.40, 55.15, "Asia/Yekaterinburg", "RU"),
    "самара": (50.15, 53.20, "Europe/Samara", "RU"),
    "омск": (73.37, 54.99, "Asia/Omsk", "RU"),
    "ростов-на-дону": (39.72, 47.24, "Europe/Moscow", "RU"),
    "уфа": (55.97, 54.74, "Asia/Yekaterinburg", "RU"),
    "красноярск": (92.79, 56.01, "Asia/Krasnoyarsk", "RU"),
    "воронеж": (39.20, 51.67, "Europe/Moscow", "RU"),
    "пермь": (56.23, 58.01, "Asia/Yekaterinburg", "RU"),
    "волгоград": (44.52, 48.71, "Europe/Moscow", "RU"),
    "краснодар": (38.97, 45.04, "Europe/Moscow", "RU"),
    "саратов": (46.03, 51.53, "Europe/Saratov", "RU"),
    "тюмень": (65.53, 57.15, "Asia/Yekaterinburg", "RU"),
    "астрахань": (48.04, 46.35, "Europe/Astrakhan", "RU"),
    "владивосток": (131.87, 43.11, "Asia/Vladivostok", "RU"),
    "ижевск": (53.20, 56.85, "Europe/Samara", "RU"),
    "ульяновск": (48.40, 54.33, "Europe/Ulyanovsk", "RU"),
    "барнаул": (83.77, 53.35, "Asia/Barnaul", "RU"),
    "иркутск": (104.30, 52.28, "Asia/Irkutsk", "RU"),
    "хабаровск": (135.08, 48.48, "Asia/Vladivostok", "RU"),
    "ярославль": (39.89, 57.63, "Europe/Moscow", "RU"),
    "владимир": (40.41, 56.14, "Europe/Moscow", "RU"),
    "рязань": (39.74, 54.62, "Europe/Moscow", "RU"),
    "тула": (37.61, 54.19, "Europe/Moscow", "RU"),
    "тверь": (35.91, 56.86, "Europe/Moscow", "RU"),
    "калуга": (36.28, 54.53, "Europe/Moscow", "RU"),
    "смоленск": (32.04, 54.78, "Europe/Moscow", "RU"),
    "псков": (28.33, 57.81, "Europe/Moscow", "RU"),
    "новгород": (31.28, 58.52, "Europe/Moscow", "RU"),
    "кострома": (40.93, 57.77, "Europe/Moscow", "RU"),
    "иваново": (40.98, 57.00, "Europe/Moscow", "RU"),
    "липецк": (39.60, 52.60, "Europe/Moscow", "RU"),
    "тамбов": (41.46, 52.73, "Europe/Moscow", "RU"),
    "курск": (36.19, 51.74, "Europe/Moscow", "RU"),
    "орёл": (36.08, 52.97, "Europe/Moscow", "RU"),
    "белгород": (36.58, 50.60, "Europe/Moscow", "RU"),
    "брянск": (34.37, 53.25, "Europe/Moscow", "RU"),
    "мурманск": (33.08, 68.97, "Europe/Moscow", "RU"),
    "архангельск": (40.52, 64.54, "Europe/Moscow", "RU"),
    "петрозаводск": (34.37, 61.78, "Europe/Moscow", "RU"),
    "сыктывкар": (50.84, 61.67, "Europe/Moscow", "RU"),
    "киров": (49.66, 58.60, "Europe/Kirov", "RU"),
    "йошкар-ола": (47.89, 56.63, "Europe/Moscow", "RU"),
    "саранск": (45.18, 54.19, "Europe/Moscow", "RU"),
    "чебоксары": (47.25, 56.13, "Europe/Moscow", "RU"),
    "петропавловск-камчатский": (158.65, 53.02, "Asia/Kamchatka", "RU"),
    "магадан": (150.80, 59.57, "Asia/Magadan", "RU"),
    "южно-сахалинск": (142.73, 46.96, "Asia/Sakhalin", "RU"),
    "анадырь": (177.50, 64.73, "Asia/Anadyr", "RU"),
    "якутск": (129.73, 62.03, "Asia/Yakutsk", "RU"),
    "чита": (113.50, 52.03, "Asia/Chita", "RU"),
    "улан-удэ": (107.61, 51.83, "Asia/Irkutsk", "RU"),
    "кемерово": (86.08, 55.33, "Asia/Novosibirsk", "RU"),
    "томск": (84.97, 56.50, "Asia/Tomsk", "RU"),
    "оренбург": (55.10, 51.77, "Asia/Yekaterinburg", "RU"),
    "пенза": (45.00, 53.20, "Europe/Moscow", "RU"),
    "ставрополь": (41.97, 45.04, "Europe/Moscow", "RU"),
    "махачкала": (47.50, 42.98, "Europe/Moscow", "RU"),
    "нальчик": (43.61, 43.50, "Europe/Moscow", "RU"),
    "владикавказ": (44.68, 43.02, "Europe/Moscow", "RU"),
    "грозный": (45.70, 43.31, "Europe/Moscow", "RU"),
    "майкоп": (40.10, 44.60, "Europe/Moscow", "RU"),
    "черкесск": (42.05, 44.22, "Europe/Moscow", "RU"),
    "элиста": (44.26, 46.31, "Europe/Moscow", "RU"),
    "горно-алтайск": (85.96, 51.96, "Asia/Barnaul", "RU"),
    "кызыл": (94.38, 51.72, "Asia/Krasnoyarsk", "RU"),
    "абакан": (91.44, 53.72, "Asia/Krasnoyarsk", "RU"),
    "бийск": (85.25, 52.52, "Asia/Barnaul", "RU"),
    "набережные челны": (52.34, 55.73, "Europe/Moscow", "RU"),
    "нефтекамск": (54.25, 56.09, "Asia/Yekaterinburg", "RU"),
    "тольятти": (49.35, 53.53, "Europe/Samara", "RU"),
    "сочи": (39.73, 43.60, "Europe/Moscow", "RU"),
    "севастополь": (33.53, 44.62, "Europe/Moscow", "RU"),
    "симферополь": (34.11, 44.96, "Europe/Moscow", "RU"),
    "калининград": (20.51, 54.71, "Europe/Kaliningrad", "RU"),
    # === UKRAINE ===
    "киев": (30.52, 50.45, "Europe/Kyiv", "UA"),
    "харьков": (36.23, 50.00, "Europe/Kyiv", "UA"),
    "одесса": (30.73, 46.48, "Europe/Kyiv", "UA"),
    "днепр": (35.05, 48.47, "Europe/Kyiv", "UA"),
    "днепропетровск": (35.05, 48.47, "Europe/Kyiv", "UA"),
    "запорожье": (35.18, 47.84, "Europe/Kyiv", "UA"),
    "львов": (24.03, 49.84, "Europe/Kyiv", "UA"),
    "кривой рог": (33.36, 47.91, "Europe/Kyiv", "UA"),
    "николаев": (31.99, 46.98, "Europe/Kyiv", "UA"),
    "мариуполь": (37.55, 47.10, "Europe/Kyiv", "UA"),
    "винница": (28.47, 49.23, "Europe/Kyiv", "UA"),
    "полтава": (34.55, 49.59, "Europe/Kyiv", "UA"),
    "чернигов": (31.28, 51.50, "Europe/Kyiv", "UA"),
    "черкассы": (32.07, 49.43, "Europe/Kyiv", "UA"),
    "сумы": (34.80, 50.92, "Europe/Kyiv", "UA"),
    "сызрань": (48.47, 53.16, "Europe/Samara", "RU"),
    "житомир": (28.67, 50.26, "Europe/Kyiv", "UA"),
    "ровно": (26.25, 50.62, "Europe/Kyiv", "UA"),
    "ивано-франковск": (24.71, 48.92, "Europe/Kyiv", "UA"),
    "тернополь": (25.59, 49.55, "Europe/Kyiv", "UA"),
    "луцк": (25.33, 50.76, "Europe/Kyiv", "UA"),
    "ужгород": (22.29, 48.62, "Europe/Kyiv", "UA"),
    "хмельницкий": (26.98, 49.42, "Europe/Kyiv", "UA"),
    "черновцы": (25.93, 48.29, "Europe/Kyiv", "UA"),
    "кировоград": (32.26, 48.51, "Europe/Kyiv", "UA"),
    "кропивницкий": (32.26, 48.51, "Europe/Kyiv", "UA"),
    # === BELARUS ===
    "минск": (27.57, 53.90, "Europe/Minsk", "BY"),
    "гомель": (31.00, 52.44, "Europe/Minsk", "BY"),
    "могилёв": (30.34, 53.91, "Europe/Minsk", "BY"),
    "витебск": (30.22, 55.19, "Europe/Minsk", "BY"),
    "гродно": (23.83, 53.68, "Europe/Minsk", "BY"),
    "брест": (23.69, 52.10, "Europe/Minsk", "BY"),
    "бобруйск": (29.23, 53.14, "Europe/Minsk", "BY"),
    "барановичи": (26.01, 53.13, "Europe/Minsk", "BY"),
    "пинск": (26.07, 52.13, "Europe/Minsk", "BY"),
    "новополоцк": (28.63, 55.53, "Europe/Minsk", "BY"),
    # === KAZAKHSTAN ===
    "алматы": (76.89, 43.25, "Asia/Almaty", "KZ"),
    "астана": (71.47, 51.17, "Asia/Almaty", "KZ"),
    "нур-султан": (71.47, 51.17, "Asia/Almaty", "KZ"),
    "шымкент": (69.60, 42.30, "Asia/Almaty", "KZ"),
    "караганда": (73.10, 49.80, "Asia/Almaty", "KZ"),
    "актобе": (57.30, 50.28, "Asia/Aqtobe", "KZ"),
    "тараз": (71.37, 42.90, "Asia/Almaty", "KZ"),
    "павлодар": (77.00, 52.30, "Asia/Almaty", "KZ"),
    "усть-каменогорск": (82.63, 49.99, "Asia/Almaty", "KZ"),
    "семей": (80.25, 50.40, "Asia/Almaty", "KZ"),
    "атырау": (51.88, 47.12, "Asia/Atyrau", "KZ"),
    "кызылорда": (65.50, 44.85, "Asia/Almaty", "KZ"),
    "костанай": (63.63, 53.22, "Asia/Almaty", "KZ"),
    "актау": (51.17, 43.65, "Asia/Aqtau", "KZ"),
    "петропавловск": (69.15, 54.87, "Asia/Almaty", "KZ"),
    "уральск": (51.37, 51.23, "Asia/Oral", "KZ"),
    "кокшетау": (69.38, 53.28, "Asia/Almaty", "KZ"),
    # === UZBEKISTAN ===
    "ташкент": (69.24, 41.30, "Asia/Tashkent", "UZ"),
    "самарканд": (66.96, 39.65, "Asia/Samarkand", "UZ"),
    "бухара": (64.43, 39.77, "Asia/Samarkand", "UZ"),
    "наманган": (71.66, 41.00, "Asia/Tashkent", "UZ"),
    "андижан": (72.36, 40.79, "Asia/Tashkent", "UZ"),
    "фергана": (71.78, 40.39, "Asia/Tashkent", "UZ"),
    "нукус": (59.61, 42.46, "Asia/Nukus", "UZ"),
    "карши": (65.79, 38.87, "Asia/Samarkand", "UZ"),
    "ургенч": (60.63, 41.55, "Asia/Samarkand", "UZ"),
    # === KYRGYZSTAN ===
    "бишкек": (74.59, 42.87, "Asia/Bishkek", "KG"),
    "ош": (72.80, 40.51, "Asia/Bishkek", "KG"),
    "джалал-абад": (73.00, 40.93, "Asia/Bishkek", "KG"),
    "каракол": (78.39, 42.49, "Asia/Bishkek", "KG"),
    # === TAJIKISTAN ===
    "душанбе": (68.78, 38.57, "Asia/Dushanbe", "TJ"),
    "худжанд": (69.63, 40.28, "Asia/Dushanbe", "TJ"),
    "куляб": (69.78, 37.92, "Asia/Dushanbe", "TJ"),
    "курган-тюбе": (68.55, 37.84, "Asia/Dushanbe", "TJ"),
    # === TURKMENISTAN ===
    "ашхабад": (58.38, 37.96, "Asia/Ashgabat", "TM"),
    "туркменбаши": (52.97, 40.02, "Asia/Ashgabat", "TM"),
    "мары": (62.19, 37.63, "Asia/Ashgabat", "TM"),
    "дашогуз": (59.97, 41.84, "Asia/Ashgabat", "TM"),
    "туркменабад": (63.57, 39.08, "Asia/Ashgabat", "TM"),
    # === AZERBAIJAN ===
    "баку": (49.89, 40.41, "Asia/Baku", "AZ"),
    "ганжа": (46.36, 40.68, "Asia/Baku", "AZ"),
    "сумгаит": (49.67, 40.59, "Asia/Baku", "AZ"),
    "мингечевир": (47.05, 40.77, "Asia/Baku", "AZ"),
    "ленкорань": (48.85, 38.74, "Asia/Baku", "AZ"),
    # === ARMENIA ===
    "ереван": (44.51, 40.18, "Asia/Yerevan", "AM"),
    "гюмри": (43.85, 40.79, "Asia/Yerevan", "AM"),
    "ванадзор": (44.50, 40.81, "Asia/Yerevan", "AM"),
    # === GEORGIA ===
    "тбилиси": (44.79, 41.72, "Asia/Tbilisi", "GE"),
    "кутаиси": (42.69, 42.27, "Asia/Tbilisi", "GE"),
    "батуми": (41.64, 41.65, "Asia/Tbilisi", "GE"),
    "руд": (41.27, 41.83, "Asia/Tbilisi", "GE"),
    # === MOLDOVA ===
    "кишинёв": (28.86, 47.01, "Europe/Chisinau", "MD"),
    "кишинев": (28.86, 47.01, "Europe/Chisinau", "MD"),
    "тирасполь": (29.62, 46.84, "Europe/Chisinau", "MD"),
    "бельцы": (27.92, 47.76, "Europe/Chisinau", "MD"),
    # === BALTICS ===
    "рига": (24.11, 56.95, "Europe/Riga", "LV"),
    "даугавпилс": (26.53, 55.88, "Europe/Riga", "LV"),
    "таллин": (24.75, 59.44, "Europe/Tallinn", "EE"),
    "тарту": (26.72, 58.38, "Europe/Tallinn", "EE"),
    "вильнюс": (25.28, 54.69, "Europe/Vilnius", "LT"),
    "каунас": (23.91, 54.90, "Europe/Vilnius", "LT"),
    "клайпеда": (21.14, 55.70, "Europe/Vilnius", "LT"),
    # === INTERNATIONAL ===
    "лондон": (-0.13, 51.51, "Europe/London", "GB"),
    "берлин": (13.41, 52.52, "Europe/Berlin", "DE"),
    "париж": (2.35, 48.86, "Europe/Paris", "FR"),
    "нью-йорк": (-74.01, 40.71, "America/New_York", "US"),
    "дубай": (55.30, 25.20, "Asia/Dubai", "AE"),
    "пекин": (116.41, 39.91, "Asia/Shanghai", "CN"),
    "токио": (139.69, 35.69, "Asia/Tokyo", "JP"),
    "мадрид": (-3.70, 40.42, "Europe/Madrid", "ES"),
    "барселона": (2.17, 41.39, "Europe/Madrid", "ES"),
    "рим": (12.50, 41.90, "Europe/Rome", "IT"),
    "милан": (9.19, 45.46, "Europe/Rome", "IT"),
    "варшава": (21.01, 52.24, "Europe/Warsaw", "PL"),
    "прага": (14.42, 50.08, "Europe/Prague", "CZ"),
    "софия": (23.32, 42.70, "Europe/Sofia", "BG"),
    "белград": (20.46, 44.82, "Europe/Belgrade", "RS"),
    "загреб": (15.98, 45.81, "Europe/Zagreb", "HR"),
    "вен": (16.37, 48.21, "Europe/Vienna", "AT"),
    "будапешт": (19.04, 47.50, "Europe/Budapest", "HU"),
    "бухарест": (26.10, 44.43, "Europe/Bucharest", "RO"),
    "афины": (23.72, 37.98, "Europe/Athens", "GR"),
    "анкара": (32.85, 39.94, "Europe/Istanbul", "TR"),
    "стамбул": (28.98, 41.01, "Europe/Istanbul", "TR"),
    "телявив": (34.78, 32.09, "Asia/Jerusalem", "IL"),
    "иерусалим": (35.21, 31.77, "Asia/Jerusalem", "IL"),
    "банкок": (100.50, 13.75, "Asia/Bangkok", "TH"),
    "дели": (77.22, 28.66, "Asia/Kolkata", "IN"),
    "шанхай": (121.47, 31.23, "Asia/Shanghai", "CN"),
    "сеул": (126.98, 37.57, "Asia/Seoul", "KR"),
    "сидней": (151.21, -33.87, "Australia/Sydney", "AU"),
    "лос-анджелес": (-118.24, 34.05, "America/Los_Angeles", "US"),
    "чикаго": (-87.65, 41.88, "America/Chicago", "US"),
    "хошимин": (106.70, 10.78, "Asia/Ho_Chi_Minh", "VN"),
    "ханой": (105.85, 21.03, "Asia/Hanoi", "VN"),
}


def _geocode_city(city: str) -> dict | None:
    """Try Nominatim geocoding as fallback."""
    try:
        from geopy.geocoders import Nominatim
        g = Nominatim(user_agent="ZlataBot/2.0", timeout=5)
        loc = g.geocode(city)
        if loc and loc.latitude and loc.longitude:
            return {"lat": loc.latitude, "lng": loc.longitude, "tz_str": "Europe/Moscow", "nation": "RU"}
    except Exception:
        pass
    return None


def resolve_city_coords(city: str) -> dict:
    """dict → Nominatim geocoding → Moscow fallback."""
    city = (city or "").strip()
    if not city:
        return {"lat": DEFAULT_LAT, "lng": DEFAULT_LNG, "tz_str": "Europe/Moscow", "nation": "RU"}

    cached = CITY_COORDS.get(city.lower())
    if cached:
        lng, lat, tz_str, nation = cached
        return {"lat": lat, "lng": lng, "tz_str": tz_str, "nation": nation}

    result = _geocode_city(city)
    if result:
        return result

    return {"lat": DEFAULT_LAT, "lng": DEFAULT_LNG, "tz_str": "Europe/Moscow", "nation": "RU"}


def validate_city(city: str) -> bool:
    """Check if a city can be resolved (dict or Nominatim)."""
    city = (city or "").strip()
    if not city:
        return False
    if city.lower() in CITY_COORDS:
        return True
    result = _geocode_city(city)
    return result is not None


def get_user_birth_data(user_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT name, birth_date, birth_time, birth_city, lat, lng, tz_str, nation FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row and row["birth_date"] else None


def _build_subject(user_data: dict) -> AstrologicalSubject | None:
    bd_str = user_data["birth_date"]
    try:
        bd = datetime.strptime(bd_str, "%d.%m.%Y")
    except ValueError:
        try:
            bd = datetime.strptime(bd_str, "%Y-%m-%d")
        except ValueError:
            return None

    if user_data["birth_time"]:
        parts = user_data["birth_time"].split(":")
        hour = int(parts[0]) if parts[0].isdigit() else 12
        minute = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    else:
        hour, minute = 12, 0

    city = (user_data.get("birth_city") or "").strip() or "Moscow"

    # use stored coords if available (saved during /start registration)
    lat = user_data.get("lat")
    lng = user_data.get("lng")
    tz_str = user_data.get("tz_str") or "Europe/Moscow"
    nation = user_data.get("nation") or "RU"
    if lat is not None and lng is not None:
        try:
            return AstrologicalSubject(
                name=user_data.get("name") or "User",
                year=bd.year,
                month=bd.month,
                day=bd.day,
                hour=hour,
                minute=minute,
                lng=float(lng),
                lat=float(lat),
                tz_str=tz_str,
                city=city,
                nation=nation,
                online=False,
            )
        except Exception:
            pass

    # fallback: CITY_COORDS dict
    coords = CITY_COORDS.get(city.lower())
    if coords:
        lng_c, lat_c, tz_str, nation = coords
        try:
            return AstrologicalSubject(
                name=user_data.get("name") or "User",
                year=bd.year,
                month=bd.month,
                day=bd.day,
                hour=hour,
                minute=minute,
                lng=lng_c,
                lat=lat_c,
                tz_str=tz_str,
                city=city,
                nation=nation,
                online=False,
            )
        except Exception:
            pass

    # final fallback: geonames
    try:
        return AstrologicalSubject(
            name=user_data.get("name") or "User",
            year=bd.year,
            month=bd.month,
            day=bd.day,
            hour=hour,
            minute=minute,
            city=city,
        )
    except Exception:
        return AstrologicalSubject(
            name=user_data.get("name") or "User",
            year=bd.year,
            month=bd.month,
            day=bd.day,
            hour=hour,
            minute=minute,
            lng=DEFAULT_LNG,
            lat=DEFAULT_LAT,
            tz_str="Europe/Moscow",
            city=city,
            nation="RU",
            online=False,
        )


async def generate_chart_png(user_id: int) -> bytes | None:
    user_data = get_user_birth_data(user_id)
    if not user_data:
        return None

    subject = _build_subject(user_data)
    m = subject.model()

    # ----- 1. Generate kerykeion SVG wheel -----
    chart = KerykeionChartSVG(
        subject, chart_type="Natal", chart_language="RU", theme="light"
    )
    svg_full = chart.makeTemplate()
    svg_full = re.sub(r"<!DOCTYPE[^>]*>", "", svg_full)
    svg_full = re.sub(r"<!--.*?-->", "", svg_full, flags=re.DOTALL)

    # Dark theme CSS
    dark_css = """
:root {
  --kerykeion-color-neutral-content: #e2e8f0;
  --kerykeion-color-base-content: #e2e8f0;
  --kerykeion-color-base-100: #1e293b;
  --kerykeion-color-base-200: #334155;
  --kerykeion-color-base-300: #475569;
  --kerykeion-chart-color-paper-0: #e2e8f0;
  --kerykeion-chart-color-paper-1: #0f172a;
  --kerykeion-chart-color-zodiac-bg-0: #1e293b;
  --kerykeion-chart-color-zodiac-bg-1: #0f172a;
  --kerykeion-chart-color-zodiac-bg-2: #1e293b;
  --kerykeion-chart-color-zodiac-bg-3: #0f172a;
  --kerykeion-chart-color-zodiac-bg-4: #1e293b;
  --kerykeion-chart-color-zodiac-bg-5: #0f172a;
  --kerykeion-chart-color-zodiac-bg-6: #1e293b;
  --kerykeion-chart-color-zodiac-bg-7: #0f172a;
  --kerykeion-chart-color-zodiac-bg-8: #1e293b;
  --kerykeion-chart-color-zodiac-bg-9: #0f172a;
  --kerykeion-chart-color-zodiac-bg-10: #1e293b;
  --kerykeion-chart-color-zodiac-bg-11: #0f172a;
  --kerykeion-modern-zodiac-bg-0: #334155;
  --kerykeion-modern-zodiac-bg-1: #1e293b;
  --kerykeion-modern-zodiac-bg-opacity: 0.5;
  --kerykeion-modern-stroke: #475569;
  --kerykeion-modern-house-ring: #334155;
  --kerykeion-modern-planet-ring: #1e293b;
  --kerykeion-modern-planet-ring-outer: #334155;
  --kerykeion-chart-color-sun: #fbbf24;
  --kerykeion-chart-color-moon: #94a3b8;
  --kerykeion-chart-color-mercury: #34d399;
  --kerykeion-chart-color-venus: #f472b6;
  --kerykeion-chart-color-mars: #fb7185;
  --kerykeion-chart-color-jupiter: #a78bfa;
  --kerykeion-chart-color-saturn: #fb923c;
  --kerykeion-chart-color-uranus: #22d3ee;
  --kerykeion-chart-color-neptune: #60a5fa;
  --kerykeion-chart-color-pluto: #f87171;
  --kerykeion-chart-color-conjunction: #4ade80;
  --kerykeion-chart-color-opposition: #f87171;
  --kerykeion-chart-color-trine: #60a5fa;
  --kerykeion-chart-color-square: #fb923c;
  --kerykeion-chart-color-sextile: #a78bfa;
  --kerykeion-chart-color-zodiac-radix-ring-0: #475569;
  --kerykeion-chart-color-zodiac-radix-ring-1: #334155;
  --kerykeion-chart-color-zodiac-radix-ring-2: #334155;
  --kerykeion-chart-color-houses-radix-line: #475569;
  --kerykeion-chart-color-first-house: #fbbf24;
  --kerykeion-chart-color-tenth-house: #a78bfa;
  --kerykeion-modern-retrograde: #f87171;
  --kerykeion-modern-indicator: #64748b;
}
"""
    svg_full = svg_full.replace("</style>", f"{dark_css}\n</style>")

    # Extract the wheel group, scale and center it
    wheel_start = svg_full.find("<g kr:node='Full_Wheel'")
    pos = svg_full.index(">", wheel_start) + 1
    depth = 1
    while depth > 0 and pos < len(svg_full):
        nxt_o = svg_full.find("<g ", pos)
        nxt_c = svg_full.find("</g>", pos)
        if nxt_c == -1:
            break
        if nxt_o != -1 and nxt_o < nxt_c:
            depth += 1
            pos = nxt_o + 3
        else:
            depth -= 1
            pos = nxt_c + 4
    wheel_svg = svg_full[wheel_start:pos]
    # Scale 1.7x, square viewBox 1000x1000, center at (500,500)
    # group center (240,240) * 1.7 = (408,408)
    # translate = (500-408, 500-408) = (92,92)
    wheel_svg = wheel_svg.replace(
        "transform='translate(100,50)'",
        "transform='translate(92,92) scale(1.7)'",
    )

    # Extract the LAST <defs> from original SVG (contains all planet/zodiac symbols)
    defs_start = svg_full.rfind("<defs")
    defs_end = svg_full.rfind("</defs>") + len("</defs>")
    svg_defs = svg_full[defs_start:defs_end] if defs_start >= 0 else ""
    # Scale zodiac symbols down
    if svg_defs:
        ZodIds = ("Ari","Tau","Gem","Can","Leo","Vir","Lib","Sco","Sag","Cap","Aqu","Pis")
        for zid in ZodIds:
            pat = re.compile(rf"<symbol id='{zid}'>(.*?)</symbol>", re.DOTALL)
            svg_defs = pat.sub(lambda m, zid=zid: f"<symbol id='{zid}'><g transform='scale(0.65)'>{m.group(1)}</g></symbol>", svg_defs)

    # ---- 2. Build data for corner blocks ----
    signs_sh = ["\u2648","\u2649","\u264a","\u264b","\u264c","\u264d",
                "\u264e","\u264f","\u2650","\u2651","\u2652","\u2653"]

    name = user_data.get("name", "")
    city = user_data.get("birth_city", "")
    nation = user_data.get("nation", "")
    bd = user_data.get("birth_date", "")
    bt = user_data.get("birth_time", "") or "—"
    tz_str = user_data.get("tz_str", "")

    # Planet lines
    planet_attrs = [
        ("sun", "\u2609 \u0421\u043e\u043b\u043d\u0446\u0435"),
        ("moon", "\u263d \u041b\u0443\u043d\u0430"),
        ("mercury", "\u263f \u041c\u0435\u0440\u043a\u0443\u0440\u0438\u0439"),
        ("venus", "\u2640 \u0412\u0435\u043d\u0435\u0440\u0430"),
        ("mars", "\u2642 \u041c\u0430\u0440\u0441"),
        ("jupiter", "\u2643 \u042e\u043f\u0438\u0442\u0435\u0440"),
        ("saturn", "\u2644 \u0421\u0430\u0442\u0443\u0440\u043d"),
        ("uranus", "\u2645 \u0423\u0440\u0430\u043d"),
        ("neptune", "\u2646 \u041d\u0435\u043f\u0442\u0443\u043d"),
        ("pluto", "\u2647 \u041f\u043b\u0443\u0442\u043e\u043d"),
    ]
    planet_lines = []
    for attr, label in planet_attrs:
        p = getattr(m, attr, None)
        if p:
            d = int(p.position)
            mi = int((p.position - d) * 60)
            sh = signs_sh[p.sign_num] if p.sign_num < 12 else "?"
            rr = " R" if p.retrograde else ""
            planet_lines.append(f"{label}: {d}\u00b0{mi:02d}' {sh}{rr}")

    # House cusps
    house_attrs = ["first_house","second_house","third_house","fourth_house",
                   "fifth_house","sixth_house","seventh_house","eighth_house",
                   "ninth_house","tenth_house","eleventh_house","twelfth_house"]
    house_lines = []
    for i, attr in enumerate(house_attrs):
        h = getattr(m, attr, None)
        if h:
            d = int(h.position)
            mi = int((h.position - d) * 60)
            sh = signs_sh[h.sign_num] if h.sign_num < 12 else "?"
            house_lines.append(
                f"\u0414\u043e\u043c {i+1}: {sh} {d}\u00b0{mi:02d}'"
            )

    # Elements & qualities from planets
    elem_map = {"Fire": 0, "Earth": 1, "Air": 2, "Water": 3}
    qual_map = {"Cardinal": 0, "Fixed": 1, "Mutable": 2}
    elems = [0, 0, 0, 0]
    quals = [0, 0, 0]
    count = 0
    for attr, _ in planet_attrs:
        p = getattr(m, attr, None)
        if p:
            ei = elem_map.get(p.element, -1)
            if ei >= 0:
                elems[ei] += 1
            qi = qual_map.get(p.quality, -1)
            if qi >= 0:
                quals[qi] += 1
            count += 1
    total_planes = count
    elem_pct = [(x / total_planes * 100) if total_planes else 0 for x in elems]
    qual_pct = [(x / total_planes * 100) if total_planes else 0 for x in quals]

    elem_names = ["\u041e\u0433\u043e\u043d\u044c", "\u0417\u0435\u043c\u043b\u044f",
                  "\u0412\u043e\u0437\u0434\u0443\u0445", "\u0412\u043e\u0434\u0430"]
    qual_names = ["\u041a\u0430\u0440\u0434\u0438\u043d\u0430\u043b\u044c\u043d\u044b\u0439",
                  "\u0424\u0438\u043a\u0441\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0439",
                  "\u041c\u0443\u0442\u0430\u0431\u0435\u043b\u044c\u043d\u044b\u0439"]

    # ---- 3. Build HTML ----
    wheel_svg_tag = (
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        'viewBox="0 0 1000 1000" '
        'width="100%" height="100%" style="background:transparent" '
        'preserveAspectRatio="xMidYMid meet">'
        f"<style>{svg_full[svg_full.find('<style'):svg_full.find('</style>')+8]}</style>"
        f"{svg_defs}"
        f"<g transform='translate(0,0)'>{wheel_svg}</g></svg>"
    )

    # Starfield JS
    star_js = """
    <script>
      (function(){
        var c = document.getElementById('stars');
        for(var i=0;i<180;i++){
          var s = document.createElement('div');
          s.className = 'star';
          var sz = Math.random()*2+0.5;
          s.style.setProperty('--s', sz+'px');
          s.style.setProperty('--x', Math.random()*100+'%');
          s.style.setProperty('--y', Math.random()*100+'%');
          s.style.setProperty('--d', (Math.random()*3+2)+'s');
          s.style.setProperty('--delay', Math.random()*5+'s');
          s.style.opacity = Math.random()*0.7+0.2;
          c.appendChild(s);
        }
      })();
    </script>"""

    planet_rows = "".join(
        f"<tr><td>{l}</td></tr>" for l in planet_lines
    )
    house_rows = "".join(
        f"<tr><td>{l}</td></tr>" for l in house_lines
    )
    elem_rows = "".join(
        f"<tr><td>{elem_names[i]}: {elem_pct[i]:.0f}%</td></tr>"
        for i in range(4)
    )
    qual_rows = "".join(
        f"<tr><td>{qual_names[i]}: {qual_pct[i]:.0f}%</td></tr>"
        for i in range(3)
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
@keyframes tw{{0%,100%{{opacity:0.2}}50%{{opacity:0.9}}}}
body{{
  width:100vw;height:100vh;overflow:hidden;position:relative;
  background:#05070a;font-family:'Segoe UI','Arial',sans-serif;color:#e2e8f0;
}}
.stars{{position:absolute;inset:0;pointer-events:none;}}
.star{{
  position:absolute;border-radius:50%;background:#fff;
  width:var(--s);height:var(--s);left:var(--x);top:var(--y);
  animation:tw var(--d) ease-in-out infinite;animation-delay:var(--delay);
}}
.nebula1{{
  position:absolute;top:-20%;left:-10%;width:60%;height:60%;
  background:radial-gradient(ellipse at center,rgba(99,102,241,0.08),transparent 70%);
  pointer-events:none;
}}
.nebula2{{
  position:absolute;bottom:-10%;right:-10%;width:50%;height:50%;
  background:radial-gradient(ellipse at center,rgba(168,85,247,0.06),transparent 70%);
  pointer-events:none;
}}
.wheel-wrap{{
  position:absolute;inset:0;
  display:flex;align-items:center;justify-content:center;
}}
.wheel-wrap svg{{
  width:94vmin;height:94vmin;opacity:0.93;
  filter:drop-shadow(0 0 30px rgba(99,102,241,0.12));
}}
.corner{{
  position:absolute;z-index:2;
  background:rgba(15,23,42,0.78);border:1px solid rgba(99,102,241,0.18);
  border-radius:8px;padding:8px 12px;font-size:11px;line-height:1.5;
  backdrop-filter:blur(4px);max-width:320px;
}}
.corner .ttl{{color:#fbbf24;font-size:12px;font-weight:bold;margin-bottom:3px;}}
.tl{{top:10px;left:10px;}}
.bl{{bottom:10px;left:10px;}}
.tr{{top:10px;right:10px;}}
.br{{bottom:10px;right:10px;}}
.gt{{font-size:10px;border-collapse:collapse;width:100%;}}
.gt td{{padding:1px 4px;}}
.gt tr:nth-child(odd){{background:rgba(51,65,85,0.3);}}
.tri{{
  position:absolute;bottom:16px;right:16px;z-index:3;
  width:0;height:0;
  border-left:20px solid transparent;border-bottom:20px solid rgba(167,139,250,0.3);
}}
</style></head><body>
<div class="stars" id="stars"></div>
<div class="nebula1"></div>
<div class="nebula2"></div>
<div class="wheel-wrap">{wheel_svg_tag}</div>

<div class="corner tl">
  <div class="ttl">{name} — \u041d\u0430\u0442\u0430\u043b\u044c\u043d\u0430\u044f \u041a\u0430\u0440\u0442\u0430</div>
  <div>{city}, {nation}</div>
  <div>{bd} {bt} {tz_str}</div>
  <div style="margin-top:4px;color:#94a3b8;">\u0421\u0442\u0438\u0445\u0438\u0438:</div>
  <table class="gt">{elem_rows}</table>
  <div style="margin-top:2px;color:#94a3b8;">\u041a\u0430\u0447\u0435\u0441\u0442\u0432\u0430:</div>
  <table class="gt">{qual_rows}</table>
</div>

<div class="corner bl">
  <div>\u0417\u043e\u0434\u0438\u0430\u043a: \u0422\u0440\u043e\u043f\u0438\u0447\u0435\u0441\u043a\u0438\u0439</div>
  <div>\u0414\u043e\u043c\u0438\u0444\u0438\u043a\u0430\u0446\u0438\u044f: \u041f\u043b\u0430\u0446\u0438\u0434\u0443\u0441</div>
  <div>\u041b\u0443\u043d\u0430: {getattr(getattr(m,'lunar_phase',None),'moon_phase_name','—')}</div>
  <div style="margin-top:4px;color:#94a3b8;font-size:10px;">\u0410\u0441\u043f\u0435\u043a\u0442\u044b \u043d\u0430 \u043a\u043e\u043b\u0435\u0441\u0435:</div>
  <div style="font-size:9px;line-height:1.6;">
    <span style="display:inline-block;width:10px;height:10px;background:#4ade80;border-radius:2px;vertical-align:middle;margin-right:4px;"></span>\u0421\u043e\u0435\u0434\u0438\u043d\u0435\u043d\u0438\u0435 (0\u00b0)
    <span style="display:inline-block;width:10px;height:10px;background:#f87171;border-radius:2px;vertical-align:middle;margin:0 4px 0 8px;"></span>\u041e\u043f\u043f\u043e\u0437\u0438\u0446\u0438\u044f (180\u00b0)
    <br>
    <span style="display:inline-block;width:10px;height:10px;background:#60a5fa;border-radius:2px;vertical-align:middle;margin-right:4px;"></span>\u0422\u0440\u0438\u043d (120\u00b0)
    <span style="display:inline-block;width:10px;height:10px;background:#fb923c;border-radius:2px;vertical-align:middle;margin:0 4px 0 8px;"></span>\u041a\u0432\u0430\u0434\u0440\u0430\u0442 (90\u00b0)
    <span style="display:inline-block;width:10px;height:10px;background:#a78bfa;border-radius:2px;vertical-align:middle;margin:0 4px 0 8px;"></span>\u0421\u0435\u043a\u0441\u0442\u0438\u043b\u044c (60\u00b0)
  </div>
</div>

<div class="corner tr">
  <div class="ttl">\u041f\u043e\u043b\u043e\u0436\u0435\u043d\u0438\u044f \u043f\u043b\u0430\u043d\u0435\u0442</div>
  <table class="gt">{planet_rows}</table>
</div>

<div class="corner br">
  <div class="ttl">\u041a\u0443\u0441\u043f\u0438\u0434\u044b \u0434\u043e\u043c\u043e\u0432</div>
  <table class="gt">{house_rows}</table>
</div>

<div class="tri"></div>
{star_js}
</body></html>"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            viewport={"width": 900, "height": 900}, device_scale_factor=2
        )
        await page.set_content(html)
        await page.wait_for_timeout(2000)
        png_bytes = await page.screenshot()
        await browser.close()

    return png_bytes


def get_natal_text_for_ai(user_id: int) -> str | None:
    user_data = get_user_birth_data(user_id)
    if not user_data:
        return None

    subject = _build_subject(user_data)
    m = subject.model()

    lines = []
    lines.append(f"Имя: {user_data['name'] or '—'}")
    lines.append(f"Дата рождения: {user_data['birth_date']}")
    lines.append(f"Время рождения: {user_data.get('birth_time') or '—'}")
    lines.append(f"Город: {user_data.get('birth_city') or '—'}")
    lines.append("")

    point_names = {
        "sun": "Солнце", "moon": "Луна", "mercury": "Меркурий",
        "venus": "Венера", "mars": "Марс", "jupiter": "Юпитер",
        "saturn": "Сатурн", "uranus": "Уран", "neptune": "Нептун",
        "pluto": "Плутон",
    }

    house_map = {
        "first_house": "1", "second_house": "2", "third_house": "3",
        "fourth_house": "4", "fifth_house": "5", "sixth_house": "6",
        "seventh_house": "7", "eighth_house": "8", "ninth_house": "9",
        "tenth_house": "10", "eleventh_house": "11", "twelfth_house": "12",
    }

    for attr, ru_name in point_names.items():
        point = getattr(m, attr, None)
        if point:
            sign_ru = ZODIAC_SIGNS_RU.get(point.sign, point.sign)
            house_num = house_map.get(point.house.lower(), point.house)
            lines.append(f"{ru_name} — {sign_ru}, {house_num} дом")

    lines.append("")
    if m.ascendant:
        asc_sign = ZODIAC_SIGNS_RU.get(m.ascendant.sign, m.ascendant.sign)
        lines.append(f"Асцендент: {asc_sign}")
    if m.medium_coeli:
        mc_sign = ZODIAC_SIGNS_RU.get(m.medium_coeli.sign, m.medium_coeli.sign)
        lines.append(f"MC (Середина неба): {mc_sign}")

    from kerykeion import NatalAspects

    aspects = NatalAspects(subject)
    aspect_names_ru = {
        "conjunction": "соединение", "sextile": "секстиль",
        "square": "квадратура", "trine": "трин",
        "opposition": "оппозиция", "quincunx": "квинконс",
        "semi-sextile": "полусекстиль", "semi-square": "полуквадрат",
        "sesquiquadrate": "полуторный квадрат",
        "quintile": "квинтиль", "biquintile": "биквинтиль",
    }
    planet_names_en_ru = {
        "Sun": "Солнце", "Moon": "Луна", "Mercury": "Меркурий",
        "Venus": "Венера", "Mars": "Марс", "Jupiter": "Юпитер",
        "Saturn": "Сатурн", "Uranus": "Уран", "Neptune": "Нептун",
        "Pluto": "Плутон", "Ascendant": "Асцендент",
        "Medium_Coeli": "MC", "Descendant": "Десцендент",
        "Imum_Coeli": "IC", "Mean_Lilith": "Лилит",
        "True_North_Lunar_Node": "Северный узел",
        "True_South_Lunar_Node": "Южный узел",
        "Chiron": "Хирон",
    }
    aspects_lines = []
    for a in aspects.relevant_aspects:
        ru_aspect = aspect_names_ru.get(a.aspect, a.aspect)
        p1 = planet_names_en_ru.get(a.p1_name, a.p1_name)
        p2 = planet_names_en_ru.get(a.p2_name, a.p2_name)
        aspects_lines.append(f"{p1} — {ru_aspect} — {p2} (орб {a.orbit:.1f})")

    if aspects_lines:
        lines.append("")
        lines.append("Аспекты:")
        lines.extend(aspects_lines[:10])

    return "\n".join(lines)
