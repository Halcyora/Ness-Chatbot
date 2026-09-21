"""
Simple in-process rate limiting to guard against runaway request volume/cost.

Mirrors the "API Gateway usage plan: rate limit + daily cap per IP" guardrail
described in architecture.md, implemented locally since there's no API Gateway
in front of this dev server. Uses a fixed-window counter per client (IP by
default) - good enough to stop abuse/cost runaway without external deps.
"""

import os
import time
from typing import Dict, Tuple

RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))
RATE_LIMIT_PER_DAY = int(os.getenv("RATE_LIMIT_PER_DAY", "500"))

_MINUTE = 60
_DAY = 86400

# client_id -> counters for the current minute/day windows
_buckets: Dict[str, Dict[str, float]] = {}


def check_rate_limit(client_id: str) -> Tuple[bool, str, int]:
    """
    Check and record a request for client_id against both the per-minute and per-day limits.

    Args:
        client_id: Identifier for the caller (typically IP address)

    Returns:
        (allowed, reason, retry_after_seconds) - reason/retry_after are only
        meaningful when allowed is False.
    """
    now = time.time()
    bucket = _buckets.setdefault(
        client_id,
        {"minute_start": now, "minute_count": 0, "day_start": now, "day_count": 0},
    )

    # Reset windows that have fully elapsed
    if now - bucket["minute_start"] >= _MINUTE:
        bucket["minute_start"] = now
        bucket["minute_count"] = 0
    if now - bucket["day_start"] >= _DAY:
        bucket["day_start"] = now
        bucket["day_count"] = 0

    if bucket["minute_count"] >= RATE_LIMIT_PER_MINUTE:
        retry_after = int(_MINUTE - (now - bucket["minute_start"])) + 1
        return False, "Too many requests - please slow down and try again shortly.", retry_after

    if bucket["day_count"] >= RATE_LIMIT_PER_DAY:
        retry_after = int(_DAY - (now - bucket["day_start"])) + 1
        return False, "Daily message limit reached - please try again tomorrow.", retry_after

    bucket["minute_count"] += 1
    bucket["day_count"] += 1
    return True, "", 0


def reset_rate_limits() -> None:
    """Clear all rate-limit state. Primarily for tests."""
    _buckets.clear()
