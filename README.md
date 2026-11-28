# TripPilot AI

**Explore more. Plan smarter. Travel better.**
An AI travel planner: enter a destination, dates, budget (INR), travellers and interests, and get a day-by-day
itinerary with weather, a map, and a budget estimate. Built with free tiers only (Rs 0).

## How it works
```
Browser (Next.js)  --->  FastAPI backend  --->  Geocoding (Nominatim / Open-Meteo)
        |                    |                   Weather   (Open-Meteo)
        |                    |                   Places    (OpenStreetMap Overpass, Wikipedia fallback)
        |                    |                   AI        (Gemini, Groq as automatic fallback)
        |                    +--> Supabase (Auth + Postgres with Row Level Security)
        |                    +--> n8n (optional automation: events + intake webhook)
        +--> Supabase Auth (sign in / sign up, anon key only)
```
- **Grounded, validated AI:** the model may only pick places from real map data; its JSON is validated by a schema
  before display, retried once, and falls back to the second provider. Live data is never invented: if weather or
  places can't be loaded the app says so.
- **Budget:** computed in code from the itinerary (never trusted from the model) and always labelled an estimate.
- **Security:** secrets only in `.env` files; the frontend uses the public anon key; saving uses the user's own login
  token so Row Level Security protects every row; no service-role key in the app.

## Features
Smart trip form with validation - AI day-wise itinerary (morning/afternoon/evening, durations, costs) - weather
(live forecast within ~15 days, otherwise last year's dates, clearly labelled) - interactive map with day-coloured pins -
budget breakdown (total, per traveller, remaining) - save trips and reopen them - responsive for phone and desktop.

## Run locally (Windows)
Fastest: fill in the env files below, then double-click **`start-demo.bat`**.

Backend (`backend/`):
```
py -3.12 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env         (then fill it in)
python scripts\check_llm.py    (lists model names your keys can use)
uvicorn app.main:app --reload --port 8000
```
Frontend (`frontend/`):
```
npm install
copy .env.local.example .env.local   (then fill it in)
npm run dev
```
Database: run `supabase/migrations/001_initial_schema.sql` in the Supabase SQL Editor. For demos, turn off
"Confirm email" under Authentication > Providers > Email.

| File | Keys |
|---|---|
| `backend/.env` | `GEMINI_API_KEY`, `GEMINI_MODEL`, `GROQ_API_KEY`, `GROQ_MODEL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `NOMINATIM_USER_AGENT` (your email), optional `N8N_WEBHOOK_URL` |
| `frontend/.env.local` | `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` |

Never commit `.env` files or API keys.

## Tests
`cd backend && python -m pytest -q` (backend, all external services mocked). `cd frontend && npm run lint && npm run build`.

## API
See `docs/api-documentation.md`. n8n workflows and setup: `docs/n8n.md` (files in `n8n/`).

## Limits (honest)
Costs are AI estimates, not booking prices. Free API tiers have rate limits. Public map servers (Overpass) are
sometimes overloaded, so the app falls back to Wikipedia for nearby places. No bookings or payments in this MVP.

## Team
Frontend - Backend & database - AI - n8n & integrations - QA & deployment.
