"""Run from backend/:  python scripts\\check_overpass.py [lat lon]
Sends the same attractions query the app uses to each Overpass server and prints what comes back.
Default location: Manali."""
import sys
import time

import httpx

sys.path.insert(0, ".")
from app.core.config import get_settings  # noqa: E402
from app.services.places import build_query, parse_overpass  # noqa: E402

s = get_settings()
lat = float(sys.argv[1]) if len(sys.argv) > 2 else 32.2454608
lon = float(sys.argv[2]) if len(sys.argv) > 2 else 77.1872926
headers = {"User-Agent": s.nominatim_user_agent, "Accept": "application/json"}

print(f"User-Agent sent: {s.nominatim_user_agent}")
print(f"Location: {lat}, {lon}\n")

for url in s.overpass_url_list():
    host = httpx.URL(url).host
    start = time.time()
    try:
        res = httpx.post(url, data={"data": build_query(lat, lon)}, headers=headers, timeout=httpx.Timeout(40.0, connect=10.0))
    except httpx.HTTPError as e:
        print(f"[{host}] FAILED after {time.time() - start:.1f}s: {type(e).__name__} {e}\n")
        continue
    took = time.time() - start
    print(f"[{host}] HTTP {res.status_code} in {took:.1f}s")
    if res.status_code != 200:
        print("   body:", res.text[:300].replace("\n", " "), "\n")
        continue
    try:
        payload = res.json()
    except ValueError:
        print("   200 but not JSON:", res.text[:300].replace("\n", " "), "\n")
        continue
    if payload.get("remark"):
        print("   server remark:", payload["remark"][:300])
    items = parse_overpass(payload)
    print(f"   raw elements: {len(payload.get('elements') or [])}, usable named attractions: {len(items)}")
    for a in items[:5]:
        print("   -", a.name, f"({a.category})")
    print()

# Wikipedia geosearch (the fallback when every Overpass server is busy)
import asyncio  # noqa: E402

from app.services.places import fetch_wikipedia_places  # noqa: E402


async def _wiki():
    async with httpx.AsyncClient(timeout=15) as c:
        return await fetch_wikipedia_places(c, lat, lon, s.nominatim_user_agent, set())


places = asyncio.run(_wiki())
print(f"[wikipedia geosearch] {len(places)} places")
for a in places[:5]:
    print("   -", a.name)
