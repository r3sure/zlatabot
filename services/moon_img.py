from io import BytesIO
from pathlib import Path

from PIL import Image

from config import BASE_DIR
from services.astrology import get_moon_info

MOONS_DIR = BASE_DIR / "assets" / "moons"


def get_moon_image_bytes() -> BytesIO:
    info = get_moon_info()
    phase_en = info["phase_en"]
    filename = f"moon_{phase_en.lower().replace(' ', '_')}.png"
    full = MOONS_DIR / filename
    if not full.exists():
        full = MOONS_DIR / "moon_full_moon.png"

    moon = Image.open(full).convert("RGBA")
    bg = Image.new("RGB", moon.size, "black")
    bg.paste(moon, mask=moon.split()[3])

    buf = BytesIO()
    bg.save(buf, format="PNG")
    buf.seek(0)
    return buf
