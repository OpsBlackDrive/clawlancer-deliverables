"""Thread-safe token-bucket rate limiter using a monotonic clock."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Decision:
    allowed: bool
    remaining_tokens: float
    retry_after_seconds: float


class TokenBucket:
    """A configurable token bucket supporting fractional rates and costs."""

    def __init__(
        self,
        rate: float,
        burst: float,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if rate <= 0:
            raise ValueError("rate must be greater than zero")
        if burst <= 0:
            raise ValueError("burst must be greater than zero")

        self.rate = float(rate)
        self.burst = float(burst)
        self._clock = clock
        self._tokens = self.burst
        self._updated_at = self._clock()
        self._lock = threading.Lock()

    def _refill(self, now: float) -> None:
        elapsed = max(0.0, now - self._updated_at)
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._updated_at = now

    def consume(self, cost: float = 1.0) -> Decision:
        """Attempt to consume tokens and return an explicit decision."""
        if cost <= 0:
            raise ValueError("cost must be greater than zero")
        if cost > self.burst:
            raise ValueError("cost cannot exceed burst capacity")

        with self._lock:
            now = self._clock()
            self._refill(now)

            if self._tokens >= cost:
                self._tokens -= cost
                return Decision(True, self._tokens, 0.0)

            deficit = cost - self._tokens
            return Decision(False, self._tokens, deficit / self.rate)

    def available(self) -> float:
        """Return the currently available token count after refilling."""
        with self._lock:
            self._refill(self._clock())
            return self._tokens
