"""Resilient HTTP Collector for Market Sentinel.

Features:
- Browser fingerprint emulation with User-Agent rotation and realistic headers
- Exponential backoff with full jitter on 429 and 5xx errors
- Configurable per-host rate limiting
- Detailed telemetry (latency, retry count, status codes)
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]


class ScraperError(Exception):
    """Base exception for collector operations."""
    pass


class ScraperBlockError(ScraperError):
    """Raised when target server explicitly blocks or rate limits past retries."""
    pass


class ScraperNetworkError(ScraperError):
    """Raised on persistent timeout or connection drop."""
    pass


@dataclass
class FetchResult:
    url: str
    status_code: int
    text: str
    latency_ms: float
    attempts: int
    headers: dict[str, str] = field(default_factory=dict)


class ResilientCollector:
    def __init__(
        self,
        timeout: float = 15.0,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        rate_limit_delay: float = 1.0,
        client: Optional[httpx.Client] = None,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time: float = 0.0
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)

    def _get_browser_headers(self) -> dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }

    def _throttle(self) -> None:
        """Enforce spacing between consecutive outgoing requests."""
        if self.rate_limit_delay <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            time.sleep(sleep_time)
        self._last_request_time = time.monotonic()

    def fetch(self, url: str, extra_headers: Optional[dict[str, str]] = None) -> FetchResult:
        headers = self._get_browser_headers()
        if extra_headers:
            headers.update(extra_headers)

        last_status = 0
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            self._throttle()
            start_time = time.monotonic()
            try:
                response = self._client.get(url, headers=headers)
                latency = round((time.monotonic() - start_time) * 1000, 2)
                last_status = response.status_code

                # Success
                if response.status_code == 200:
                    return FetchResult(
                        url=url,
                        status_code=response.status_code,
                        text=response.text,
                        latency_ms=latency,
                        attempts=attempt,
                        headers=dict(response.headers),
                    )

                # Explicit forbidden / bot wall
                if response.status_code == 403:
                    raise ScraperBlockError(f"HTTP 403 Forbidden: Bot wall or IP block detected at {url}")

                # Retriable server error or rate-limit
                if response.status_code in (429, 500, 502, 503, 504):
                    logger.warning(
                        f"Fetch attempt {attempt}/{self.max_retries} for {url} returned HTTP {response.status_code}"
                    )
                    if attempt < self.max_retries:
                        # Full jitter exponential backoff: base * 2^(attempt-1) + random(0, 1)
                        backoff = (self.backoff_base * (2 ** (attempt - 1))) + random.uniform(0.1, 0.9)
                        time.sleep(backoff)
                        continue
                    else:
                        raise ScraperBlockError(
                            f"HTTP {response.status_code} persists after {self.max_retries} retries for {url}"
                        )

                # Other 4xx client errors (404, etc.)
                return FetchResult(
                    url=url,
                    status_code=response.status_code,
                    text=response.text,
                    latency_ms=latency,
                    attempts=attempt,
                    headers=dict(response.headers),
                )

            except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                last_error = net_err
                logger.warning(
                    f"Network error on attempt {attempt}/{self.max_retries} for {url}: {net_err}"
                )
                if attempt < self.max_retries:
                    backoff = (self.backoff_base * (2 ** (attempt - 1))) + random.uniform(0.1, 0.5)
                    time.sleep(backoff)
                else:
                    raise ScraperNetworkError(
                        f"Network failure after {self.max_retries} retries for {url}: {last_error}"
                    ) from last_error

        raise ScraperError(f"Unexpected termination fetching {url} with status {last_status}")

    def close(self) -> None:
        self._client.close()
