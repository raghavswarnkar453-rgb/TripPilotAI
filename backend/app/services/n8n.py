"""Optional n8n hook. Sends small trip-event summaries to an n8n webhook; never affects the user's request.

Privacy: payloads carry trip details only - no user id, email, tokens or API keys.
"""
import datetime as dt
import logging
import uuid

import httpx

from app.schemas.trip import GenerateResponse

log = logging.getLogger(__name__)


def generated_payload(r: GenerateResponse) -> dict:
    return {
        "destination": r.destination.display_name if r.destination else r.request.destination,
        "start_date": r.request.start_date.isoformat(),
        "end_date": r.request.end_date.isoformat(),
        "travelers": r.request.travelers,
        "budget": r.request.budget,
        "estimated_total": r.budget.total_estimated,
        "over_budget": r.budget.over_budget,
        "weather_source": r.weather.source if r.weather.status == "ok" else None,
        "attractions_status": r.attractions_status,
        "warnings": len(r.warnings),
        "model": r.model,
    }


def saved_payload(trip_id: uuid.UUID, title: str, r: GenerateResponse) -> dict:
    return {"trip_id": str(trip_id), "title": title, **generated_payload(r)}


async def notify(url: str, secret: str, event: str, data: dict) -> None:
    """Best-effort POST to n8n. Short timeout, errors are logged and swallowed."""
    if not url:
        return
    headers = {"X-TripPilot-Secret": secret} if secret else {}
    body = {"event": event, "sent_at": dt.datetime.now(dt.timezone.utc).isoformat(), "data": data}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(4.0, connect=2.0)) as client:
            res = await client.post(url, json=body, headers=headers)
        if res.status_code >= 400:
            log.warning("n8n webhook returned HTTP %s (is the workflow active?)", res.status_code)
    except httpx.HTTPError as e:
        log.warning("n8n webhook unreachable: %s", type(e).__name__)
