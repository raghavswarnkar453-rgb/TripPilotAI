import uuid

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException

from app.core.config import Settings, get_settings
from app.schemas.saved import SavedTripSummary, SaveTripRequest, SaveTripResponse
from app.schemas.trip import GenerateResponse, TripRequest
from app.services.errors import Unauthorized
from app.services.n8n import generated_payload, notify, saved_payload
from app.services.planner import generate_trip
from app.services.supabase_store import SupabaseStore

router = APIRouter(prefix="/api/trips", tags=["trips"])


def bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer ") or len(authorization) < 20:
        raise Unauthorized("Please sign in to save or view trips.")
    return authorization[7:].strip()


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    req: TripRequest, background: BackgroundTasks, settings: Settings = Depends(get_settings)
) -> GenerateResponse:
    result = await generate_trip(req, settings)
    background.add_task(notify, settings.n8n_webhook_url, settings.n8n_webhook_secret, "trip_generated", generated_payload(result))
    return result


@router.post("", response_model=SaveTripResponse)
async def save_trip(
    body: SaveTripRequest,
    background: BackgroundTasks,
    token: str = Depends(bearer_token),
    settings: Settings = Depends(get_settings),
) -> SaveTripResponse:
    async with httpx.AsyncClient(timeout=15.0) as client:
        store = SupabaseStore(settings.supabase_url, settings.supabase_anon_key, token, client)
        uid = await store.user_id()
        title = body.title or f"{body.result.request.destination} trip"
        trip_id, already = await store.save(uid, title, body.result)
    if not already:
        background.add_task(
            notify, settings.n8n_webhook_url, settings.n8n_webhook_secret, "trip_saved", saved_payload(trip_id, title, body.result)
        )
    return SaveTripResponse(id=trip_id, already_saved=already)


@router.get("", response_model=list[SavedTripSummary])
async def list_trips(
    token: str = Depends(bearer_token), settings: Settings = Depends(get_settings)
) -> list[SavedTripSummary]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        store = SupabaseStore(settings.supabase_url, settings.supabase_anon_key, token, client)
        return await store.list_trips()


@router.get("/{trip_id}", response_model=GenerateResponse)
async def get_trip(
    trip_id: uuid.UUID, token: str = Depends(bearer_token), settings: Settings = Depends(get_settings)
) -> GenerateResponse:
    async with httpx.AsyncClient(timeout=15.0) as client:
        store = SupabaseStore(settings.supabase_url, settings.supabase_anon_key, token, client)
        result = await store.get_trip(trip_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Trip not found.")
    return result
