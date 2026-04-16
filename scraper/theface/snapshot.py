"""Optional Playwright-powered snapshots (PDF and full-page PNG).

Some readers prefer a pixel-faithful backup of every article alongside the
extracted HTML/Markdown. This module is intentionally optional: it imports
playwright lazily so the rest of the scraper still runs if the dep is missing.

Two output formats are supported:

- `render_pdfs()`    — one A4 PDF per article.
- `take_screenshots()` — one full-page PNG per article (the full scrollable
  height, not just the viewport).

Both use the same browser setup and the same scroll-to-bottom routine to
force any lazy-loaded images into the DOM before capture.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator, Optional


# JS snippet that scrolls to the bottom in small increments so IntersectionObserver
# -based lazy loading triggers for every image on the page.
_SCROLL_TO_BOTTOM_JS = """
async () => {
  await new Promise(resolve => {
    let total = 0;
    const step = 400;
    const id = setInterval(() => {
      window.scrollBy(0, step);
      total += step;
      if (total >= document.body.scrollHeight) {
        clearInterval(id);
        // Give lazy images a beat to finish loading before we resolve.
        setTimeout(resolve, 500);
      }
    }, 80);
  });
}
"""


def _slug_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1] or "page"


def _import_playwright():
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "playwright is not installed. Install it with:\n"
            "  pip install playwright && playwright install chromium"
        ) from exc
    return sync_playwright


@contextmanager
def _open_page(
    *, viewport_width: int = 1280, user_agent: Optional[str] = None
) -> Iterator:
    sync_playwright = _import_playwright()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": viewport_width, "height": 900},
            user_agent=user_agent,
            # Corporate / sandbox TLS proxies often re-sign with a local CA;
            # ignore cert errors so the scrape still works in those
            # environments. No security implication for a read-only scraper.
            ignore_https_errors=True,
        )
        page = context.new_page()
        try:
            yield page
        finally:
            browser.close()


def _goto_with_fallback(page, url: str) -> None:
    """Navigate to `url`, falling back to a looser wait if networkidle stalls."""
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
    except Exception:
        # Some pages (ad-heavy, pings, etc.) never settle — accept DOM ready.
        page.goto(url, wait_until="domcontentloaded", timeout=60000)


def render_pdfs(
    urls: Iterable[str],
    out_dir: Path,
    *,
    viewport_width: int = 1280,
    user_agent: Optional[str] = None,
    progress: Optional[callable] = None,
) -> None:
    """Render each URL to `out_dir/<slug>.pdf` using headless Chromium."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with _open_page(viewport_width=viewport_width, user_agent=user_agent) as page:
        for url in urls:
            slug = _slug_from_url(url)
            target = out_dir / f"{slug}.pdf"
            _goto_with_fallback(page, url)
            page.evaluate(_SCROLL_TO_BOTTOM_JS)
            page.pdf(
                path=str(target),
                format="A4",
                print_background=True,
                margin={"top": "12mm", "bottom": "12mm",
                        "left": "10mm", "right": "10mm"},
            )
            if progress is not None:
                progress(url, target)


def take_screenshots(
    urls: Iterable[str],
    out_dir: Path,
    *,
    viewport_width: int = 1280,
    user_agent: Optional[str] = None,
    progress: Optional[callable] = None,
) -> None:
    """Capture a full-page PNG screenshot of each URL.

    Writes `out_dir/<slug>.png`. The screenshot covers the entire scrollable
    height of the page (`full_page=True`), not just the viewport, so a long
    photo essay comes out as one tall image.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    with _open_page(viewport_width=viewport_width, user_agent=user_agent) as page:
        for url in urls:
            slug = _slug_from_url(url)
            target = out_dir / f"{slug}.png"
            _goto_with_fallback(page, url)
            page.evaluate(_SCROLL_TO_BOTTOM_JS)
            # Scroll back to the top so the hero isn't mid-animation.
            page.evaluate("() => window.scrollTo(0, 0)")
            page.screenshot(path=str(target), full_page=True, type="png")
            if progress is not None:
                progress(url, target)
