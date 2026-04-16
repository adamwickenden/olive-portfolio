"""Iterate the contributor's listing pages and collect article URLs."""

from __future__ import annotations

from typing import Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

from .http import polite_get

CONTRIBUTOR_BASE = "https://theface.com/contributors/olive-pometsey"


def listing_url(page: int) -> str:
    """Build the listing URL for the given 1-indexed page number."""
    if page < 1:
        raise ValueError("page must be >= 1")
    if page == 1:
        return CONTRIBUTOR_BASE
    return f"{CONTRIBUTOR_BASE}/p{page}"


def extract_article_urls(html: str) -> List[str]:
    """Pull article URLs out of one listing page's HTML.

    Each article card on the listing wraps the cover image in
    `<a class="card__image" href="...">`. We use that as the canonical anchor
    to avoid double-counting the title link directly underneath it.
    """
    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    urls: List[str] = []
    for a in soup.select("a.card__image[href]"):
        href = a["href"].strip()
        if not href.startswith("https://theface.com/"):
            continue
        # Skip the contributor page itself or any non-article link.
        if "/contributors/" in href:
            continue
        if href in seen:
            continue
        seen.add(href)
        urls.append(href)
    return urls


def iter_article_urls(
    session: requests.Session,
    *,
    start_page: int = 1,
    max_pages: int = 15,
    delay: float = 1.5,
) -> Iterable[str]:
    """Yield every article URL across the contributor's listing pages.

    Stops early if a page returns no new URLs (i.e. we've walked past the end).
    """
    seen: set[str] = set()
    for page in range(start_page, max_pages + 1):
        url = listing_url(page)
        resp = polite_get(session, url, delay=delay, referer=CONTRIBUTOR_BASE)
        if resp.status_code == 404:
            break
        resp.raise_for_status()
        page_urls = extract_article_urls(resp.text)
        new_urls = [u for u in page_urls if u not in seen]
        if not new_urls:
            # No new content on this page: assume we're past the end.
            break
        for u in new_urls:
            seen.add(u)
            yield u


def collect_all_article_urls(
    session: requests.Session,
    *,
    start_page: int = 1,
    max_pages: int = 15,
    delay: float = 1.5,
    progress: Optional[callable] = None,
) -> List[str]:
    """Eager wrapper around `iter_article_urls` that returns a list."""
    out: List[str] = []
    for url in iter_article_urls(
        session, start_page=start_page, max_pages=max_pages, delay=delay
    ):
        out.append(url)
        if progress is not None:
            progress(url)
    return out
