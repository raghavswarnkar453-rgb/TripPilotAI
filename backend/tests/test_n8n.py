import asyncio
import json

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.services import n8n
from tests.test_store import make_result

client = TestClient(app)


def test_notify_posts_event_with_secret_and_no_personal_data(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["secret"] = request.headers.get("x-trippilot-secret")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200)

    real = httpx.AsyncClient
    monkeypatch.setattr(n8n.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    asyncio.run(n8n.notify("http://n8n.test/hook", "s3cret", "trip_generated", n8n.generated_payload(make_result())))
    assert seen["secret"] == "s3cret"
    assert seen["body"]["event"] == "trip_generated"
    data = seen["body"]["data"]
    assert data["destination"] == "Manali" and data["budget"] == 20000
    assert not {"user_id", "email", "token"} & set(data)


def test_notify_never_raises_when_n8n_is_down():
    asyncio.run(n8n.notify("http://127.0.0.1:1/hook", "", "trip_generated", {}))  # connection refused
    asyncio.run(n8n.notify("", "", "trip_generated", {}))  # disabled


def test_generate_route_fires_event_after_responding(monkeypatch):
    calls = []

    async def fake_generate(req, settings):
        return make_result()

    async def fake_notify(url, secret, event, data):
        calls.append((url, event, data["destination"]))

    monkeypatch.setattr("app.api.routes.trips.generate_trip", fake_generate)
    monkeypatch.setattr("app.api.routes.trips.notify", fake_notify)
    app.dependency_overrides[get_settings] = lambda: Settings(n8n_webhook_url="http://n8n.test/hook")
    try:
        res = client.post(
            "/api/trips/generate",
            json={"destination": "Manali", "start_date": make_result().request.start_date.isoformat(),
                  "end_date": make_result().request.start_date.isoformat(), "budget": 5000, "travelers": 1},
        )
    finally:
        app.dependency_overrides.clear()
    assert res.status_code == 200
    assert calls == [("http://n8n.test/hook", "trip_generated", "Manali")]
