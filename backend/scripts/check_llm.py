"""Run from backend/:  python scripts\\check_llm.py
For each provider whose key is set in .env: lists models your key can use, then makes one tiny call
with the configured model (GEMINI_MODEL / GROQ_MODEL)."""
import sys

import httpx

sys.path.insert(0, ".")
from app.core.config import get_settings  # noqa: E402

s = get_settings()
checked = False

if s.gemini_api_key:
    checked = True
    base = "https://generativelanguage.googleapis.com/v1beta"
    h = {"x-goog-api-key": s.gemini_api_key}
    r = httpx.get(f"{base}/models", headers=h, params={"pageSize": 100}, timeout=20)
    print("\n[Gemini] list models ->", r.status_code)
    if r.status_code == 200:
        for m in r.json().get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                print("  ", m["name"].removeprefix("models/"))
    if s.gemini_model:
        r = httpx.post(
            f"{base}/models/{s.gemini_model}:generateContent",
            headers=h,
            json={"contents": [{"parts": [{"text": "Reply with the single word: ok"}]}]},
            timeout=30,
        )
        print(f"[Gemini] call {s.gemini_model} ->", r.status_code, "" if r.status_code == 200 else r.text[:300])
    else:
        print("[Gemini] set GEMINI_MODEL in .env (prefer a 'flash' / 'flash-lite' model)")

if s.groq_api_key:
    checked = True
    base = "https://api.groq.com/openai/v1"
    h = {"Authorization": f"Bearer {s.groq_api_key}"}
    r = httpx.get(f"{base}/models", headers=h, timeout=20)
    print("\n[Groq] list models ->", r.status_code)
    if r.status_code == 200:
        for m in r.json().get("data", []):
            print("  ", m["id"])
    if s.groq_model:
        r = httpx.post(
            f"{base}/chat/completions",
            headers=h,
            json={"model": s.groq_model, "messages": [{"role": "user", "content": "Reply with the single word: ok"}], "max_tokens": 5},
            timeout=30,
        )
        print(f"[Groq] call {s.groq_model} ->", r.status_code, "" if r.status_code == 200 else r.text[:300])
    else:
        print("[Groq] set GROQ_MODEL in .env (pick a chat model from the list above)")

if not checked:
    sys.exit("No GEMINI_API_KEY or GROQ_API_KEY found in backend/.env")
