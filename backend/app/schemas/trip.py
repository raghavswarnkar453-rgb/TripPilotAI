"""API contract for TripPilot AI.

Mirrored by frontend/src/lib/trip-schema.ts - change both together.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

MAX_TRIP_DAYS = 14
_TEXT_RE = re.compile(r"^[\w\s,.'()&\-]+$")

TimeSlot = Literal["morning", "afternoon", "evening"]
TravelStyle = Literal["relaxed", "balanced", "packed"]
ExpenseCategory = Literal[
    "transport", "accommodation", "food", "tickets", "local_travel", "misc"
]
DataStatus = Literal["ok", "unavailable"]


def _clean_text(value: str, field: str) -> str:
    value = " ".join(value.split())
    if not value or not _TEXT_RE.match(value):
        raise ValueError(f"{field} contains unsupported characters")
    return value


# ---------------------------------------------------------------- request
class TripRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    destination: str = Field(min_length=2, max_length=100)
    origin: str | None = Field(default=None, max_length=100)
    start_date: dt.date = Field(validation_alias=AliasChoices("start_date", "startDate"))
    end_date: dt.date = Field(validation_alias=AliasChoices("end_date", "endDate"))
    budget: float = Field(gt=0, le=100_000_000, description="Total budget in INR")
    travelers: int = Field(
        ge=1, le=50, validation_alias=AliasChoices("travelers", "travellers")
    )
    interests: list[str] = Field(default_factory=list, max_length=8)
    travel_style: TravelStyle = Field(
        default="balanced", validation_alias=AliasChoices("travel_style", "travelStyle")
    )

    @field_validator("destination")
    @classmethod
    def _destination(cls, v: str) -> str:
        return _clean_text(v, "destination")

    @field_validator("origin")
    @classmethod
    def _origin(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        return _clean_text(v, "origin")

    @field_validator("interests")
    @classmethod
    def _interests(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for raw in v:
            item = _clean_text(raw, "interest")
            if len(item) > 30:
                raise ValueError("each interest must be at most 30 characters")
            if item.lower() not in {x.lower() for x in out}:
                out.append(item)
        return out

    @model_validator(mode="after")
    def _dates(self) -> "TripRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.start_date < dt.date.today():
            raise ValueError("start_date cannot be in the past")
        if self.num_days > MAX_TRIP_DAYS:
            raise ValueError(f"trips are limited to {MAX_TRIP_DAYS} days")
        return self

    @property
    def num_days(self) -> int:
        return (self.end_date - self.start_date).days + 1


# ------------------------------------------------------- itinerary (LLM output)
class ItineraryItem(BaseModel):
    time_slot: TimeSlot
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=800)
    duration_minutes: int | None = Field(default=None, ge=5, le=1440)
    estimated_cost: float = Field(default=0, ge=0, le=10_000_000)  # INR, whole group
    place_ref: int | None = None  # index into the attractions list, set by the model
    latitude: float | None = None  # filled by the backend from place_ref only
    longitude: float | None = None


class DayPlan(BaseModel):
    day_number: int = Field(ge=1)
    date: dt.date | None = None  # filled by the backend
    title: str = Field(default="", max_length=200)
    summary: str = Field(default="", max_length=600)
    items: list[ItineraryItem] = Field(min_length=1, max_length=8)


class CostEstimates(BaseModel):
    """Whole-trip INR estimates for ALL travellers (activities are summed from items)."""

    transport: float = Field(default=0, ge=0, le=100_000_000)
    accommodation: float = Field(default=0, ge=0, le=100_000_000)
    food: float = Field(default=0, ge=0, le=100_000_000)
    local_travel: float = Field(default=0, ge=0, le=100_000_000)
    misc: float = Field(default=0, ge=0, le=100_000_000)


class ItineraryPlan(BaseModel):
    summary: str = Field(default="", max_length=1200)
    days: list[DayPlan] = Field(min_length=1, max_length=MAX_TRIP_DAYS)
    cost_estimates: CostEstimates
    tips: list[str] = Field(default_factory=list, max_length=12)


# ------------------------------------------------------------ travel data
class DestinationInfo(BaseModel):
    query: str
    display_name: str
    latitude: float
    longitude: float
    ambiguous: bool = False  # several places share this name and the user gave no state/country to tell them apart


class WeatherDay(BaseModel):
    date: dt.date
    temp_max_c: float | None = None
    temp_min_c: float | None = None
    precipitation_mm: float | None = None
    precipitation_probability: int | None = None
    condition: str | None = None


class WeatherInfo(BaseModel):
    status: DataStatus
    source: Literal["forecast", "historical"] | None = None
    note: str | None = None
    days: list[WeatherDay] = Field(default_factory=list)


class Attraction(BaseModel):
    name: str
    category: str | None = None
    latitude: float
    longitude: float


# ---------------------------------------------------------------- budget
class BudgetLine(BaseModel):
    category: ExpenseCategory
    amount: int


class BudgetSummary(BaseModel):
    currency: Literal["INR"] = "INR"
    lines: list[BudgetLine]
    total_estimated: int
    per_traveler: int
    budget: int
    remaining: int
    over_budget: bool
    is_estimate: Literal[True] = True
    disclaimer: str = (
        "These are AI-generated estimates, not confirmed booking prices. "
        "Check real prices before you book."
    )


# -------------------------------------------------------------- response
class GenerateResponse(BaseModel):
    request: TripRequest
    destination: DestinationInfo | None
    weather: WeatherInfo
    attractions: list[Attraction]
    attractions_status: DataStatus
    itinerary: ItineraryPlan
    budget: BudgetSummary
    warnings: list[str]
    model: str
    generated_at: dt.datetime
