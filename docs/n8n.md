# n8n integration (optional)

FastAPI does all the real work. n8n adds two things around it, so the app still works with n8n switched off.

| Workflow | Direction | What it does |
|---|---|---|
| **WF-01 Trip Request Intake** | you -> n8n -> backend | Webhook `POST /webhook/trippilot/trip-request` accepts a trip request, normalises it, calls the backend's `/api/trips/generate` and returns the itinerary. The backend does the validation and returns 422 with a clear message for bad input. |
| **WF-02 Trip Events** | backend -> n8n | The backend sends `trip_generated` and `trip_saved` events to `POST /webhook/trippilot/trip-events`. The workflow turns them into a readable summary; add Gmail, Telegram or Google Sheets after it. |

## 1. Import and activate
1. Open http://localhost:5678. If you already have a "WF-01 - Trip Request Intake", deactivate or delete it first: two active workflows cannot share the path `trippilot/trip-request`.
2. Workflows -> menu -> **Import from file**: `n8n/WF-01-trip-request-intake.json`, then repeat for `n8n/WF-02-trip-events.json`.
3. Open each workflow and switch **Active** on (top right). Production URLs (`/webhook/...`) only work for active workflows. The `/webhook-test/...` URL works only while you click "Listen for test event".

## 2. Point the backend at n8n (WF-02)
In `backend/.env`:
```
N8N_WEBHOOK_URL=http://localhost:5678/webhook/trippilot/trip-events
N8N_WEBHOOK_SECRET=
```
Restart uvicorn. The backend runs on your PC, so `localhost` is right here. Events carry trip details only (no user id, email or keys), are sent after the user has their response, and a failure is only logged.

## 3. Test WF-01
n8n runs inside Docker, so it reaches your PC's backend as `host.docker.internal:8000` (already set in the workflow).
```
curl -X POST http://localhost:5678/webhook/trippilot/trip-request -H "Content-Type: application/json" -d "{\"destination\":\"Manali\",\"startDate\":\"2026-12-15\",\"endDate\":\"2026-12-18\",\"budget\":20000,\"travelers\":2,\"interests\":[\"Adventure\",\"Food\"]}"
```
Expected: the same JSON the backend returns. A bad request (for example `budget: -5`) returns HTTP 422 with the backend's message.

## 4. Test WF-02
Generate a trip in the app, then open n8n -> **Executions**. You should see a "WF-02 - Trip Events" run whose "Summarize event" output has a `headline`.

## Troubleshooting
- `404 webhook not registered`: the workflow is not Active.
- WF-01 hangs or returns a connection error: the backend isn't running, or Docker can't resolve `host.docker.internal` (use your PC's LAN IP in the HTTP Request node instead).
- Backend log says `n8n webhook returned HTTP 404`: WF-02 is not Active. `n8n webhook unreachable`: n8n isn't running.
