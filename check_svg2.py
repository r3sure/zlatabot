"""Check SVG structure"""
from kerykeion import AstrologicalSubject, KerykeionChartSVG

s = AstrologicalSubject("Test", year=2001, month=1, day=30, hour=12, minute=0, lng=48.04, lat=46.35, tz_str="Europe/Astrakhan", city="Астрахань", nation="RU", online=False)
c = KerykeionChartSVG(s, chart_type="Natal", chart_language="RU", theme="light")
svg = c.makeTemplate()

import re

idx = svg.find("</defs>")
print(f"After </defs> ({idx}):")
print(repr(svg[idx:idx+500]))

print(f"\nContains <g: {'<g' in svg}")
print(f"Contains kr:node: {'kr:node' in svg}")

gs = re.findall(r"<g[^>]*>", svg)
print(f"Total <g> tags: {len(gs)}")
for g in gs[:10]:
    print(f"  {g}")

# Check if makeTemplate does both template and chart
print(f"\nmakeTemplate returned type: {type(svg)}")
print(f"Length: {len(svg)}")
