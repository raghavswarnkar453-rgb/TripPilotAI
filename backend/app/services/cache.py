import time
from typing import Any


class TTLCache:
    """Tiny in-process cache; protects Nominatim/Overpass/Open-Meteo and Gemini quota."""

    def __init__(self, ttl_seconds: float, max_items: int = 256):
        self._ttl = ttl_seconds
        self._max = max_items
        self._data: dict[Any, tuple[float, Any]] = {}

    def get(self, key: Any) -> Any | None:
        hit = self._data.get(key)
        if hit is None:
            return None
        expires, value = hit
        if expires < time.monotonic():
            self._data.pop(key, None)
            return None
        return value

    def set(self, key: Any, value: Any) -> None:
        if len(self._data) >= self._max:
            self._data.pop(next(iter(self._data)))
        self._data[key] = (time.monotonic() + self._ttl, value)

    def clear(self) -> None:
        self._data.clear()
