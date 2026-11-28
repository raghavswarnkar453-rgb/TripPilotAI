"""Run from backend/ while the server is running:  python scripts/prewarm.py [destination ...]
Generates a trip for each demo destination so slow lookups (map data, geocoding) are cached before you present.
Caches last ~1-24 hours inside the running server."""
import datetime as dt
import sys
import time

import httpx

DESTINATIONS = sys.argv[1:] or ["Manali, Himachal Pradesh", "Goa", "Jaipur, Rajasthan"]
start = dt.date.today() + dt.timedelta(days=2)
end = start + dt.timedelta(days=2)

for name in DESTINATIONS:
    body = {
        "destination": name, "start_date": start.isoformat(), "end_date": end.isoformat(),
        "budget": 20000, "travelers": 2, "interests": ["Adventure", "Food"], "travel_style": "balanced",
    }
    t0 = time.time()
    try:
        r = httpx.post("http://localhost:8000/api/trips/generate", json=body, timeout=150)
    except httpx.HTTPError as e:
        print(f"[FAIL] {name}: backend not reachable ({type(e).__name__}). Is uvicorn running?")
        continue
    took = time.time() - t0
    if r.status_code == 200:
        d = r.json()
        print(f"[ OK ] {name}: {took:.0f}s, matched '{d['destination']['display_name']}', "
              f"attractions={d['attractions_status']}, weather={d['weather']['source']}, model={d['model']}")
    else:
        print(f"[FAIL] {name}: HTTP {r.status_code} {r.text[:200]}")
