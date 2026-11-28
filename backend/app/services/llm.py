"""Provider chain: Gemini and/or Groq, with automatic fallback and one validation retry per provider."""
import logging
from dataclasses import dataclass

import httpx

from app.core.config import Settings
from app.schemas.trip import Attraction, DestinationInfo, ItineraryPlan, TripRequest, WeatherInfo
from app.services import gemini, groq
from app.services.errors import ItineraryInvalid, NotConfigured, PlannerError

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 2  # per provider
PROVIDER_LABEL = {"gemini": "Gemini", "groq": "Groq"}


@dataclass(frozen=True)
class Provider:
    name: str  # "gemini" | "groq"
    api_key: str
    model: str

    @property
    def call(self):
        return gemini.call if self.name == "gemini" else groq.call


def configured_providers(s: Settings) -> list[Provider]:
    choice = (s.llm_provider or "auto").lower()
    out: list[Provider] = []
    if choice in ("auto", "gemini") and s.gemini_api_key and s.gemini_model:
        out.append(Provider("gemini", s.gemini_api_key, s.gemini_model))
    if choice in ("auto", "groq") and s.groq_api_key and s.groq_model:
        out.append(Provider("groq", s.groq_api_key, s.groq_model))
    return out


@dataclass
class LLMResult:
    plan: ItineraryPlan
    provider: Provider
    notes: list[str]


async def generate_plan(
    client: httpx.AsyncClient,
    settings: Settings,
    req: TripRequest,
    dest: DestinationInfo | None,
    weather: WeatherInfo,
    attractions: list[Attraction],
) -> LLMResult:
    providers = configured_providers(settings)
    if not providers:
        raise NotConfigured("The AI service is not configured on the server yet.")

    prompt = gemini.build_prompt(req, dest, weather, attractions)
    notes: list[str] = []
    last_error: PlannerError | None = None

    for provider in providers:
        label = PROVIDER_LABEL[provider.name]
        validation_error = ""
        try:
            for attempt in range(MAX_ATTEMPTS):
                user_prompt = prompt
                if validation_error:
                    user_prompt += f"\n\nYour previous reply was invalid ({validation_error}). Return only the corrected JSON."
                try:
                    text = await provider.call(client, provider.api_key, provider.model, user_prompt)
                except ItineraryInvalid as e:
                    validation_error = e.message[:300]
                    log.warning("%s gave an unusable reply (attempt %d)", provider.name, attempt + 1)
                    continue
                try:
                    plan = gemini.parse_plan(text, req.num_days)
                except ValueError as e:
                    validation_error = str(e)[:300].replace("\n", " ")
                    log.warning("%s itinerary validation failed (attempt %d)", provider.name, attempt + 1)
                    continue
                if notes:
                    notes.append(f"{label} was used to generate this plan.")
                return LLMResult(plan, provider, notes)
            raise ItineraryInvalid(f"{label} returned an itinerary we couldn't validate.")
        except PlannerError as e:
            last_error = e
            log.warning("provider %s failed: %s", provider.name, type(e).__name__)
            notes.append(f"{label} was unavailable ({e.message.rstrip('.')}).")

    assert last_error is not None
    raise last_error
