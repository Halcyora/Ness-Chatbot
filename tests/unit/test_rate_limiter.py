"""
Unit tests for api/rate_limiter.py
"""

import pytest
from api import rate_limiter
from api.rate_limiter import check_rate_limit, reset_rate_limits


@pytest.fixture(autouse=True)
def _clean_state():
    """Ensure each test starts with no rate-limit history."""
    reset_rate_limits()
    yield
    reset_rate_limits()


def test_allows_requests_under_the_limit():
    for _ in range(5):
        allowed, reason, retry_after = check_rate_limit("1.2.3.4")
        assert allowed
        assert reason == ""
        assert retry_after == 0


def test_blocks_requests_over_the_per_minute_limit(monkeypatch):
    monkeypatch.setattr(rate_limiter, "RATE_LIMIT_PER_MINUTE", 3)

    for _ in range(3):
        allowed, _, _ = check_rate_limit("5.6.7.8")
        assert allowed

    allowed, reason, retry_after = check_rate_limit("5.6.7.8")
    assert not allowed
    assert "slow down" in reason.lower()
    assert retry_after > 0


def test_blocks_requests_over_the_daily_limit(monkeypatch):
    monkeypatch.setattr(rate_limiter, "RATE_LIMIT_PER_MINUTE", 1000)
    monkeypatch.setattr(rate_limiter, "RATE_LIMIT_PER_DAY", 2)

    for _ in range(2):
        allowed, _, _ = check_rate_limit("9.9.9.9")
        assert allowed

    allowed, reason, retry_after = check_rate_limit("9.9.9.9")
    assert not allowed
    assert "daily" in reason.lower()
    assert retry_after > 0


def test_clients_are_tracked_independently(monkeypatch):
    monkeypatch.setattr(rate_limiter, "RATE_LIMIT_PER_MINUTE", 1)

    allowed_a, _, _ = check_rate_limit("client-a")
    allowed_b, _, _ = check_rate_limit("client-b")
    assert allowed_a
    assert allowed_b

    blocked_a, _, _ = check_rate_limit("client-a")
    assert not blocked_a
