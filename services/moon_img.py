from pathlib import Path

from config import BASE_DIR
from services.astrology import get_moon_info

MOONS_DIR = BASE_DIR / "assets" / "moons"


def get_moon_image_path() -> str:
    info = get_moon_info()
    phase_en = info["phase_en"]
    filename = f"moon_{phase_en.lower().replace(' ', '_')}.png"
    full = MOONS_DIR / filename
    if not full.exists():
        # fallback: return a placeholder if image not found
        return str(MOONS_DIR / "moon_full_moon.png")
    return str(full)
