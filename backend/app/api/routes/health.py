from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    supabase_configured: bool
    gemini_configured: bool
    groq_configured: bool
    weather_configured: bool


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    s = get_settings()
    # Only booleans are returned - never expose key values.
    return HealthResponse(
        status="ok",
        service=s.app_name,
        version=s.app_version,
        supabase_configured=bool(s.supabase_url and s.supabase_anon_key),
        gemini_configured=bool(s.gemini_api_key and s.gemini_model),
        groq_configured=bool(s.groq_api_key and s.groq_model),
        weather_configured=True,  # Open-Meteo is keyless
    )
