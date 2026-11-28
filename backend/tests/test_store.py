import asyncio
import datetime as dt
import json
import uuid

import httpx
import pytest

from app.schemas.trip import GenerateResponse, WeatherInfo
from app.services.errors import Unauthorized, UpstreamUnavailable
from app.services.planner import finalize_plan
from app.services.budget import compute_budget
from app.services.gemini import parse_plan
from app.services.supabase_store import SupabaseStore
from tests.test_planner import ATTRACTIONS, make_req, plan_json

TRIP_ID = str(uuid.uuid4())


def make_result() -> GenerateResponse:
    req = make_req()
    plan = finalize_plan(parse_plan(plan_json(), 2), req, ATTRACTIONS)
    return GenerateResponse(
        request=req, destination=None, weather=WeatherInfo(status="unavailable"),
        attractions=ATTRACTIONS, attractions_status="ok", itinerary=plan,
        budget=compute_budget(plan, req.budget, req.travelers), warnings=[],
        model="m", generated_at=dt.datetime.now(dt.timezone.utc),
    )


def run(handler, fn):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await fn(SupabaseStore("https://x.supabase.co", "anon", "jwt-token-value", c))
    return asyncio.run(go())


def test_save_writes_all_tables_and_uses_user_jwt():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        seen.append((request.method, path))
        assert request.headers["authorization"] == "Bearer jwt-token-value"
        assert request.headers["apikey"] == "anon"
        if request.method == "GET":
            return httpx.Response(200, json=[])  # no duplicate
        body = json.loads(request.content)
        if path.endswith("/trips"):
            return httpx.Response(201, json=[{"id": TRIP_ID}])
        if path.endswith("/itinerary_days"):
            return httpx.Response(201, json=[{"id": str(uuid.uuid4()), "day_number": d["day_number"]} for d in body])
        return httpx.Response(201, json=[])

    trip_id, already = run(handler, lambda s: s.save("user-1", "Manali trip", make_result()))
    assert str(trip_id) == TRIP_ID and already is False
    tables = [p.rsplit("/", 1)[-1] for m, p in seen if m == "POST"]
    assert tables == ["trips", "itinerary_days", "itinerary_items", "expenses", "agent_runs"]


def test_save_returns_existing_trip_instead_of_duplicating():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        return httpx.Response(200, json=[{"id": TRIP_ID}])

    trip_id, already = run(handler, lambda s: s.save("user-1", "t", make_result()))
    assert already is True and str(trip_id) == TRIP_ID


def test_failed_child_insert_rolls_back_the_trip():
    deleted = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET":
            return httpx.Response(200, json=[])
        if request.method == "DELETE":
            deleted.append(request.url.params["id"])
            return httpx.Response(204)
        body = json.loads(request.content)
        if path.endswith("/trips"):
            return httpx.Response(201, json=[{"id": TRIP_ID}])
        if path.endswith("/itinerary_days"):
            return httpx.Response(201, json=[{"id": str(uuid.uuid4()), "day_number": d["day_number"]} for d in body])
        return httpx.Response(400, json={"message": "boom"})  # items fail

    with pytest.raises(UpstreamUnavailable):
        run(handler, lambda s: s.save("user-1", "t", make_result()))
    assert deleted == [f"eq.{TRIP_ID}"]


def test_expired_token_maps_to_unauthorized():
    with pytest.raises(Unauthorized):
        run(lambda r: httpx.Response(401, json={}), lambda s: s.user_id())
