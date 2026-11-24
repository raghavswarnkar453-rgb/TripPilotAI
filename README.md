# TripPilot AI
Explore more. Plan smarter. Travel better.

AI-powered multi-agent travel planner (Next.js + FastAPI + Supabase + Gemini + LangGraph).

## Structure
- `frontend/` Next.js app (port 3000)
- `backend/` FastAPI service (port 8000)
- `supabase/migrations/` SQL migrations (run in Supabase SQL Editor)
- `docs/` architecture, API and DB documentation

## Run locally
Backend:
```
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```
Frontend:
```
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```
Never commit `.env` files or API keys.
