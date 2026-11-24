from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert set(body) == {
        "status", "service", "version",
        "supabase_configured", "gemini_configured", "weather_configured",
    }


def test_health_never_leaks_keys(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "super-secret")
    res = client.get("/health")
    assert "super-secret" not in res.text
