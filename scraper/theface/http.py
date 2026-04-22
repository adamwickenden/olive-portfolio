"""HTTP session helpers: browser-style UA, polite throttling, retries on 5xx."""

from __future__ import annotations

import random
import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter

# theface.com sits behind Cloudflare. A plain `python-requests/...` UA gets a
# 403/503 on most requests, so we present as a real desktop browser. This is
# only being used to download articles the journalist herself authored, ahead
# of the publication closing.
DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_UA,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def build_session() -> requests.Session:
    """Return a requests Session pre-configured for theface.com."""
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    adapter = HTTPAdapter(pool_connections=4, pool_maxsize=4)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def polite_get(
    session: requests.Session,
    url: str,
    *,
    delay: float = 1.5,
    max_retries: int = 4,
    timeout: float = 30.0,
    stream: bool = False,
    referer: Optional[str] = None,
) -> requests.Response:
    """GET with a polite pre-request delay and exponential backoff on 5xx / 429.

    The site rate-limits aggressive scraping with 503s — we treat 5xx and 429
    as retryable and back off (4s, 8s, 16s, 32s) before giving up.
    """
    # Jitter the base delay slightly so we don't hammer in lockstep.
    time.sleep(delay + random.uniform(0.0, 0.5))

    headers = {}
    if referer:
        headers["Referer"] = referer

    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            resp = session.get(url, timeout=timeout, stream=stream, headers=headers)
        except requests.RequestException as exc:
            last_exc = exc
            resp = None

        if resp is not None and resp.status_code < 500 and resp.status_code != 429:
            return resp

        if attempt == max_retries:
            if resp is not None:
                return resp
            assert last_exc is not None
            raise last_exc

        backoff = 4.0 * (2**attempt)
        time.sleep(backoff + random.uniform(0.0, 1.0))

    # Unreachable, but keeps type-checkers happy.
    raise RuntimeError(f"Failed to GET {url} after {max_retries} retries")
