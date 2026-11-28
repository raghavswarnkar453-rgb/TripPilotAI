"""Groq (OpenAI-compatible chat completions). Same contract as gemini.call: prompt in, raw JSON text out."""
import logging

import httpx

from app.services.errors import ItineraryInvalid, ModelNotFound, RateLimited, UpstreamUnavailable
from app.services.gemini import SYSTEM_PROMPT

log = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _error_info(res: httpx.Response) -> tuple[str, str]:
    try:
        err = res.json().get("error") or {}
        return str(err.get("code") or ""), str(err.get("message") or "")[:200]
    except (ValueError, AttributeError):
        return "", ""


def _is_bad_generation(code: str, message: str) -> bool:
    text = f"{code} {message}".lower()
    return any(k in text for k in ("json_validate_failed", "failed to generate json", "max completion tokens"))


async def call(client: httpx.AsyncClient, api_key: str, model: str, user_prompt: str) -> str:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.6,
        "max_tokens": 6000,  # reasoning models spend part of this before the JSON; stay inside free-tier TPM
        "response_format": {"type": "json_object"},
    }
    if "gpt-oss" in model:
        body["reasoning_effort"] = "low"  # leaves room for the full itinerary JSON
    try:
        res = await client.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
    except httpx.HTTPError as e:
        log.warning("groq request failed: %s", type(e).__name__)
        raise UpstreamUnavailable("The Groq AI service could not be reached.") from e

    if res.status_code == 404:
        raise ModelNotFound("The configured Groq model is not available. Check GROQ_MODEL on the server.")
    if res.status_code in (413, 429):  # 413 = request larger than the free-tier tokens-per-minute budget
        raise RateLimited("The Groq AI service is busy (free-tier limit).")
    if res.status_code in (400, 401, 403):
        code, message = _error_info(res)
        log.warning("groq rejected request: status=%s code=%s message=%s", res.status_code, code, message)
        if res.status_code == 400 and _is_bad_generation(code, message):
            # The model produced malformed/truncated JSON: retryable, not a configuration problem.
            raise ItineraryInvalid("Groq returned malformed JSON.")
        raise UpstreamUnavailable("Groq rejected the request. Check GROQ_API_KEY and GROQ_MODEL.")
    if res.status_code >= 400:
        log.warning("groq error: status=%s", res.status_code)
        raise UpstreamUnavailable("The Groq AI service had a problem.")

    try:
        text = res.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise ItineraryInvalid("Groq returned an empty response.") from e
    if not text:
        raise ItineraryInvalid("Groq returned an empty response.")
    return text
