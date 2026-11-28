"""Orchestrates one trip generation: geocode -> (weather || places) -> Gemini -> validate -> budget."""
import asyncio
import datetime as dt

import httpx

from app.core.config import Settings
from app.schemas.trip import Attraction, GenerateResponse, ItineraryPlan, TripRequest
from app.services.budget import compute_budget
from app.services.cache import TTLCache
from app.services.errors import NotConfigured
from app.services.llm import configured_providers, generate_plan
from app.services.geocode import geocode
from app.services.places import fetch_attractions
from app.services.weather import fetch_weather

_geo_cache = TTLCache(24 * 3600)
_weather_cache = TTLCache(3600)
_places_cache = TTLCache(24 * 3600)
_result_cache = TTLCache(15 * 60, max_items=64)  # protects free-tier Gemini quota on repeat clicks


def finalize_plan(plan: ItineraryPlan, req: TripRequest, attractions: list[Attraction]) -> ItineraryPlan:
    """Backend-owned fields: day numbers, dates, and coordinates (only from real place refs)."""
    for i, day in enumerate(plan.days):
        day.day_number = i + 1
        day.date = req.start_date + dt.timedelta(days=i)
        for item in day.items:
            ref = item.place_ref
            if ref is not None and 0 <= ref < len(attractions):
                item.latitude = attractions[ref].latitude
                item.longitude = attractions[ref].longitude
            else:
                item.place_ref = None
                item.latitude = None
                item.longitude = None
    return plan


async def generate_trip(req: TripRequest, settings: Settings) -> GenerateResponse:
    providers = configured_providers(settings)
    if not providers:
        raise NotConfigured("The AI service is not configured on the server yet.")

    cache_key = (tuple((p.name, p.model) for p in providers), req.model_dump_json())
    cached = _result_cache.get(cache_key)
    if cached is not None:
        return cached

    warnings: list[str] = []
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        gkey = req.destination.lower()
        dest = _geo_cache.get(gkey)
        if dest is None:
            dest = await geocode(client, req.destination, settings.nominatim_user_agent)  # raises DestinationNotFound
            _geo_cache.set(gkey, dest)

        wkey = (round(dest.latitude, 2), round(dest.longitude, 2), req.start_date, req.end_date)
        pkey = (round(dest.latitude, 2), round(dest.longitude, 2))
        weather = _weather_cache.get(wkey)
        places = _places_cache.get(pkey)

        async def _weather():
            return weather or await fetch_weather(client, dest.latitude, dest.longitude, req.start_date, req.end_date)

        async def _places():
            return places or await fetch_attractions(
                client,
                settings.overpass_url_list(),
                dest.latitude,
                dest.longitude,
                settings.nominatim_user_agent,
                {req.destination.lower(), dest.display_name.split(",")[0].strip().lower()},
            )

        weather, (attractions, attractions_status) = await asyncio.gather(_weather(), _places())
        if weather.status == "ok":
            _weather_cache.set(wkey, weather)
        if attractions_status == "ok":
            _places_cache.set(pkey, (attractions, attractions_status))

        llm = await generate_plan(client, settings, req, dest, weather, attractions)

    plan = finalize_plan(llm.plan, req, attractions)
    warnings.extend(llm.notes)
    budget = compute_budget(plan, req.budget, req.travelers)

    if dest.ambiguous:
        warnings.append(
            f"Several places are called '{req.destination}'. We used {dest.display_name}. "
            "If you meant a different one, add the state or country, for example 'Manali, Himachal Pradesh'."
        )
    if weather.status != "ok":
        warnings.append(weather.note or "Weather information is unavailable right now.")
    elif weather.source == "historical" and weather.note:
        warnings.append(weather.note)
    if attractions_status != "ok":
        warnings.append("Nearby attractions couldn't be loaded, so map pins are unavailable for this plan.")
    if budget.over_budget:
        warnings.append(
            f"The estimated total (INR {budget.total_estimated:,}) is above your budget. "
            "Try fewer days, a calmer travel style, or a bigger budget."
        )

    result = GenerateResponse(
        request=req,
        destination=dest,
        weather=weather,
        attractions=attractions,
        attractions_status=attractions_status,
        itinerary=plan,
        budget=budget,
        warnings=warnings,
        model=f"{llm.provider.name}:{llm.provider.model}",
        generated_at=dt.datetime.now(dt.timezone.utc),
    )
    _result_cache.set(cache_key, result)
    return result
