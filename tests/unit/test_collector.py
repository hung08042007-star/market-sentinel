import time
import httpx
import pytest
from src.collector.client import (
    ResilientCollector,
    ScraperBlockError,
    ScraperNetworkError,
)


def test_collector_success_200():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert "User-Agent" in request.headers
        return httpx.Response(200, text="<html>Success</html>", headers={"Content-Type": "text/html"})

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)
    collector = ResilientCollector(client=client, rate_limit_delay=0.0)

    result = collector.fetch("https://example.com/products")
    assert result.status_code == 200
    assert result.text == "<html>Success</html>"
    assert result.attempts == 1
    assert result.latency_ms >= 0


def test_collector_recovers_after_rate_limit_429():
    call_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, text="Too Many Requests")
        return httpx.Response(200, text="<html>Recovered</html>")

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)
    collector = ResilientCollector(client=client, max_retries=3, backoff_base=0.01, rate_limit_delay=0.0)

    result = collector.fetch("https://example.com/rate-limited")
    assert result.status_code == 200
    assert result.text == "<html>Recovered</html>"
    assert result.attempts == 2
    assert call_count == 2


def test_collector_fails_after_persistent_429():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="Too Many Requests")

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)
    collector = ResilientCollector(client=client, max_retries=2, backoff_base=0.01, rate_limit_delay=0.0)

    with pytest.raises(ScraperBlockError, match="HTTP 429 persists after 2 retries"):
        collector.fetch("https://example.com/blocked")


def test_collector_fails_immediately_on_403_forbidden():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Forbidden - Cloudflare")

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)
    collector = ResilientCollector(client=client, rate_limit_delay=0.0)

    with pytest.raises(ScraperBlockError, match="HTTP 403 Forbidden"):
        collector.fetch("https://example.com/waf-block")


def test_collector_retries_on_timeout():
    call_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ReadTimeout("Connection timed out", request=request)
        return httpx.Response(200, text="<html>Success on retry</html>")

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)
    collector = ResilientCollector(client=client, max_retries=2, backoff_base=0.01, rate_limit_delay=0.0)

    result = collector.fetch("https://example.com/slow")
    assert result.status_code == 200
    assert result.attempts == 2
    assert call_count == 2


def test_collector_enforces_rate_limit_throttle():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="OK")

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)
    delay = 0.05
    collector = ResilientCollector(client=client, rate_limit_delay=delay)

    start = time.monotonic()
    collector.fetch("https://example.com/1")
    collector.fetch("https://example.com/2")
    elapsed = time.monotonic() - start

    assert elapsed >= delay, f"Expected elapsed >= {delay}, got {elapsed}"
