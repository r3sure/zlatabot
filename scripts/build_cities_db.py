"""Download RU geonames data and build a comprehensive Russian cities JSON."""
import csv, json, os, urllib.request, zipfile, io, re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DEST = DATA_DIR / "ru_cities.json"

# Download RU.zip from geonames
URL = "https://download.geonames.org/export/dump/RU.zip"
print("Downloading RU.zip from geonames.org...")
resp = urllib.request.urlopen(URL)
z = zipfile.ZipFile(io.BytesIO(resp.read()))
# The main file is RU.txt (tab-separated)
content = z.read("RU.txt").decode("utf-8")

reader = csv.reader(io.StringIO(content), delimiter="\t")
cities = {}  # lowercase russian name -> (lat, lng, tz_str)
collisions = 0

for row in reader:
    # geonameid(0), name(1), asciiname(2), alternatenames(3), lat(4), lng(5),
    # feature_class(6), feature_code(7), country(8), ...
    # population(14), timezone(17)
    feature_code = row[7]
    # Only include populated places (cities, towns, villages)
    if feature_code not in ("PPL", "PPLA", "PPLA2", "PPLA3", "PPLA4", "PPLA5", "PPLC",
                            "PPLG", "PPLH", "PPLL", "PPLQ", "PPLR", "PPLS", "PPLW", "PPLX",
                            "STLMT"):
        continue

    lat = float(row[4])
    lng = float(row[5])
    tz_str = row[17]
    name = row[1]
    alt_names = row[3]

    # Collect all names: the main name, asciiname, and alt names
    all_names = {name.lower(), row[2].lower()}
    if alt_names:
        for an in alt_names.split(","):
            an = an.strip().lower()
            if an and len(an) > 1:
                all_names.add(an)

    for n in all_names:
        # Only keep cyrillic names (Russian)
        if re.search(r'[а-яё]', n):
            n_clean = re.sub(r'[^\sа-яё-]', '', n).strip()
            n_clean = re.sub(r'\s+', ' ', n_clean)
            if n_clean and len(n_clean) > 1:
                if n_clean not in cities:
                    cities[n_clean] = (lat, lng, tz_str)
                else:
                    collisions += 1

print(f"Found {len(cities)} Russian city name variants, {collisions} collisions skipped")

# Write to JSON
with open(DEST, "w", encoding="utf-8") as f:
    json.dump(cities, f, ensure_ascii=False, indent=1)

print(f"Written to {DEST}")
print(f"File size: {os.path.getsize(DEST) / 1024:.0f} KB")
