"""A tiny in-process sliding-window limiter for login brute-force protection.

Stdlib only — no Redis/deps. Keyed by an arbitrary string (email or client IP),
it tracks recent *failed* attempts and reports how long a key must wait once it
exceeds the threshold. State is per-process and in-memory, so it resets on
restart and isn't shared across workers; that's an acceptable tradeoff for a
demo, but a multi-worker deploy would want a shared store.
"""
import threading
import time


class SlidingWindowLimiter:
    def __init__(self, max_events: int, window_seconds: float) -> None:
        self._max = max_events
        self._window = window_seconds
        self._events: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> list[float]:
        cutoff = now - self._window
        events = [t for t in self._events.get(key, []) if t > cutoff]
        if events:
            self._events[key] = events
        else:
            self._events.pop(key, None)
        return events

    def retry_after(self, key: str) -> float:
        """Seconds until `key` is allowed again, or 0 if it's under the limit."""
        now = time.time()
        with self._lock:
            events = self._prune(key, now)
            if len(events) < self._max:
                return 0.0
            return self._window - (now - events[0])

    def record(self, key: str) -> None:
        """Note one failed attempt for `key`."""
        now = time.time()
        with self._lock:
            self._events.setdefault(key, []).append(now)

    def reset(self, key: str) -> None:
        """Clear a key's history (call on a successful login)."""
        with self._lock:
            self._events.pop(key, None)
