from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TripPilot AI API"
    app_version: str = "0.1.0"

    frontend_url: str = "http://localhost:3000"

    gemini_api_key: str = ""
    gemini_model: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    openweather_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
