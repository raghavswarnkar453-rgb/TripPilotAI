import asyncio
import datetime as dt
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.trip import Attraction, TripRequest, WeatherInfo
from app.core.config import Settings
from app.services import gemini, llm
from app.services.budget import compute_budget
from app.services.errors import ItineraryInvalid, RateLimited
from app.services.planner import finalize_plan

client = TestClient(app)
START = dt.date.today() + dt.timedelta(days=10)


def make_req(days: int = 2) -> TripRequest:
    return TripRequest(
        destination="Manali",
        start_date=START,
        end_date=START + dt.timedelta(days=days - 1),
        budget=20000,
        travelers=2,
        interests=["Adventure", "Food"],
    )


def plan_json(days: int = 2) -> str:
    return json.dumps(
        {
            "summary": "A short trip.",
            "days": [
                {
                    "day_number": i + 1,
                    "title": f"Day {i + 1}",
                    "summary": "Explore.",
                    "items": [
                        {"time_slot": "morning", "title": "Walk", "estimated_cost": 100, "place_ref": 0},
                        {"time_slot": "evening", "title": "Dinner", "estimated_cost": 500, "place_ref": 99},
                    ],
                }
                for i in range(days)
            ],
            "cost_estimates": {"transport": 6000, "accommodation": 8000, "food": 3000, "local_travel": 1000, "misc": 500},
            "tips": ["Carry a jacket."],
        }
    )


ATTRACTIONS = [Attraction(name="Hadimba Temple", category="historic", latitude=32.24, longitude=77.18)]


def test_parse_plan_accepts_fenced_json_and_truncates_extra_days():
    plan = gemini.parse_plan("```json\n" + plan_json(3) + "\n```", expected_days=2)
    assert len(plan.days) == 2


def test_parse_plan_rejects_too_few_days_and_garbage():
    with pytest.raises(ValueError):
        gemini.parse_plan(plan_json(1), expected_days=2)
    with pytest.raises(ValueError):
        gemini.parse_plan("sorry, I can't do that", expected_days=2)


def test_finalize_sets_dates_and_only_real_coordinates():
    req = make_req()
    plan = finalize_plan(gemini.parse_plan(plan_json(), 2), req, ATTRACTIONS)
    assert [d.date for d in plan.days] == [START, START + dt.timedelta(days=1)]
    first, second = plan.days[0].items
    assert (first.latitude, first.longitude) == (32.24, 77.18)
    assert second.place_ref is None and second.latitude is None  # out-of-range ref is dropped


def test_budget_lines_sum_to_total_and_flag_over_budget():
    plan = finalize_plan(gemini.parse_plan(plan_json(), 2), make_req(), ATTRACTIONS)
    b = compute_budget(plan, budget=10000, travelers=2)
    assert b.total_estimated == sum(line.amount for line in b.lines)
    assert b.remaining == 10000 - b.total_estimated
    assert b.over_budget is True and b.is_estimate is True


def _gemini_reply(text: str) -> httpx.Response:
    return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]})


def _run(handler, **settings):
    cfg = Settings(gemini_api_key="key", gemini_model="model-x", **settings)

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await llm.generate_plan(c, cfg, make_req(), None, WeatherInfo(status="unavailable"), ATTRACTIONS)

    return asyncio.run(go())


def test_gemini_retries_once_on_invalid_json_then_succeeds():
    replies = iter(["not json", plan_json()])
    res = _run(lambda request: _gemini_reply(next(replies)))
    assert len(res.plan.days) == 2 and res.provider.name == "gemini"


def test_gemini_gives_up_after_two_invalid_replies():
    with pytest.raises(ItineraryInvalid):
        _run(lambda request: _gemini_reply("still not json"))


def test_gemini_429_maps_to_rate_limited_without_leaking_key():
    with pytest.raises(RateLimited) as e:
        _run(lambda request: httpx.Response(429, text="quota"))
    assert "key" not in e.value.message.lower()


def test_generate_route_validates_input():
    res = client.post("/api/trips/generate", json={"destination": "Manali", "start_date": "2020-01-01", "end_date": "2020-01-02", "budget": 1000, "travelers": 1})
    assert res.status_code == 422


def test_generate_route_503_when_gemini_not_configured():
    from app.core.config import Settings, get_settings

    app.dependency_overrides[get_settings] = lambda: Settings(gemini_api_key="", gemini_model="")
    try:
        res = client.post(
            "/api/trips/generate",
            json={"destination": "Manali", "start_date": START.isoformat(), "end_date": START.isoformat(), "budget": 5000, "travelers": 1},
        )
    finally:
        app.dependency_overrides.clear()
    assert res.status_code == 503
    assert "detail" in res.json()


def test_trip_endpoints_require_auth():
    assert client.get("/api/trips").status_code == 401
    assert client.post("/api/trips", json={}).status_code in (401, 422)


def _groq_reply(text: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


def _router(gemini_resp, groq_resp):
    def handler(request: httpx.Request) -> httpx.Response:
        return gemini_resp(request) if "googleapis" in request.url.host else groq_resp(request)

    return handler


def test_falls_back_to_groq_when_gemini_rate_limited():
    res = _run(
        _router(lambda r: httpx.Response(429), lambda r: _groq_reply(plan_json())),
        groq_api_key="gk", groq_model="llama-x",
    )
    assert res.provider.name == "groq"
    assert any("Gemini was unavailable" in n for n in res.notes)


def test_falls_back_to_groq_when_gemini_output_is_invalid_twice():
    res = _run(
        _router(lambda r: _gemini_reply("nope"), lambda r: _groq_reply(plan_json())),
        groq_api_key="gk", groq_model="llama-x",
    )
    assert res.provider.name == "groq"


def test_groq_only_mode_never_calls_gemini():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "groq.com" in request.url.host
        assert request.headers["authorization"] == "Bearer gk"
        return _groq_reply(plan_json())

    res = _run(handler, groq_api_key="gk", groq_model="llama-x", llm_provider="groq")
    assert res.provider.name == "groq"


def test_error_raised_when_every_provider_fails():
    with pytest.raises(RateLimited):
        _run(lambda r: httpx.Response(429), groq_api_key="gk", groq_model="llama-x")


def test_no_provider_configured_raises():
    from app.services.errors import NotConfigured

    async def go():
        async with httpx.AsyncClient() as c:
            await llm.generate_plan(c, Settings(), make_req(), None, WeatherInfo(status="unavailable"), ATTRACTIONS)

    with pytest.raises(NotConfigured):
        asyncio.run(go())


def test_overpass_falls_back_to_second_server_and_sends_user_agent():
    from app.services.places import fetch_attractions

    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.host, request.headers.get("user-agent")))
        if request.url.host == "a.example":
            return httpx.Response(406)
        return httpx.Response(200, json={"elements": [{"lat": 32.2, "lon": 77.1, "tags": {"name": "Hadimba Temple", "historic": "temple"}}]})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await fetch_attractions(c, ["https://a.example/api", "https://b.example/api"], 32.2, 77.1, "TestUA/1.0")

    items, status = asyncio.run(go())
    assert status == "ok" and items[0].name == "Hadimba Temple"
    assert [h for h, _ in seen] == ["a.example", "b.example"]
    assert all(ua == "TestUA/1.0" for _, ua in seen)


def test_overpass_unavailable_when_all_servers_fail():
    from app.services.places import fetch_attractions

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(429))) as c:
            return await fetch_attractions(c, ["https://a.example/x", "https://b.example/x"], 1.0, 1.0, "UA")

    assert asyncio.run(go()) == ([], "unavailable")


def test_groq_malformed_json_400_is_retried_not_reported_as_bad_key():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(400, json={"error": {"code": "json_validate_failed", "message": "Failed to generate JSON"}})
        body = json.loads(request.content)
        assert body["reasoning_effort"] == "low" and body["max_tokens"] == 6000
        return _groq_reply(plan_json())

    cfg = Settings(groq_api_key="gk", groq_model="openai/gpt-oss-120b", llm_provider="groq")

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await llm.generate_plan(c, cfg, make_req(), None, WeatherInfo(status="unavailable"), ATTRACTIONS)

    res = asyncio.run(go())
    assert len(calls) == 2 and res.provider.name == "groq"


def test_groq_real_auth_error_still_reports_configuration_problem():
    from app.services.errors import UpstreamUnavailable

    cfg = Settings(groq_api_key="bad", groq_model="m", llm_provider="groq")

    async def go():
        t = httpx.MockTransport(lambda r: httpx.Response(401, json={"error": {"message": "Invalid API Key"}}))
        async with httpx.AsyncClient(transport=t) as c:
            await llm.generate_plan(c, cfg, make_req(), None, WeatherInfo(status="unavailable"), ATTRACTIONS)

    with pytest.raises(UpstreamUnavailable) as e:
        asyncio.run(go())
    assert "GROQ_API_KEY" in e.value.message


def test_wikipedia_fallback_used_when_every_overpass_server_fails():
    from app.services.places import fetch_attractions

    def handler(request: httpx.Request) -> httpx.Response:
        if "wikipedia.org" in request.url.host:
            assert request.headers["user-agent"] == "UA/1"
            return httpx.Response(200, json={"query": {"geosearch": [
                {"title": "Manali", "lat": 32.24, "lon": 77.18},           # the destination itself: skipped
                {"title": "Hadimba Temple", "lat": 32.248, "lon": 77.180},
                {"title": "Solang Valley", "lat": 32.316, "lon": 77.158},
            ]}})
        return httpx.Response(502, text="at capacity")

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await fetch_attractions(c, ["https://a.example/x", "https://b.example/x"], 32.2, 77.1, "UA/1", {"manali"})

    items, status = asyncio.run(go())
    assert status == "ok"
    assert [a.name for a in items] == ["Hadimba Temple", "Solang Valley"]


def test_overpass_url_list_parses_comma_separated_setting():
    cfg = Settings(overpass_urls=" https://a.example/x , https://b.example/y ,")
    assert cfg.overpass_url_list() == ["https://a.example/x", "https://b.example/y"]


def test_slow_overpass_server_does_not_block_the_next_one(monkeypatch):
    import time

    from app.services import places

    monkeypatch.setattr(places, "STAGGER_SECONDS", 0.05)

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "slow.example":
            await asyncio.sleep(30)  # hangs like a dead server
        return httpx.Response(200, json={"elements": [{"lat": 1.0, "lon": 2.0, "tags": {"name": "Fort", "historic": "fort"}}]})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await places.fetch_attractions(c, ["https://slow.example/x", "https://fast.example/x"], 1.0, 2.0, "UA")

    started = time.monotonic()
    items, status = asyncio.run(go())
    assert status == "ok" and items[0].name == "Fort"
    assert time.monotonic() - started < 3  # did not wait for the 30 s hang


def test_overall_deadline_then_wikipedia(monkeypatch):
    import time

    from app.services import places

    monkeypatch.setattr(places, "STAGGER_SECONDS", 0.05)
    monkeypatch.setattr(places, "OVERPASS_DEADLINE", 0.3)

    async def handler(request: httpx.Request) -> httpx.Response:
        if "wikipedia.org" in request.url.host:
            return httpx.Response(200, json={"query": {"geosearch": [{"title": "Old Fort", "lat": 1.0, "lon": 2.0}]}})
        await asyncio.sleep(30)
        return httpx.Response(200, json={})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await places.fetch_attractions(c, ["https://a.example/x", "https://b.example/x"], 1.0, 2.0, "UA")

    started = time.monotonic()
    items, status = asyncio.run(go())
    assert status == "ok" and items[0].name == "Old Fort"
    assert time.monotonic() - started < 3


def test_wikipedia_results_drop_destination_and_non_tourist_pages():
    from app.services.places import parse_wikipedia

    rows = [
        {"title": "Manali", "lat": 1, "lon": 1},
        {"title": "Manali, Himachal Pradesh", "lat": 1, "lon": 1},
        {"title": "Manali Assembly constituency", "lat": 1, "lon": 1},
        {"title": "Leh\u2013Manali Highway", "lat": 1, "lon": 1},
        {"title": "Manali Sanctuary", "lat": 1.1, "lon": 1.1},
        {"title": "Hidimba Devi Temple", "lat": 1.2, "lon": 1.2},
        {"title": "No coordinates"},
    ]
    names = [a.name for a in parse_wikipedia({"query": {"geosearch": rows}}, {"manali"})]
    assert names == ["Manali Sanctuary", "Hidimba Devi Temple"]


def test_slow_but_working_third_server_beats_wikipedia(monkeypatch):
    """Mirrors the real outage: servers 1-2 hang, server 3 answers slowly but correctly."""
    from app.services import places

    monkeypatch.setattr(places, "STAGGER_SECONDS", 0.05)
    monkeypatch.setattr(places, "OVERPASS_DEADLINE", 2.0)

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host in ("hang1.example", "hang2.example"):
            await asyncio.sleep(30)
        if request.url.host == "slow.example":
            await asyncio.sleep(0.5)
            return httpx.Response(200, json={"elements": [{"lat": 1.0, "lon": 2.0, "tags": {"name": "Aleo Viewpoint", "tourism": "viewpoint"}}]})
        return httpx.Response(200, json={"query": {"geosearch": [{"title": "Wiki Place", "lat": 1.0, "lon": 2.0}]}})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            urls = ["https://hang1.example/x", "https://hang2.example/x", "https://slow.example/x"]
            return await places.fetch_attractions(c, urls, 1.0, 2.0, "UA")

    items, status = asyncio.run(go())
    assert status == "ok" and items[0].name == "Aleo Viewpoint"


# ------------------------------------------------------------------ geocoding
def _geo(handler, query="Manali"):
    from app.services.geocode import geocode

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await geocode(c, query, "UA/1")

    return asyncio.run(go())


OPEN_METEO_HIT = {"results": [{"name": "Manali", "admin1": "Himachal Pradesh", "country": "India", "latitude": 32.24, "longitude": 77.18}]}


def test_geocode_uses_open_meteo_when_nominatim_blocks():
    def handler(request: httpx.Request) -> httpx.Response:
        if "nominatim" in request.url.host:
            return httpx.Response(403)
        assert request.url.params["name"] == "Manali"
        return httpx.Response(200, json=OPEN_METEO_HIT)

    dest = _geo(handler, "Manali, Himachal Pradesh")  # comma query is searched as "Manali" on Open-Meteo
    assert (dest.latitude, dest.longitude) == (32.24, 77.18)
    assert dest.display_name == "Manali, Himachal Pradesh, India"


def test_geocode_prefers_nominatim_when_it_works():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "nominatim" in request.url.host  # fallback must not be called
        return httpx.Response(200, json=[{"lat": "32.2", "lon": "77.1", "display_name": "Manali, Kullu, India"}])

    assert _geo(handler).display_name == "Manali, Kullu, India"


def test_geocode_unavailable_only_when_both_services_fail():
    from app.services.errors import UpstreamUnavailable

    with pytest.raises(UpstreamUnavailable):
        _geo(lambda r: httpx.Response(503))


def test_geocode_not_found_when_services_answer_with_no_match():
    from app.services.errors import DestinationNotFound

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[] if "nominatim" in request.url.host else {})

    with pytest.raises(DestinationNotFound):
        _geo(handler, "Qwertyuiopland")


MANALI_RESULTS = {"results": [
    {"name": "Manali", "admin1": "Tamil Nadu", "admin2": "Chennai district", "country": "India", "latitude": 13.17, "longitude": 80.27},
    {"name": "Manali", "admin1": "Himachal Pradesh", "admin2": "Kullu", "country": "India", "latitude": 32.24, "longitude": 77.18},
]}


def test_open_meteo_uses_state_from_query_to_pick_the_right_place():
    from app.services.geocode import parse_open_meteo

    dest = parse_open_meteo(MANALI_RESULTS, "Manali, Himachal Pradesh")
    assert (dest.latitude, dest.longitude) == (32.24, 77.18)
    assert dest.ambiguous is False


def test_open_meteo_flags_ambiguous_name_instead_of_guessing_silently():
    from app.services.geocode import parse_open_meteo

    dest = parse_open_meteo(MANALI_RESULTS, "Manali")
    assert dest.ambiguous is True
    assert "Tamil Nadu" in dest.display_name  # still returns its best guess, but flagged


def test_open_meteo_single_match_is_not_ambiguous():
    from app.services.geocode import parse_open_meteo

    assert parse_open_meteo(OPEN_METEO_HIT, "Manali").ambiguous is False


def test_planner_warns_when_destination_match_was_a_guess(monkeypatch):
    from app.schemas.trip import DestinationInfo
    from app.services import planner
    from app.services.llm import LLMResult, Provider

    async def fake_geocode(client, query, ua):
        return DestinationInfo(query=query, display_name="Manali, Chennai district, Tamil Nadu, India", latitude=13.17, longitude=80.27, ambiguous=True)

    async def fake_weather(*a, **k):
        return WeatherInfo(status="unavailable")

    async def fake_places(*a, **k):
        return [], "unavailable"

    async def fake_plan(client, settings, req, dest, weather, attractions):
        return LLMResult(gemini.parse_plan(plan_json(), req.num_days), Provider("groq", "k", "m"), [])

    monkeypatch.setattr(planner, "geocode", fake_geocode)
    monkeypatch.setattr(planner, "fetch_weather", fake_weather)
    monkeypatch.setattr(planner, "fetch_attractions", fake_places)
    monkeypatch.setattr(planner, "generate_plan", fake_plan)

    res = asyncio.run(planner.generate_trip(make_req(), Settings(groq_api_key="k", groq_model="m", llm_provider="groq")))
    assert any("Several places are called" in w and "Himachal Pradesh" in w for w in res.warnings)
