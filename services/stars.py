import json
import math
import random
from datetime import datetime
from pathlib import Path

from skyfield.api import load, Star, wgs84

from config import BASE_DIR

BRIGHT_STARS_PATH = BASE_DIR / "data" / "bright_stars.json"
CONST_LINES_PATH = BASE_DIR / "data" / "constellation_lines.json"

SCALE = 3
MM = 3.7795275 * SCALE
W, H = 210 * MM, 297 * MM
GOLD = "#FFFFFF"
WHITE = "#FFFFFF"

# Chart circle layout
CHART_CY = H * 0.43
CHART_R = min(W, H) * 0.45
CX = W / 2


def _load_stars() -> list[dict]:
    with open(BRIGHT_STARS_PATH) as f:
        return json.load(f)


def _load_constellation_lines() -> list[dict]:
    p = CONST_LINES_PATH
    if not p.exists():
        return []
    with open(p) as f:
        return json.load(f)


def _radec_to_xy(ra: float, dec: float, lst: float, lat: float):
    """Stereographic projection. Returns (nx, ny) in [-1,1] space or None."""
    ha = (lst - ra) * math.pi / 180
    d = dec * math.pi / 180
    la = lat * math.pi / 180

    sin_alt = math.sin(d) * math.sin(la) + math.cos(d) * math.cos(la) * math.cos(ha)
    if sin_alt < 0.01:
        return None

    scale = 1 / (1 + sin_alt)
    x = math.cos(d) * math.sin(ha) * scale
    y = (math.sin(d) * math.cos(la) - math.cos(d) * math.sin(la) * math.cos(ha)) * scale
    return (x, y)


def _mag_to_radius(mag: float) -> float:
    if mag < 0:
        return 5.0 * SCALE
    if mag < 1:
        return 4.0 * SCALE
    if mag < 2:
        return 3.0 * SCALE
    if mag < 3:
        return 2.5 * SCALE
    if mag < 4:
        return 2.0 * SCALE
    return 1.5 * SCALE


def _mag_to_opacity(mag: float) -> float:
    if mag < 1:
        return 1.0
    if mag < 2:
        return 0.9
    if mag < 3:
        return 0.7
    if mag < 4:
        return 0.55
    return 0.45


def generate_star_chart_svg(
    date_str: str, caption: str = "",
    time_str: str = "23:00", location: str = "Москва",
    lat: float = 55.75, lon: float = 37.62,
) -> str:
    stars_data = _load_stars()
    const_lines = _load_constellation_lines()

    day, month, year = map(int, date_str.split("."))
    hour, minute = map(int, time_str.split(":"))
    from skyfield.api import utc
    dt = datetime(year, month, day, hour, minute, tzinfo=utc)

    ts = load.timescale()
    t = ts.from_datetime(dt)
    lst = t.gmst + lon / 15
    lst_deg = (lst % 24) * 15

    # Project stars
    projected = []
    star_map = {}
    for s in stars_data:
        xy = _radec_to_xy(s["ra"], s["dec"], lst_deg, lat)
        if xy is None:
            continue
        px = CX + xy[0] * CHART_R
        py = CHART_CY - xy[1] * CHART_R
        dist2 = (px - CX) ** 2 + (py - CHART_CY) ** 2
        if dist2 > CHART_R ** 2:
            continue
        projected.append({
            "x": px, "y": py,
            "r": _mag_to_radius(s["mag"]),
            "op": _mag_to_opacity(s["mag"]),
        })
        star_map[s["hip"]] = (px, py)

    # Project constellation lines
    drawn_lines = set()
    projected_lines = []
    for cl in const_lines:
        ra1, dec1 = cl["ra1"], cl["dec1"]
        ra2, dec2 = cl["ra2"], cl["dec2"]
        xy1 = _radec_to_xy(ra1, dec1, lst_deg, lat)
        xy2 = _radec_to_xy(ra2, dec2, lst_deg, lat)
        if xy1 is None or xy2 is None:
            continue
        x1 = CX + xy1[0] * CHART_R
        y1 = CHART_CY - xy1[1] * CHART_R
        x2 = CX + xy2[0] * CHART_R
        y2 = CHART_CY - xy2[1] * CHART_R
        in1 = (x1 - CX) ** 2 + (y1 - CHART_CY) ** 2 <= CHART_R ** 2
        in2 = (x2 - CX) ** 2 + (y2 - CHART_CY) ** 2 <= CHART_R ** 2
        if not (in1 and in2):
            continue
        key = (round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1))
        if key in drawn_lines:
            continue
        drawn_lines.add(key)
        projected_lines.append((x1, y1, x2, y2))

    # Planets
    planets = load("de421.bsp")
    planet_map = [
        ("mercury", "☿"), ("venus", "♀"), ("mars", "♂"),
        ("jupiter barycenter", "♃"), ("saturn barycenter", "♄"),
    ]
    earth = planets["earth"]
    sun_body = planets["sun"]
    geo = earth + wgs84.latlon(lat, lon)

    planet_positions = []
    for name, symbol in planet_map:
        body = planets[name.lower()]
        astrometric = geo.at(t).observe(body)
        ra, dec, _ = astrometric.radec()
        xy = _radec_to_xy(ra._degrees, dec._degrees, lst_deg, lat)
        if xy is None:
            continue
        px = CX + xy[0] * CHART_R
        py = CHART_CY - xy[1] * CHART_R
        dist2 = (px - CX) ** 2 + (py - CHART_CY) ** 2
        if dist2 > CHART_R ** 2:
            continue
        planet_positions.append({"x": px, "y": py, "label": symbol})

    astrometric = geo.at(t).observe(sun_body)
    ra, dec, _ = astrometric.radec()
    xy = _radec_to_xy(ra._degrees, dec._degrees, lst_deg, lat)
    sun_pos = None
    if xy is not None:
        px = CX + xy[0] * CHART_R
        py = CHART_CY - xy[1] * CHART_R
        if (px - CX) ** 2 + (py - CHART_CY) ** 2 <= CHART_R ** 2:
            sun_pos = (px, py)

    moon = planets["moon"]
    astrometric = geo.at(t).observe(moon)
    ra, dec, _ = astrometric.radec()
    xy = _radec_to_xy(ra._degrees, dec._degrees, lst_deg, lat)
    moon_pos = None
    if xy is not None:
        px = CX + xy[0] * CHART_R
        py = CHART_CY - xy[1] * CHART_R
        if (px - CX) ** 2 + (py - CHART_CY) ** 2 <= CHART_R ** 2:
            moon_pos = (px, py)

    # Date and location label
    months_ru = [
        "", "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]
    date_label = f"{day} {months_ru[month]} {year}, {time_str}"

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="#000005"/>',
    ]

    # Background noise stars inside chart circle
    rng = random.Random(hash(date_str))
    for _ in range(3000):
        # Random point inside circle via rejection sampling
        bx = rng.uniform(CX - CHART_R, CX + CHART_R)
        by = rng.uniform(CHART_CY - CHART_R, CHART_CY + CHART_R)
        if (bx - CX) ** 2 + (by - CHART_CY) ** 2 > CHART_R ** 2:
            continue
        br = rng.uniform(0.8 * SCALE, 1.5 * SCALE)
        bop = rng.uniform(0.04, 0.12)
        svg_parts.append(
            f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{br}" '
            f'fill="white" opacity="{bop}"/>'
        )

    # Constellation lines
    for x1, y1, x2, y2 in projected_lines:
        svg_parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="white" stroke-width="{1.5 * SCALE + 1}" opacity="0.3"/>'
        )

    # Catalog stars
    for st in projected:
        svg_parts.append(
            f'<circle cx="{st["x"]:.1f}" cy="{st["y"]:.1f}" r="{st["r"]}" '
            f'fill="white" opacity="{st["op"]}"/>'
        )

    # Planets
    for p in planet_positions:
        svg_parts.append(
            f'<circle cx="{p["x"]:.1f}" cy="{p["y"]:.1f}" r="{3 * SCALE}" fill="{GOLD}"/>'
        )
        svg_parts.append(
            f'<text x="{p["x"] + 6 * SCALE:.1f}" y="{p["y"] + 2 * SCALE:.1f}" '
            f'fill="{GOLD}" font-size="{9 * SCALE}" font-family="sans-serif">{p["label"]}</text>'
        )

    if sun_pos:
        svg_parts.append(
            f'<circle cx="{sun_pos[0]:.1f}" cy="{sun_pos[1]:.1f}" r="{5 * SCALE}" '
            f'fill="{GOLD}" opacity="0.9"/>'
        )
        svg_parts.append(
            f'<circle cx="{sun_pos[0]:.1f}" cy="{sun_pos[1]:.1f}" r="{10 * SCALE}" '
            f'fill="none" stroke="{GOLD}" stroke-width="{0.6 * SCALE}" opacity="0.3"/>'
        )
        svg_parts.append(
            f'<text x="{sun_pos[0] + 7 * SCALE:.1f}" y="{sun_pos[1] + 2 * SCALE:.1f}" '
            f'fill="{GOLD}" font-size="{9 * SCALE}" font-family="sans-serif">☀</text>'
        )

    if moon_pos:
        svg_parts.append(
            f'<circle cx="{moon_pos[0]:.1f}" cy="{moon_pos[1]:.1f}" r="{4 * SCALE}" '
            f'fill="#C0C0C0" opacity="0.9"/>'
        )
        svg_parts.append(
            f'<text x="{moon_pos[0] + 6 * SCALE:.1f}" y="{moon_pos[1] + 2 * SCALE:.1f}" '
            f'fill="#C0C0C0" font-size="{9 * SCALE}" font-family="sans-serif">🌙</text>'
        )

    # Chart circle border
    svg_parts.append(
        f'<circle cx="{CX}" cy="{CHART_CY}" r="{CHART_R}" '
        f'fill="none" stroke="{GOLD}" stroke-width="{0.3 * SCALE + 3}" opacity="0.4"/>'
    )

    # Cardinal directions
    dirs = [("N", 0, -1), ("S", 0, 1), ("E", 1, 0), ("W", -1, 0)]
    for label, dx, dy in dirs:
        x = CX + dx * (CHART_R + 10 * SCALE)
        y = CHART_CY + dy * (CHART_R + 10 * SCALE)
        svg_parts.append(
            f'<text x="{x}" y="{y}" text-anchor="middle" dominant-baseline="central" '
            f'fill="white" font-size="{10 * SCALE}" font-family="sans-serif" font-weight="bold" opacity="0.5">{label}</text>'
        )

    # === TEXT SECTION at bottom ===
    text_area_top = H * 0.82 + 50
    text_area_bottom = H - 2 * SCALE

    # Separator line above text
    svg_parts.append(
        f'<line x1="{W * 0.15}" y1="{text_area_top}" x2="{W * 0.85}" y2="{text_area_top}" '
        f'stroke="{GOLD}" stroke-width="{1.5 * SCALE}" opacity="0.3"/>'
    )

    # Caption / title phrase with auto-wrap at ~35 chars
    caption_start = text_area_top + 25 * SCALE
    line_h = 22 * SCALE + 6 * SCALE
    if caption:
        raw_lines = caption.strip().split("\n")
        lines = []
        for line in raw_lines:
            words = line.strip().split()
            cur = ""
            for w in words:
                if len(cur) + len(w) + 1 > 35:
                    lines.append(cur.strip())
                    cur = w
                else:
                    cur += " " + w
            if cur:
                lines.append(cur.strip())
        for i, line in enumerate(lines):
            svg_parts.append(
                f'<text x="{CX}" y="{caption_start + i * line_h}" '
                f'text-anchor="middle" fill="{GOLD}" font-size="{20 * SCALE}" '
                f'font-family="Georgia, serif" letter-spacing="{2 * SCALE}" '
                f'opacity="0.95">{line}</text>'
            )

    # Date and location
    datetime_str = f"{date_label}"
    loc_str = location
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"
    lat_abs, lon_abs = abs(lat), abs(lon)
    lat_d, lat_m = int(lat_abs), int((lat_abs % 1) * 60)
    lon_d, lon_m = int(lon_abs), int((lon_abs % 1) * 60)
    coords_str = f"{lat_d}°{lat_m}′{lat_dir} {lon_d}°{lon_m}′{lon_dir}"
    text_bottom = text_area_bottom - 10 * SCALE

    svg_parts.append(
        f'<text x="{CX}" y="{text_bottom}" text-anchor="middle" '
        f'fill="{GOLD}" font-size="{9 * SCALE}" font-family="sans-serif" '
        f'opacity="0.5">{datetime_str}</text>'
    )
    svg_parts.append(
        f'<text x="{CX}" y="{text_bottom - 14 * SCALE}" text-anchor="middle" '
        f'fill="{GOLD}" font-size="{9 * SCALE}" font-family="sans-serif" '
        f'opacity="0.5">{loc_str}</text>'
    )
    svg_parts.append(
        f'<text x="{CX}" y="{text_bottom - 28 * SCALE}" text-anchor="middle" '
        f'fill="{GOLD}" font-size="{9 * SCALE}" font-family="sans-serif" '
        f'opacity="0.5">{coords_str}</text>'
    )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)
