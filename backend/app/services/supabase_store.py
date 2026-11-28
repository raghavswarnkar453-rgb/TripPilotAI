"""Saves/loads trips through Supabase PostgREST using the *user's own JWT* + the anon key.

Row Level Security does the access control, so no service-role key is ever needed here.
"""
import logging
import uuid

import httpx

from app.schemas.saved import SavedTripSummary
from app.schemas.trip import GenerateResponse
from app.services.budget import compute_budget
from app.services.errors import NotConfigured, PlannerError, Unauthorized, UpstreamUnavailable

log = logging.getLogger(__name__)

SLOT_TIME = {"morning": "09:00:00", "afternoon": "14:00:00", "evening": "18:30:00"}


class SupabaseStore:
    def __init__(self, url: str, anon_key: str, token: str, client: httpx.AsyncClient):
        if not (url and anon_key):
            raise NotConfigured("Saving trips is not configured on the server yet.")
        self._rest = f"{url.rstrip('/')}/rest/v1"
        self._auth = f"{url.rstrip('/')}/auth/v1"
        self._headers = {"apikey": anon_key, "Authorization": f"Bearer {token}"}
        self._client = client

    async def _request(self, method: str, url: str, *, ok: tuple[int, ...] = (200, 201), **kwargs) -> httpx.Response:
        headers = {**self._headers, **kwargs.pop("headers", {})}
        try:
            res = await self._client.request(method, url, headers=headers, **kwargs)
        except httpx.HTTPError as e:
            raise UpstreamUnavailable("The database could not be reached. Please try again.") from e
        if res.status_code in (401, 403):
            raise Unauthorized("Your session has expired. Please sign in again.")
        if res.status_code not in ok:
            log.warning("supabase %s failed: status=%s", method, res.status_code)
            raise UpstreamUnavailable("The database rejected the request. Please try again.")
        return res

    async def user_id(self) -> str:
        res = await self._request("GET", f"{self._auth}/user")
        uid = res.json().get("id")
        if not uid:
            raise Unauthorized("Your session is not valid. Please sign in again.")
        return uid

    async def save(self, uid: str, title: str, result: GenerateResponse) -> tuple[uuid.UUID, bool]:
        req = result.request
        trip_filter = {
            "select": "id",
            "user_id": f"eq.{uid}",
            "destination": f"eq.{req.destination}",
            "start_date": f"eq.{req.start_date.isoformat()}",
            "end_date": f"eq.{req.end_date.isoformat()}",
            "budget": f"eq.{req.budget}",
            "travelers": f"eq.{req.travelers}",
            "limit": "1",
        }
        existing = (await self._request("GET", f"{self._rest}/trips", params=trip_filter)).json()
        if existing:
            return uuid.UUID(existing[0]["id"]), True

        prefer = {"Prefer": "return=representation"}
        trip_id: str | None = None
        try:
            trip = (
                await self._request(
                    "POST",
                    f"{self._rest}/trips",
                    headers=prefer,
                    json={
                        "user_id": uid,
                        "title": title,
                        "origin": req.origin or "Not specified",
                        "destination": req.destination,
                        "start_date": req.start_date.isoformat(),
                        "end_date": req.end_date.isoformat(),
                        "budget": req.budget,
                        "currency": "INR",
                        "travelers": req.travelers,
                        "travel_style": req.travel_style,
                        "preferences": {
                            "interests": req.interests,
                            "summary": result.itinerary.summary,
                            "tips": result.itinerary.tips,
                        },
                        "status": "planned",
                    },
                )
            ).json()[0]
            trip_id = trip["id"]

            days = (
                await self._request(
                    "POST",
                    f"{self._rest}/itinerary_days",
                    headers=prefer,
                    json=[
                        {
                            "trip_id": trip_id,
                            "day_number": d.day_number,
                            "trip_date": d.date.isoformat() if d.date else None,
                            "summary": (d.title + ": " + d.summary).strip(": ")[:600] or None,
                        }
                        for d in result.itinerary.days
                    ],
                )
            ).json()
            day_ids = {row["day_number"]: row["id"] for row in days}

            items = [
                {
                    "day_id": day_ids[d.day_number],
                    "name": it.title[:200],
                    "category": it.time_slot,
                    "description": it.description or None,
                    "latitude": it.latitude,
                    "longitude": it.longitude,
                    "start_time": SLOT_TIME[it.time_slot],
                    "duration_minutes": it.duration_minutes,
                    "estimated_cost": it.estimated_cost,
                    "currency": "INR",
                    "sort_order": n,
                }
                for d in result.itinerary.days
                for n, it in enumerate(d.items)
            ]
            await self._request("POST", f"{self._rest}/itinerary_items", json=items)

            # Never trust client-supplied totals: recompute from the itinerary.
            budget = compute_budget(result.itinerary, req.budget, req.travelers)
            expenses = [
                {
                    "trip_id": trip_id,
                    "category": line.category,
                    "description": "Estimate",
                    "amount": line.amount,
                    "currency": "INR",
                    "is_actual": False,
                }
                for line in budget.lines
                if line.amount > 0
            ]
            if expenses:
                await self._request("POST", f"{self._rest}/expenses", json=expenses)

            await self._request(
                "POST",
                f"{self._rest}/agent_runs",
                json={
                    "user_id": uid,
                    "trip_id": trip_id,
                    "input_data": req.model_dump(mode="json"),
                    "output_data": result.model_copy(update={"budget": budget}).model_dump(mode="json"),
                    "status": "success",
                },
            )
        except PlannerError:
            if trip_id:  # child rows cascade-delete
                try:
                    await self._request("DELETE", f"{self._rest}/trips", params={"id": f"eq.{trip_id}"}, ok=(200, 204))
                except PlannerError:
                    log.error("rollback of partial trip %s failed", trip_id)
            raise
        return uuid.UUID(trip_id), False

    async def list_trips(self) -> list[SavedTripSummary]:
        res = await self._request(
            "GET",
            f"{self._rest}/trips",
            params={
                "select": "id,title,destination,start_date,end_date,budget,travelers,created_at",
                "order": "created_at.desc",
                "limit": "50",
            },
        )
        return [SavedTripSummary.model_validate(row) for row in res.json()]

    async def get_trip(self, trip_id: uuid.UUID) -> GenerateResponse | None:
        res = await self._request(
            "GET",
            f"{self._rest}/agent_runs",
            params={
                "select": "output_data",
                "trip_id": f"eq.{trip_id}",
                "status": "eq.success",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
        rows = res.json()
        if not rows or not rows[0].get("output_data"):
            return None
        return GenerateResponse.model_validate(rows[0]["output_data"])
