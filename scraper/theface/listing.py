"""Iterate the contributor's listing pages and collect article URLs."""

from __future__ import annotations

from typing import Callable, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

from .http import polite_get

CONTRIBUTOR_ROOT = "https://theface.com/contributors"
EXPECTED_AUTHOR = "Olive Pometsey"
DEFAULT_CONTRIBUTOR_SLUG = "olive-pometsey"


def contributor_base_url(contributor_slug: str = DEFAULT_CONTRIBUTOR_SLUG) -> str:
    """Return the contributor listing base URL for a slug."""
    slug = contributor_slug.strip().strip("/")
    if not slug:
        raise ValueError("contributor_slug must not be empty")
    return f"{CONTRIBUTOR_ROOT}/{slug}"


DEFAULT_CONTRIBUTOR_BASE = contributor_base_url(DEFAULT_CONTRIBUTOR_SLUG)


def listing_url(page: int, *, contributor_base: str = DEFAULT_CONTRIBUTOR_BASE) -> str:
    """Build the listing URL for the given 1-indexed page number."""
    if page < 1:
        raise ValueError("page must be >= 1")
    if page == 1:
        return contributor_base
    return f"{contributor_base}/p{page}"


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


def _normalise_author_name(name: Optional[str]) -> str:
    """Collapse whitespace / case so exact byline checks are robust."""
    if not name:
        return ""
    return " ".join(name.strip().lower().split())


def _append_unique_name(authors: List[str], seen: set[str], name: str) -> None:
    key = _normalise_author_name(name)
    if not key or key in seen:
        return
    seen.add(key)
    authors.append(name.strip())


def extract_article_authors(html: str) -> List[str]:
    """Return the names credited in the article's visible `Words:` box.

    The contributor listing is noisy: many pages include shared playlists,
    staff roundups, or other mixed-author pieces. The only stable signal we
    trust for candidate selection is the visible contributor box on the
    article itself, specifically the names listed under `Words:`.
    """
    soup = BeautifulSoup(html, "lxml")
    for block in soup.select(".contributors"):
        authors: List[str] = []
        seen: set[str] = set()
        current_role = ""
        for child in block.children:
            if isinstance(child, NavigableString):
                continue
            if not isinstance(child, Tag):
                continue
            classes = set(child.get("class", []))
            if "contributors__type" in classes:
                current_role = child.get_text(" ", strip=True).rstrip(":").lower()
                continue
            if child.name == "br":
                current_role = ""
                continue
            if "contributors__name" not in classes or current_role != "words":
                continue
            _append_unique_name(authors, seen, child.get_text(" ", strip=True))
        if authors:
            return authors
    return []


def is_exclusive_author_credit(
    authors: List[str], *, expected_author: str = EXPECTED_AUTHOR
) -> bool:
    """Return True only when the piece is credited solely to `expected_author`."""
    return (
        len(authors) == 1
        and _normalise_author_name(authors[0])
        == _normalise_author_name(expected_author)
    )


def filter_exclusive_article_urls(
    session: requests.Session,
    urls: Iterable[str],
    *,
    expected_author: str = EXPECTED_AUTHOR,
    contributor_base: str = DEFAULT_CONTRIBUTOR_BASE,
    delay: float = 0.75,
    progress: Optional[Callable[[str, List[str], bool], None]] = None,
) -> List[str]:
    """Keep only article URLs whose visible `Words:` box names `expected_author`."""
    kept: List[str] = []
    for url in urls:
        resp = polite_get(session, url, delay=delay, referer=contributor_base)
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            if progress is not None:
                progress(url, [], False)
            continue

        authors = extract_article_authors(resp.text)
        keep = is_exclusive_author_credit(authors, expected_author=expected_author)
        if keep:
            kept.append(url)
        if progress is not None:
            progress(url, authors, keep)
    return kept


def iter_article_urls(
    session: requests.Session,
    *,
    start_page: int = 1,
    max_pages: int = 15,
    contributor_base: str = DEFAULT_CONTRIBUTOR_BASE,
    delay: float = 1.5,
    page_progress: Optional[Callable[[int, int], None]] = None,
) -> Iterable[str]:
    """Yield every article URL across the contributor's listing pages.

    Stops early if a page returns no new URLs (i.e. we've walked past the end).
    """
    seen: set[str] = set()
    for page in range(start_page, max_pages + 1):
        url = listing_url(page, contributor_base=contributor_base)
        resp = polite_get(session, url, delay=delay, referer=contributor_base)
        if resp.status_code == 404:
            break
        resp.raise_for_status()
        page_urls = extract_article_urls(resp.text)
        new_urls = [u for u in page_urls if u not in seen]
        if page_progress is not None:
            page_progress(page, len(new_urls))
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
    contributor_base: str = DEFAULT_CONTRIBUTOR_BASE,
    expected_author: Optional[str] = EXPECTED_AUTHOR,
    author_check_delay: float = 0.75,
    progress: Optional[Callable[[str], None]] = None,
    page_progress: Optional[Callable[[int, int], None]] = None,
) -> List[str]:
    """Eager wrapper around `iter_article_urls` that returns a list.

    When `expected_author` is set, the contributor listing is treated as a
    candidate set and each article page is verified so only pieces credited
    solely to that author are kept.
    """
    discovered = list(
        iter_article_urls(
            session,
            start_page=start_page,
            max_pages=max_pages,
            contributor_base=contributor_base,
            delay=delay,
            page_progress=page_progress,
        )
    )
    if expected_author is None:
        out: List[str] = []
        for url in discovered:
            out.append(url)
            if progress is not None:
                progress(url)
        return out

    filtered = filter_exclusive_article_urls(
        session,
        discovered,
        expected_author=expected_author,
        contributor_base=contributor_base,
        delay=author_check_delay,
    )
    if progress is not None:
        for url in filtered:
            progress(url)
    return filtered
