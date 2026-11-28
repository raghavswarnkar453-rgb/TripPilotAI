"""Destination lookup: Nominatim first, Open-Meteo's geocoder as a fallback. Never invents coordinates."""
import logging

import httpx

from app.schemas.trip import DestinationInfo
from app.services.errors import DestinationNotFound, UpstreamUnavailable

log = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OPEN_METEO_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"


def parse_nominatim(results: list[dict], query: str) -> DestinationInfo | None:
    if not results:
        return None
    top = results[0]
    try:
        return DestinationInfo(
            query=query,
            display_name=str(top.get("display_name", query)),
            latitude=float(top["lat"]),
            longitude=float(top["lon"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _candidate_text(r: dict) -> str:
    return " ".join(str(r.get(k) or "") for k in ("name", "admin1", "admin2", "admin3", "country")).lower()


def parse_open_meteo(payload: dict, query: str) -> DestinationInfo | None:
    results = payload.get("results") or []
    if not results:
        return None

    # "Manali, Himachal Pradesh": search by "Manali", then keep the result that also matches the rest.
    extra = [t.strip().lower() for t in query.split(",")[1:] if t.strip()]
    top = results[0]
    if extra:
        top = next((r for r in results if all(t in _candidate_text(r) for t in extra)), results[0])

    # Same name in different states/countries and nothing from the user to choose between them.
    top_name = str(top.get("name") or "").lower()
    rivals = [r for r in results if str(r.get("name") or "").lower() == top_name and (r.get("admin1"), r.get("country")) != (top.get("admin1"), top.get("country"))]
    ambiguous = not extra and bool(rivals)

    try:
        parts = [str(top[k]) for k in ("name", "admin2", "admin1", "country") if top.get(k)]
        return DestinationInfo(
            query=query,
            display_name=", ".join(dict.fromkeys(parts)) or query,  # dict.fromkeys drops repeats, keeps order
            latitude=float(top["latitude"]),
            longitude=float(top["longitude"]),
            ambiguous=ambiguous,
        )
    except (KeyError, TypeError, ValueError):
        return None


async def _nominatim(client: httpx.AsyncClient, query: str, user_agent: str) -> DestinationInfo | None:
    # Nominatim policy: identify the app via User-Agent, max 1 request/second, cache results (planner caches).
    res = await client.get(
        NOMINATIM_URL,
        params={"q": query, "format": "jsonv2", "limit": 1, "accept-language": "en"},
        headers={"User-Agent": user_agent},
        timeout=httpx.Timeout(10.0, connect=5.0),
    )
    res.raise_for_status()
    return parse_nominatim(res.json(), query)


async def _open_meteo(client: httpx.AsyncClient, query: str) -> DestinationInfo | None:
    # Open-Meteo matches place names only, so "Manali, Himachal Pradesh" is searched as "Manali".
    name = query.split(",")[0].strip()
    res = await client.get(
        OPEN_METEO_GEO_URL,
        params={"name": name, "count": 10, "language": "en", "format": "json"},
        timeout=httpx.Timeout(10.0, connect=5.0),
    )
    res.raise_for_status()
    return parse_open_meteo(res.json(), query)


def _why(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        return f"HTTP {e.response.status_code}"
    return type(e).__name__


async def geocode(client: httpx.AsyncClient, query: str, user_agent: str) -> DestinationInfo:
    reachable = False  # did at least one service answer (even with "no match")?

    try:
        found = await _nominatim(client, query, user_agent)
        reachable = True
        if found:
            return found
    except (httpx.HTTPError, ValueError) as e:
        log.warning("nominatim lookup failed: %s", _why(e))

    try:
        found = await _open_meteo(client, query)
        reachable = True
        if found:
            return found
    except (httpx.HTTPError, ValueError) as e:
        log.warning("open-meteo geocoding failed: %s", _why(e))

    if reachable:
        raise DestinationNotFound(f"We couldn't find a place called '{query}'. Try a city or region name.")
    raise UpstreamUnavailable("Location lookup is temporarily unavailable.")
