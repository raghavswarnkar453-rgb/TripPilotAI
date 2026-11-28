import datetime as dt
import logging

import httpx

from app.schemas.trip import WeatherDay, WeatherInfo

log = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_MAX_AHEAD_DAYS = 15  # Open-Meteo forecasts cover today .. today+15

_WMO = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Freezing fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    56: "Freezing drizzle", 57: "Freezing drizzle", 61: "Light rain", 63: "Rain",
    65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain", 71: "Light snow",
    73: "Snow", 75: "Heavy snow", 77: "Snow grains", 80: "Light showers", 81: "Showers",
    82: "Heavy showers", 85: "Light snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


def _num(values: list, idx: int) -> float | None:
    try:
        v = values[idx]
    except IndexError:
        return None
    return float(v) if v is not None else None


def parse_daily(payload: dict, target_dates: list[dt.date] | None = None) -> list[WeatherDay]:
    daily = payload.get("daily") or {}
    times = daily.get("time") or []
    cols = {
        k: daily.get(k) or []
        for k in (
            "temperature_2m_max", "temperature_2m_min", "precipitation_sum",
            "precipitation_probability_max", "weather_code",
        )
    }
    days: list[WeatherDay] = []
    for i, t in enumerate(times):
        if target_dates is not None:
            if i >= len(target_dates):
                break
            day = target_dates[i]
        else:
            day = dt.date.fromisoformat(t)
        prob = _num(cols["precipitation_probability_max"], i)
        code = _num(cols["weather_code"], i)
        days.append(
            WeatherDay(
                date=day,
                temp_max_c=_num(cols["temperature_2m_max"], i),
                temp_min_c=_num(cols["temperature_2m_min"], i),
                precipitation_mm=_num(cols["precipitation_sum"], i),
                precipitation_probability=int(prob) if prob is not None else None,
                condition=_WMO.get(int(code)) if code is not None else None,
            )
        )
    return days


def _minus_year(d: dt.date) -> dt.date:
    try:
        return d.replace(year=d.year - 1)
    except ValueError:  # 29 Feb
        return d.replace(year=d.year - 1, day=28)


def _unavailable(note: str) -> WeatherInfo:
    return WeatherInfo(status="unavailable", note=note)


async def fetch_weather(
    client: httpx.AsyncClient,
    lat: float,
    lon: float,
    start: dt.date,
    end: dt.date,
    today: dt.date | None = None,
) -> WeatherInfo:
    """Never raises and never invents data: returns status='unavailable' on any failure."""
    today = today or dt.date.today()
    daily_vars = "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum"
    try:
        if end <= today + dt.timedelta(days=FORECAST_MAX_AHEAD_DAYS):
            res = await client.get(
                FORECAST_URL,
                params={
                    "latitude": lat, "longitude": lon, "timezone": "auto",
                    "daily": daily_vars + ",precipitation_probability_max",
                    "start_date": start.isoformat(), "end_date": end.isoformat(),
                },
            )
            res.raise_for_status()
            days = parse_daily(res.json())
            if not days:
                return _unavailable("No forecast was returned for these dates.")
            return WeatherInfo(status="ok", source="forecast", days=days)

        # Trip is beyond the forecast horizon: show what the same dates looked like last year.
        trip_dates = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
        res = await client.get(
            ARCHIVE_URL,
            params={
                "latitude": lat, "longitude": lon, "timezone": "auto",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
                "start_date": _minus_year(start).isoformat(),
                "end_date": _minus_year(end).isoformat(),
            },
        )
        res.raise_for_status()
        days = parse_daily(res.json(), target_dates=trip_dates)
        if not days:
            return _unavailable("No weather data is available for these dates yet.")
        return WeatherInfo(
            status="ok",
            source="historical",
            note=(
                "A live forecast isn't available this far ahead. These figures are the weather "
                "observed on the same dates last year - a rough guide only, not a forecast."
            ),
            days=days,
        )
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as e:
        log.warning("weather lookup failed: %s", type(e).__name__)
        return _unavailable("Weather service is temporarily unavailable.")
