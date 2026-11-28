from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TripPilot AI API"
    app_version: str = "0.1.0"

    frontend_url: str = "http://localhost:3000"

    gemini_api_key: str = ""
    gemini_model: str = ""  # set in .env; run `python scripts/check_llm.py` to find one your key can use
    groq_api_key: str = ""
    groq_model: str = ""  # e.g. a Llama model; `python scripts/check_llm.py` lists what your key can use
    # auto = Gemini first, Groq as fallback | gemini | groq
    llm_provider: str = "auto"
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # Open-Meteo needs no key. Overpass/Nominatim are public services with usage policies.
    # Optional n8n automation hook. Leave empty to disable. Example: http://localhost:5678/webhook/trippilot/trip-events
    n8n_webhook_url: str = ""
    n8n_webhook_secret: str = ""

    # Comma-separated, tried in order. Public servers are often at capacity, so we list several.
    overpass_urls: str = (
        "https://overpass-api.de/api/interpreter,"
        "https://overpass.private.coffee/api/interpreter,"
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter,"
        "https://overpass.osm.jp/api/interpreter"
    )
    nominatim_user_agent: str = "TripPilotAI/0.1 (college project; set NOMINATIM_USER_AGENT in .env)"


    def overpass_url_list(self) -> list[str]:
        return [u.strip() for u in self.overpass_urls.split(",") if u.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
