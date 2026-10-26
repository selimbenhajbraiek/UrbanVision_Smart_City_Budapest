import threading
import time
from collections.abc import Callable
from typing import Any


class TTLCache:
    """Tiny thread-safe in-memory cache: each value expires `ttl_seconds` after it was stored."""

    def __init__(self, ttl_seconds: float):
        self.ttl_seconds = ttl_seconds
        self._items: dict[Any, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get_or_set(self, key: Any, factory: Callable[[], Any]) -> Any:
        now = time.monotonic()
        with self._lock:
            hit = self._items.get(key)
            if hit and hit[0] > now:
                return hit[1]
        value = factory()  # called outside the lock so slow requests don't block others
        with self._lock:
            self._items[key] = (now + self.ttl_seconds, value)
        return value

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
