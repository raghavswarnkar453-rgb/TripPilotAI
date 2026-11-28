"""Schemas for saving / listing trips. Mirrored by frontend/src/lib/trip-schema.ts."""
import datetime as dt
import uuid

from pydantic import BaseModel, Field

from app.schemas.trip import GenerateResponse


class SaveTripRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    result: GenerateResponse


class SaveTripResponse(BaseModel):
    id: uuid.UUID
    already_saved: bool = False


class SavedTripSummary(BaseModel):
    id: uuid.UUID
    title: str
    destination: str
    start_date: dt.date
    end_date: dt.date
    budget: float
    travelers: int
    created_at: dt.datetime
