import asyncio
import logging
import re

import httpx

from app.schemas.trip import Attraction

log = logging.getLogger(__name__)

MAX_ATTRACTIONS = 40
STAGGER_SECONDS = 1.5  # start the next Overpass server if the current one hasn't answered by then
OVERPASS_DEADLINE = 16.0  # give up on Overpass after this long, then use Wikipedia (slow servers can take ~8 s)


def build_query(lat: float, lon: float, radius_m: int = 12000) -> str:
    around = f"(around:{radius_m},{lat:.5f},{lon:.5f})"
    return (
        "[out:json][timeout:20];\n(\n"
        f'  nwr{around}["tourism"~"^(attraction|viewpoint|museum|zoo|theme_park|gallery)$"]["name"];\n'
        f'  nwr{around}["historic"]["name"];\n'
        f'  nwr{around}["leisure"~"^(park|nature_reserve)$"]["name"];\n'
        f'  nwr{around}["natural"~"^(peak|waterfall|hot_spring|beach)$"]["name"];\n'
        ");\nout center 100;"
    )


def parse_overpass(payload: dict) -> list[Attraction]:
    scored: list[tuple[int, str, Attraction]] = []
    seen: set[str] = set()
    for el in payload.get("elements") or []:
        tags = el.get("tags") or {}
        name = (tags.get("name:en") or tags.get("name") or "").strip()
        lat = el.get("lat", (el.get("center") or {}).get("lat"))
        lon = el.get("lon", (el.get("center") or {}).get("lon"))
        if not name or lat is None or lon is None or name.lower() in seen:
            continue
        seen.add(name.lower())
        category = next(
            (tags[k] for k in ("tourism", "historic", "natural", "leisure") if tags.get(k)), None
        )
        score = (2 if ("wikidata" in tags or "wikipedia" in tags) else 0) + (
            1 if ("tourism" in tags or "historic" in tags) else 0
        )
        scored.append(
            (score, name.lower(), Attraction(name=name, category=category, latitude=float(lat), longitude=float(lon)))
        )
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [a for _, _, a in scored[:MAX_ATTRACTIONS]]


WIKIPEDIA_GEOSEARCH = "https://en.wikipedia.org/w/api.php"


# Wikipedia geosearch also returns administrative/infrastructure pages, which aren't things to visit.
_NON_TOURIST = re.compile(
    r"\b(constituency|assembly|election|highway|district|tehsil|railway|station|airport|school|college|"
    r"university|institute|hospital|list of|block|municipal|panchayat|census)\b",
    re.IGNORECASE,
)


def _is_destination_itself(name: str, skip_names: set[str]) -> bool:
    low = name.lower()
    return any(low == s or low.startswith(s + ",") or low.startswith(s + " (") for s in skip_names)


def parse_wikipedia(payload: dict, skip_names: set[str]) -> list[Attraction]:
    out: list[Attraction] = []
    for row in (payload.get("query") or {}).get("geosearch") or []:
        name = str(row.get("title") or "").strip()
        lat, lon = row.get("lat"), row.get("lon")
        if not name or lat is None or lon is None:
            continue
        if _is_destination_itself(name, skip_names) or _NON_TOURIST.search(name):
            continue
        out.append(Attraction(name=name, category="landmark", latitude=float(lat), longitude=float(lon)))
    return out[:MAX_ATTRACTIONS]


async def fetch_wikipedia_places(
    client: httpx.AsyncClient, lat: float, lon: float, user_agent: str, skip_names: set[str]
) -> list[Attraction]:
    """Last-resort source: notable places near the destination from Wikipedia's geosearch. Never raises."""
    try:
        res = await client.get(
            WIKIPEDIA_GEOSEARCH,
            params={
                "action": "query", "list": "geosearch", "gscoord": f"{lat}|{lon}",
                "gsradius": 10000, "gslimit": 50, "format": "json", "formatversion": 2,
            },
            headers={"User-Agent": user_agent},
        )
        res.raise_for_status()
        return parse_wikipedia(res.json(), skip_names)
    except (httpx.HTTPError, ValueError) as e:
        log.warning("wikipedia geosearch failed: %s", type(e).__name__)
        return []


async def _query_overpass(client: httpx.AsyncClient, url: str, lat: float, lon: float, user_agent: str) -> list[Attraction]:
    host = httpx.URL(url).host
    try:
        res = await client.post(
            url,
            data={"data": build_query(lat, lon)},
            headers={"User-Agent": user_agent, "Accept": "application/json"},
            timeout=httpx.Timeout(14.0, connect=6.0),
        )
        res.raise_for_status()
        items = parse_overpass(res.json())
    except httpx.HTTPStatusError as e:
        log.warning("overpass %s returned HTTP %s", host, e.response.status_code)
        return []
    except (httpx.HTTPError, ValueError) as e:
        log.warning("overpass %s failed: %s", host, type(e).__name__)
        return []
    if not items:
        log.warning("overpass %s returned no named attractions", host)
    return items


async def _first_overpass_result(
    client: httpx.AsyncClient, urls: list[str], lat: float, lon: float, user_agent: str
) -> list[Attraction]:
    """Hedged requests: servers start one after another (next one when the previous fails or is slow),
    the first usable answer wins, and everything is cancelled at the deadline. Cached by the caller."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + OVERPASS_DEADLINE
    queue = list(urls)
    pending: set[asyncio.Task] = set()
    try:
        while (queue or pending) and loop.time() < deadline:
            if queue:
                pending.add(asyncio.create_task(_query_overpass(client, queue.pop(0), lat, lon, user_agent)))
            remaining = deadline - loop.time()
            wait_for = min(STAGGER_SECONDS, remaining) if queue else remaining
            done, pending = await asyncio.wait(pending, timeout=wait_for, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                items = task.result()
                if items:
                    return items
        return []
    finally:
        for task in pending:
            task.cancel()


async def fetch_attractions(
    client: httpx.AsyncClient,
    overpass_urls: list[str],
    lat: float,
    lon: float,
    user_agent: str,
    skip_names: set[str] | None = None,
) -> tuple[list[Attraction], str]:
    """Returns (attractions, status). Overpass servers first, then Wikipedia; never raises."""
    items = await _first_overpass_result(client, overpass_urls, lat, lon, user_agent)
    if items:
        return items, "ok"
    log.warning("overpass gave no usable result; trying Wikipedia geosearch")
    items = await fetch_wikipedia_places(client, lat, lon, user_agent, skip_names or set())
    return (items, "ok") if items else ([], "unavailable")
