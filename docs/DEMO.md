# Demo guide

## 30 minutes before
1. Plug in the laptop. Close heavy apps. Connect to reliable Wi-Fi; keep **your phone hotspot ready** as a backup
   (college Wi-Fi sometimes blocks map servers).
2. Start Docker Desktop and make sure the **n8n** container is running (http://localhost:5678). In n8n, confirm
   **WF-01** (and WF-02) show **Active**.
3. Double-click **`start-demo.bat`**. It starts both servers, pre-warms Manali / Goa / Jaipur, and opens the app.
   Expect `[ OK ]` lines. If a line says `[FAIL]`, read the message (usually a key or model name in `backend\.env`).
4. Open http://localhost:8000/health - expect `"status":"ok"`, `supabase_configured` and at least one of
   `gemini_configured` / `groq_configured` true.
5. In the app: **sign up / sign in**, generate **one** trip, click **Save trip**, check **My trips** shows it.
   Now your demo account already has a saved trip as a safety net.
6. Zoom the browser to 110-125% so the back row can read it. Close the DevTools.

## Live demo (about 5 minutes)
1. **Problem (20 s):** planning a trip means 10 tabs - weather, places, costs. TripPilot does it in one step.
2. **Generate (60 s):** click "Manali, Himachal Pradesh", keep the default dates (live forecast), budget 20000,
   2 travellers, pick Adventure + Food, click *Generate*. While it loads, explain the pipeline: geocode, weather,
   places, AI, validation, budget.
3. **Walk the tabs (90 s):** Itinerary (morning/afternoon/evening, costs) - Map (day-coloured pins, click a stop list link) -
   Budget (per-traveller, remaining, "estimates only") - Weather (point out the honest "live forecast" label).
4. **Save and reopen (30 s):** Save trip, open *My trips*, open it again.
5. **n8n (60 s):** run the curl from `docs/n8n.md`, show the response, then open n8n > Executions and show the run.
6. **Architecture (30 s):** README diagram. Mention free tiers, RLS, Gemini + Groq fallback.

## If something breaks
| Problem | Do this |
|---|---|
| Generate is slow (> 40 s) | It is probably the AI free-tier. Wait, or set `LLM_PROVIDER=groq` (or `gemini`) in `backend\.env` and restart the backend. |
| "busy (free-tier limit)" | Wait 1 minute, or switch provider as above. |
| Map background grey | Network blocks the map servers: pins and the "Stops on the map" list still work. Switch to hotspot. |
| "Location lookup unavailable" | Retry once; or type the place with its state, e.g. `Manali, Himachal Pradesh`. |
| Backend not reachable | The backend window was closed. Re-run `start-demo.bat`. |
| Everything fails | Open the saved trip in *My trips* (it loads from the database) and demo from that. |

## Questions you may get
- **How do you stop the AI making things up?** It may only choose from real map places, output is schema-validated and
  retried, costs are recomputed in code, and weather/places are never fabricated when an API fails.
- **Why n8n?** It automates around the app (intake webhook, event notifications) without changing the core backend; the app
  still works if n8n is off.
- **Is user data safe?** Row Level Security in Supabase, public anon key only in the browser, secrets in `.env`, trips saved
  with the user's own login token.
- **What does it cost?** Rs 0: free tiers of Gemini, Groq, Supabase, Open-Meteo, OpenStreetMap, Wikipedia.
- **Limitations?** Estimates not bookings; free API rate limits; weather beyond ~15 days is last year's data (labelled).
