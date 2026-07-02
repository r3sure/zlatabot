"""Channel auto-poster — generates images + text, sends to channel."""
import asyncio
import logging
import random
from pathlib import Path
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from services.ai import generate_text
from services.astrology import get_moon_info, SIGN_GENITIVE

logger = logging.getLogger(__name__)

SIZE = 1080  # square output
LINE_PAD = 75

BASE_DIR = Path(__file__).resolve().parent.parent
FONT_TITLE = BASE_DIR / "assets" / "fonts" / "Cormorant[wght].ttf"
BG_PATH = BASE_DIR / "assets" / "bg.png"
CARDS_DIR = BASE_DIR / "assets" / "cards"
MOONS_DIR = BASE_DIR / "assets" / "moons"
ZODIAC_DIR = BASE_DIR / "assets" / "zodiac_signs"

GOLD = (230, 190, 70)
GOLD_DIM = (150, 120, 45)
GOLD_DULL = (200, 175, 100)
WHITE = (255, 255, 255)

WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

ALL_SIGNS = ["Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева",
             "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"]

ZODIAC_MAP = {
    "Овен": "aries", "Телец": "taurus", "Близнецы": "gemini",
    "Рак": "cancer", "Лев": "leo", "Дева": "virgo",
    "Весы": "libra", "Скорпион": "scorpio", "Стрелец": "sagittarius",
    "Козерог": "capricorn", "Водолей": "aquarius", "Рыбы": "pisces",
}

TAROT_CARDS = [
    "00-TheFool", "01-TheMagician", "02-TheHighPriestess", "03-TheEmpress",
    "04-TheEmperor", "05-TheHierophant", "06-TheLovers", "07-TheChariot",
    "08-Strength", "09-TheHermit", "10-WheelOfFortune", "11-Justice",
    "12-TheHangedMan", "13-Death", "14-Temperance", "15-TheDevil",
    "16-TheTower", "17-TheStar", "18-TheMoon", "19-TheSun",
    "20-Judgement", "21-TheWorld",
]

TAROT_NAMES = {
    "00-TheFool": "Шут", "01-TheMagician": "Маг", "02-TheHighPriestess": "Верховная Жрица",
    "03-TheEmpress": "Императрица", "04-TheEmperor": "Император", "05-TheHierophant": "Иерофант",
    "06-TheLovers": "Влюблённые", "07-TheChariot": "Колесница", "08-Strength": "Сила",
    "09-TheHermit": "Отшельник", "10-WheelOfFortune": "Колесо Фортуны", "11-Justice": "Справедливость",
    "12-TheHangedMan": "Повешенный", "13-Death": "Смерть", "14-Temperance": "Умеренность",
    "15-TheDevil": "Дьявол", "16-TheTower": "Башня", "17-TheStar": "Звезда",
    "18-TheMoon": "Луна", "19-TheSun": "Солнце", "20-Judgement": "Суд", "21-TheWorld": "Мир",
}

CHANNEL_ID = "@zlatazvezd"


def _tf(size, weight=700):
    f = ImageFont.truetype(str(FONT_TITLE), size)
    f.set_variation_by_axes([weight])
    return f


def _square_bg():
    bg = Image.open(BG_PATH).convert("RGBA")
    bw, bh = bg.size
    scale = max(SIZE / bw, SIZE / bh)
    new_w, new_h = int(bw * scale), int(bh * scale)
    bg = bg.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - SIZE) // 2
    top = (new_h - SIZE) // 2
    return bg.crop((left, top, left + SIZE, top + SIZE))


def _random_card():
    code = random.choice(TAROT_CARDS)
    name = TAROT_NAMES[code]
    return code, name


def _moon_footer():
    m = get_moon_info()
    return f"Луна в {m['sign_prep']}  ·  {m['phase']}"

def _fmt_caption(text):
    """Ensure each emoji starts on a new line."""
    import re
    text = re.sub(r'(?<!\n)([\U0001F300-\U0001F9FF\u2600-\u27BF\u2B50\u2728])', r'\n\1', text)
    return text.strip()




def _draw_vignette(bg):
    """Subtle dark edge fade — 4 sided gradient."""
    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    fade = 140
    for i in range(fade):
        a = int(50 * (1 - i / fade) ** 2)
        if a < 1:
            continue
        m = i * 3
        d.rectangle([m, m, SIZE - m, SIZE - m], fill=(0, 0, 0, a))
    bg.paste(overlay, (0, 0), overlay)


def _draw_stars(bg):
    """Scatter small white/gold dots across background."""
    draw = ImageDraw.Draw(bg)
    for _ in range(250):
        x = random.randint(0, SIZE)
        y = random.randint(0, SIZE)
        r = random.choice([1, 1, 1, 2])
        if random.random() < 0.3:
            clr = (255, 255, 255)
        else:
            clr = (255, 255, 200) if random.random() < 0.5 else (230, 210, 180)
        draw.ellipse([x, y, x + r, y + r], fill=clr)


def _draw_date(draw):
    from datetime import datetime
    now = datetime.now()
    text = f"{now.strftime('%d.%m.%Y')}, {WEEKDAYS[now.weekday()]}"
    draw.text((SIZE - LINE_PAD, SIZE - 40), text, fill=GOLD_DULL, font=_tf(18, 400), anchor="rt")


def _draw_subtitle(draw, text):
    """Small golden subtitle below the line."""
    bbox = draw.textbbox((0, 0), text, font=_tf(32, 600))
    tw = bbox[2] - bbox[0]
    draw.text(((SIZE - tw) // 2, 135), text, fill=GOLD, font=_tf(32, 600))


# ── Image generators ───────────────────────────────────────────

def _generate_energy_day(card_code: str, card_name: str = "") -> bytes:
    bg = _square_bg()
    _draw_stars(bg)
    _draw_vignette(bg)
    draw = ImageDraw.Draw(bg)

    draw.text((LINE_PAD, 45), "ЭНЕРГИЯ ДНЯ", fill=GOLD, font=_tf(56))
    draw.line((LINE_PAD, 115, SIZE - LINE_PAD, 115), fill=(*GOLD_DIM, 200), width=2)
    if card_name:
        _draw_subtitle(draw, card_name)
    _draw_date(draw)

    card_p = CARDS_DIR / f"{card_code}.png"
    if card_p.exists():
        cw, ch = int(380 * 0.85), int(570 * 0.85)
        cx = (SIZE - cw) // 2
        cy = (SIZE - ch) // 2 + 50
        card = Image.open(card_p).convert("RGBA").resize((cw, ch), Image.LANCZOS)
        bg.paste(card, (cx, cy), card)

    buf = BytesIO()
    bg.save(buf, "PNG")
    buf.seek(0)
    return buf.getvalue()


def _generate_horoscope(sign_ru: str, card_name: str = "") -> bytes:
    bg = _square_bg()
    _draw_stars(bg)
    _draw_vignette(bg)
    draw = ImageDraw.Draw(bg)

    draw.text((LINE_PAD, 45), "ГОРОСКОП ДНЯ", fill=GOLD, font=_tf(56))
    draw.line((LINE_PAD, 115, SIZE - LINE_PAD, 115), fill=(*GOLD_DIM, 200), width=2)
    _draw_subtitle(draw, sign_ru)
    _draw_date(draw)

    eng = ZODIAC_MAP.get(sign_ru)
    if eng:
        z_path = ZODIAC_DIR / f"zodiac_{eng}.png"
        if z_path.exists():
            zw = zh = 520
            zx = (SIZE - zw) // 2
            zy = (SIZE - zh) // 2 + 60
            z = Image.open(z_path).convert("RGBA").resize((zw, zh), Image.LANCZOS)
            bg.paste(z, (zx, zy), z)

    buf = BytesIO()
    bg.save(buf, "PNG")
    buf.seek(0)
    return buf.getvalue()


def _generate_moon() -> bytes:
    bg = _square_bg()
    _draw_stars(bg)
    _draw_vignette(bg)
    draw = ImageDraw.Draw(bg)

    draw.text((LINE_PAD, 45), "ЛУННЫЙ ДЕНЬ", fill=GOLD, font=_tf(56))
    draw.line((LINE_PAD, 115, SIZE - LINE_PAD, 115), fill=(*GOLD_DIM, 200), width=2)
    _draw_date(draw)

    m = get_moon_info()
    _draw_subtitle(draw, f"{m['phase']} в {m['sign_prep']}")

    moon_p = MOONS_DIR / f"moon_{m['phase_en'].lower().replace(' ', '_')}.png"
    if moon_p.exists():
        mw = mh = int(600 * 0.8)
        mx = (SIZE - mw) // 2
        my = (SIZE - mh) // 2 + 60
        moon_img = Image.open(moon_p).convert("RGBA").resize((mw, mh), Image.LANCZOS)
        bg.paste(moon_img, (mx, my), moon_img)

    buf = BytesIO()
    bg.save(buf, "PNG")
    buf.seek(0)
    return buf.getvalue()


# ── AI text generators ────────────────────────────────────────

async def _generate_energy_text() -> tuple[str, str, str]:
    code, name = _random_card()
    m = get_moon_info()
    prompt = (
        f"Ты — астролог Злата. Вытянута карта Таро: «{name}».\n"
        f"Луна: {m['phase']} в знаке {m['sign']}.\n\n"
        f"Напиши «Энергия дня» — 2-3 предложения о том, "
        f"какую энергию несёт этот день. "
        f"Без подписи. Только текст."
    )
    text = await asyncio.to_thread(generate_text, prompt, 0.7)
    text = text.strip().strip('"').strip('"')
    return code, name, text


async def _generate_horoscope_text(sign_ru: str) -> str:
    m = get_moon_info()
    prompt = (
        f"Ты — астролог Злата. Напиши гороскоп на сегодня для знака {SIGN_GENITIVE.get(sign_ru, sign_ru)}.\n"
        f"Луна: {m['phase']} в знаке {m['sign']}.\n\n"
        f"Формат: 2-3 предложения. Без подписи. Без заголовка. Только текст."
    )
    text = await asyncio.to_thread(generate_text, prompt, 0.7)
    return text.strip().strip('"').strip('"')


async def _generate_moon_text() -> str:
    m = get_moon_info()
    prompt = (
        f"Ты — астролог Злата. Сегодня Луна в фазе {m['phase']}, в знаке {m['sign']}.\n\n"
        f"Напиши описание лунного дня (2-3 предложения): "
        f"что несёт эта энергия, чем заниматься, чего избегать. "
        f"Без подписи. Только текст."
    )
    text = await asyncio.to_thread(generate_text, prompt, 0.7)
    return text.strip().strip('"').strip('"')


# ── Main posting functions ────────────────────────────────────

async def post_energy_day(bot):
    code, name, text = await _generate_energy_text()
    moon = _moon_footer()
    img_bytes = _generate_energy_day(code, name)
    cta = "\n\n✍️ Хотите индивидуальный разбор? Напишите мне — @Zlataesotericbot"
    caption = _fmt_caption(f"✨ <b>Энергия дня: {name}</b>\n\n{text}\n\n{moon}{cta}\n\n#карта_дня")
    from aiogram.types import FSInputFile, BufferedInputFile
    await bot.send_photo(CHANNEL_ID, BufferedInputFile(img_bytes, "energy.png"), caption=caption)
    logger.info("Пост «Энергия дня» отправлен")


async def post_horoscope(bot, sign_ru: str):
    text = await _generate_horoscope_text(sign_ru)
    moon = _moon_footer()
    img_bytes = _generate_horoscope(sign_ru)
    cta = "\n\n✍️ Хотите индивидуальный разбор? Напишите мне — @Zlataesotericbot"
    caption = _fmt_caption(f"♈ <b>Гороскоп для {SIGN_GENITIVE.get(sign_ru, sign_ru)}</b>\n\n{text}\n\n{moon}{cta}\n\n#гороскоп")
    from aiogram.types import BufferedInputFile
    await bot.send_photo(CHANNEL_ID, BufferedInputFile(img_bytes, "horoscope.png"), caption=caption)
    logger.info(f"Пост «Гороскоп {sign_ru}» отправлен")


async def post_moon_day(bot):
    text = await _generate_moon_text()
    m = get_moon_info()
    moon = _moon_footer()
    img_bytes = _generate_moon()
    cta = "\n\n✍️ Хотите индивидуальный разбор? Напишите мне — @Zlataesotericbot"
    caption = _fmt_caption(f"🌙 <b>Лунный день</b>\n\n{m['phase']} в {m['sign_prep']}\n\n{text}\n\n{moon}{cta}\n\n#лунный_день")
    from aiogram.types import BufferedInputFile
    await bot.send_photo(CHANNEL_ID, BufferedInputFile(img_bytes, "moon.png"), caption=caption)
    logger.info("Пост «Лунный день» отправлен")


# ── Test: generate all posts for a day ────────────────────────

async def test_all_posts(bot):
    """Generate and send all posts for a day immediately."""
    logger.info("Запуск тестового прогона всех постов...")
    await post_energy_day(bot)
    await asyncio.sleep(2)
    for sign in ALL_SIGNS:
        await post_horoscope(bot, sign)
        await asyncio.sleep(2)
    await post_moon_day(bot)
    logger.info("Тестовый прогон завершён")
