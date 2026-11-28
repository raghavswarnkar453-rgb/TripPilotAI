# TripPilot AI - API

Base URL (local): http://localhost:8000. All errors look like `{"detail": "<safe message>"}`.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | /health | no | Config flags only (never key values) |
| POST | /api/trips/generate | no | Body: TripRequest. Returns GenerateResponse (itinerary, weather, attractions, budget, warnings) |
| POST | /api/trips | Bearer (Supabase JWT) | Body: `{title?, result: GenerateResponse}`. Returns `{id, already_saved}` |
| GET | /api/trips | Bearer | List the user's saved trips |
| GET | /api/trips/{id} | Bearer | Full saved plan (GenerateResponse) |

Status codes: 404 destination not found, 422 invalid input, 429 Gemini free-tier limit, 401 missing/expired session,
502 upstream (Gemini/Supabase) problem, 503 server not configured.

Schemas: `backend/app/schemas/trip.py` and `saved.py` (frontend mirror: `frontend/src/lib/trip-schema.ts`).
Budget figures are always estimates for the whole group, in INR.

## AI providers
`LLM_PROVIDER=auto` (default) tries Gemini first and falls back to Groq on rate limits, outages or invalid output.
Set `gemini` or `groq` to force one. The response `model` field is `provider:model`, and `warnings` says when a fallback was used.
