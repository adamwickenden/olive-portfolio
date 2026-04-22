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

from io import BytesIO
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator, Optional

DEFAULT_PDF_VIEWPORT_WIDTH = 1280
DEFAULT_SCREENSHOT_VIEWPORT_WIDTH = 960
DEFAULT_PDF_SCALE = 0.92
_FRAME_ATTACH_TIMEOUT_S = 5.0
_SETTLE_DELAY_MS = 750
_WAIT_TIMEOUT_MS = 15000
_EMBED_PAINT_DELAY_MS = 1200
_SCREENSHOT_TILE_SETTLE_MS = 500
_SCREENSHOT_OVERLAP_PX = 120
_PDF_PAGE_MARGIN_PX = 36


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


# CSS blanket that hides every consent / cookie / newsletter overlay we're
# likely to meet. Broad on purpose — we're only taking read-only screenshots,
# so false positives that hide *too much* UI chrome are fine (and far better
# than a giant consent banner mid-screenshot).
_HIDE_OVERLAYS_CSS = """
[id^="sp_message_container"], [id*="sp_message_iframe"],
[class*="sp_message"], [class*="sp_veil"],
[id^="qc-cmp2"], [class*="qc-cmp2"], [class*="qc-cmp2-container"],
[id*="cmp-container"], [class*="cmp-container"],
[class*="cookie-banner"], [id*="cookie-banner"],
[class*="cookie-notice"], [id*="cookie-notice"],
[class*="cookie-consent"], [id*="cookie-consent"],
[class*="consent-banner"], [id*="consent-banner"],
[class*="CybotCookiebot"], [id*="CybotCookiebot"],
[id^="onetrust-"], [class*="onetrust-"], #onetrust-consent-sdk,
.didomi-popup, .didomi-popup-container, #didomi-popup, #didomi-host,
#truste-consent-track, .truste_box_overlay, .truste_overlay,
[class*="newsletter-popup"], [id*="newsletter-popup"],
[class*="signup-modal"], [id*="signup-modal"],
iframe[src*="consent"], iframe[src*="cmp"],
iframe[src*="cookielaw"], iframe[src*="privacy"],
iframe[id*="sp_message"],
#audio-player, .audio-player
{
  display: none !important;
  visibility: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
}

/* CMPs often lock scroll on <html>/<body>. Undo that so scroll-to-bottom
   still triggers lazy-loads. */
html, body {
  overflow: auto !important;
  position: static !important;
  height: auto !important;
}
"""


_PDF_CAPTURE_CSS = """
/* Hide fixed site chrome that pollutes the printed page. */
#color-switcher,
header.site-header,
body > div[style*="left: 1.25rem"],
.audio-player,
#audio-player,
[data-mutual-ad],
.BeOpWidget,
.newsletter-popup-outer,
.main-nav,
.search-box,
footer + script,
script[src="/ads.js"]
{
  display: none !important;
}

/* Remove the giant desktop offset that exists only to make room for
   the fixed header on the live site. */
.styling-section > div:first-child {
  padding-top: 20px !important;
  padding-bottom: 12px !important;
}

/* Tame desktop headline styles so the hero image still fits on page 1. */
.styling-section h1 {
  font-size: 52px !important;
  line-height: 0.96 !important;
  margin-bottom: 10px !important;
}

.styling-section h1,
.styling-section h1 span {
  white-space: normal !important;
  overflow-wrap: anywhere !important;
  word-break: normal !important;
}

.styling-section .standfirst {
  font-size: 20px !important;
  line-height: 1.12 !important;
}

/* Keep the article header, hero image, and standfirst together so the image
   does not get punted to the next page after an oversized title block. */
.image-box,
.image-box__frame,
.image-box__image,
.article-header__divider,
.standfirst {
  break-inside: avoid !important;
  page-break-inside: avoid !important;
}

/* Make the hero image behave like a normal responsive image in print. */
.image-box,
.image-box__frame {
  width: 100% !important;
  max-width: 100% !important;
}

.image-box__frame {
  position: static !important;
  height: auto !important;
  padding-bottom: 0 !important;
  overflow: visible !important;
}

.image-box__image {
  display: block !important;
  width: 100% !important;
  height: auto !important;
  max-width: 100% !important;
  position: static !important;
  inset: auto !important;
  object-fit: cover !important;
}
"""


# Buttons that commonly dismiss / accept a consent dialog. We try each in
# order; first hit wins. Kept deliberately broad so we don't need per-CMP
# customisation.
_CONSENT_ACCEPT_SELECTORS = [
    'button:has-text("Accept All")',
    'button:has-text("Accept all")',
    'button:has-text("I Accept")',
    'button:has-text("I accept")',
    'button:has-text("Agree")',
    'button:has-text("AGREE")',
    'button:has-text("Got it")',
    'button:has-text("Allow all")',
    'button[aria-label*="accept" i]',
    'button[aria-label*="agree" i]',
    "#onetrust-accept-btn-handler",
    ".qc-cmp2-summary-buttons button[mode=\"primary\"]",
]


def _dismiss_overlays(page) -> None:
    """Best-effort: click an Accept button, then blanket-hide remaining overlays.

    Both steps are intentional. Clicking Accept makes the site set its
    consent cookies (so subsequent pages in the same context don't show the
    banner again), and the CSS blanket is a belt-and-braces for any overlay
    that snuck in via an iframe or a selector we didn't hit.
    """
    for selector in _CONSENT_ACCEPT_SELECTORS:
        try:
            loc = page.locator(selector).first
            if loc.count() > 0:
                loc.click(timeout=1500)
                break
        except Exception:
            continue
    try:
        page.add_style_tag(content=_HIDE_OVERLAYS_CSS)
    except Exception:
        pass


def _slug_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1] or "page"


def partition_existing_outputs(
    urls: Iterable[str],
    out_dir: Path,
    *,
    suffix: str,
) -> tuple[list[str], list[str]]:
    """Split URLs into `(existing, missing)` for a given output suffix."""
    existing: list[str] = []
    missing: list[str] = []
    for url in urls:
        target = out_dir / f"{_slug_from_url(url)}{suffix}"
        if target.exists():
            existing.append(url)
        else:
            missing.append(url)
    return existing, missing


def _import_playwright():
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "playwright is not installed. Install it with:\n"
            "  uv sync\n"
            "  uv run playwright install chromium"
        ) from exc
    return sync_playwright


def _import_pillow():
    try:
        from PIL import Image  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "Pillow is not installed. Install it with:\n"
            "  uv sync"
        ) from exc
    return Image


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


def _wait_for_article_assets(page) -> None:
    """Wait for the main document assets to finish loading.

    Screenshots are the most literal capture we have, but only if we wait for
    the page to finish painting its lazy images, fonts, and embeds first.
    """
    try:
        page.wait_for_load_state("load", timeout=10000)
    except Exception:
        pass

    try:
        page.wait_for_function(
            "() => !document.fonts || document.fonts.status === 'loaded'",
            timeout=10000,
        )
    except Exception:
        pass

    try:
        page.wait_for_function(
            """
            () => Array.from(document.querySelectorAll('main img')).every((img) => {
              if (!img.isConnected) {
                return true;
              }

              const style = window.getComputedStyle(img);
              if (style.display === 'none' || style.visibility === 'hidden') {
                return true;
              }

              if (!img.complete || img.naturalWidth === 0) {
                return false;
              }

              if (img.dataset.src || img.dataset.srcset) {
                if (!img.currentSrc || img.currentSrc.startsWith('data:')) {
                  return false;
                }
                if (/[?&]w=16(?:[&#]|$)/.test(img.currentSrc)) {
                  return false;
                }
              }

              return true;
            })
            """,
            timeout=_WAIT_TIMEOUT_MS,
        )
    except Exception:
        pass


def _embed_frames(page):
    """Return the visible inline content embed frames on the article page."""
    embeds = page.locator(".content-builder__block--embed-code iframe")
    frames = []
    count = embeds.count()
    for index in range(count):
        locator = embeds.nth(index)
        try:
            locator.wait_for(state="attached", timeout=3000)
        except Exception:
            continue

        deadline = time.monotonic() + _FRAME_ATTACH_TIMEOUT_S
        frame = None
        while time.monotonic() < deadline and frame is None:
            try:
                handle = locator.element_handle()
            except Exception:
                handle = None
            if handle is not None:
                frame = handle.content_frame()
                if frame is not None:
                    break
            page.wait_for_timeout(200)

        if frame is not None:
            frames.append(frame)
    return frames


def _wait_for_embeds(page) -> None:
    """Wait for inline embeds (YouTube, Spotify, etc.) to load their frames."""
    for frame in _embed_frames(page):
        try:
            frame.wait_for_load_state("domcontentloaded", timeout=_WAIT_TIMEOUT_MS)
        except Exception:
            pass
        try:
            frame.wait_for_load_state("load", timeout=_WAIT_TIMEOUT_MS)
        except Exception:
            pass


def _prime_embeds(page) -> None:
    """Visit each embed block so cross-origin frames get a chance to paint.

    Full-page screenshots are only "real" if the embeds have actually rendered
    while on screen. Scrolling through them one by one is slower, but it
    matches what a human viewer would do before taking a capture.
    """
    embeds = page.locator(".content-builder__block--embed-code")
    count = embeds.count()
    for index in range(count):
        locator = embeds.nth(index)
        try:
            locator.scroll_into_view_if_needed(timeout=5000)
        except Exception:
            continue
        page.wait_for_timeout(_EMBED_PAINT_DELAY_MS)


def _wait_for_capture_ready(page) -> None:
    """Wait until the page has reached a stable state for visual capture."""
    _wait_for_article_assets(page)
    _wait_for_embeds(page)
    _prime_embeds(page)
    page.wait_for_timeout(_SETTLE_DELAY_MS)


def _page_metrics(page) -> dict:
    """Return the current document and viewport dimensions in CSS pixels."""
    return page.evaluate(
        """
        () => ({
          fullHeight: Math.max(
            document.body.scrollHeight,
            document.documentElement.scrollHeight,
            document.body.offsetHeight,
            document.documentElement.offsetHeight
          ),
          viewportHeight: window.innerHeight,
          viewportWidth: document.documentElement.clientWidth
        })
        """
    )


def _wait_for_viewport_paint(page) -> None:
    """Give the current viewport a chance to finish painting visible embeds."""
    try:
        page.wait_for_function(
            """
            () => Array.from(
              document.querySelectorAll('.content-builder__block--embed-code iframe')
            )
              .filter((iframe) => {
                const rect = iframe.getBoundingClientRect();
                return rect.bottom > 0 && rect.top < window.innerHeight;
              })
              .every((iframe) => iframe.clientWidth > 0 && iframe.clientHeight > 0)
            """,
            timeout=5000,
        )
    except Exception:
        pass
    page.wait_for_timeout(_SCREENSHOT_TILE_SETTLE_MS)


def _capture_stitched_image(page):
    """Capture the full page by stitching viewport screenshots.

    Cross-origin embeds can disappear from Playwright's built-in full-page
    screenshot if they are off-screen when Chromium rasterises the page. By
    capturing tile-by-tile after scrolling each section into view, we preserve
    what was actually painted.
    """
    Image = _import_pillow()
    metrics = _page_metrics(page)
    full_height = int(metrics["fullHeight"])
    viewport_height = int(metrics["viewportHeight"])

    if full_height <= 0 or viewport_height <= 0:
        raise RuntimeError("Unable to determine page dimensions for screenshot")

    last_top = max(full_height - viewport_height, 0)
    step = max(viewport_height - _SCREENSHOT_OVERLAP_PX, 1)
    positions = list(range(0, last_top + 1, step))
    if not positions or positions[-1] != last_top:
        positions.append(last_top)

    tiles = []
    for top in positions:
        page.evaluate("(y) => window.scrollTo(0, y)", top)
        _wait_for_viewport_paint(page)
        shot = page.screenshot(type="png", animations="disabled")
        with BytesIO(shot) as buffer:
            tiles.append((top, Image.open(buffer).convert("RGB")))

    stitched = Image.new("RGB", (tiles[0][1].width, full_height), "white")
    painted_until = 0
    for top, tile in tiles:
        crop_top = max(painted_until - top, 0)
        crop_bottom = min(tile.height, full_height - top)
        if crop_top >= crop_bottom:
            continue
        stitched.paste(tile.crop((0, crop_top, tile.width, crop_bottom)),
                       (0, top + crop_top))
        painted_until = max(painted_until, top + crop_bottom)

    return stitched


def _capture_stitched_screenshot(page, target: Path) -> None:
    """Capture the full page to one tall PNG."""
    stitched = _capture_stitched_image(page)
    stitched.save(target)


def _save_paginated_pdf(image, target: Path, *, scale: float = 1.0) -> None:
    """Paginate a tall stitched image onto portrait A4 PDF pages.

    This avoids Chromium's print renderer, which was distorting the intro
    layout and leaking fixed site chrome into the PDF output.
    """
    if scale <= 0:
        raise ValueError("scale must be > 0")

    if scale != 1.0:
        image = image.resize(
            (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        )

    Image = _import_pillow()
    a4_ratio = 842.88 / 595.92
    page_width = image.width + (_PDF_PAGE_MARGIN_PX * 2)
    page_height = round(page_width * a4_ratio)
    content_height = page_height - (_PDF_PAGE_MARGIN_PX * 2)
    if content_height <= 0:
        raise RuntimeError("Computed non-positive PDF content height")

    pages = []
    top = 0
    while top < image.height:
        bottom = min(top + content_height, image.height)
        crop = image.crop((0, top, image.width, bottom))
        page = Image.new("RGB", (page_width, page_height), "white")
        page.paste(crop, (_PDF_PAGE_MARGIN_PX, _PDF_PAGE_MARGIN_PX))
        pages.append(page)
        top = bottom

    first, *rest = pages
    first.save(target, "PDF", save_all=True, append_images=rest, resolution=144.0)


def render_pdfs(
    urls: Iterable[str],
    out_dir: Path,
    *,
    viewport_width: int = DEFAULT_PDF_VIEWPORT_WIDTH,
    scale: float = DEFAULT_PDF_SCALE,
    user_agent: Optional[str] = None,
    progress: Optional[callable] = None,
    warning: Optional[callable] = None,
) -> list[dict[str, str]]:
    """Render each URL to `out_dir/<slug>.pdf`.

    The PDF is built from a fully painted stitched capture of the page rather
    than Chromium's print renderer, which proved unreliable for this site's
    fixed header and hero-image layout. Existing PDFs are left untouched so
    rerunning the command resumes from the first missing file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    failures: list[dict[str, str]] = []
    with _open_page(viewport_width=viewport_width, user_agent=user_agent) as page:
        for url in urls:
            slug = _slug_from_url(url)
            target = out_dir / f"{slug}.pdf"
            if target.exists():
                if progress is not None:
                    progress(url, target)
                continue
            try:
                _goto_with_fallback(page, url)
                _dismiss_overlays(page)
                page.evaluate(_SCROLL_TO_BOTTOM_JS)
                # Re-apply after scroll in case the CMP re-rendered.
                page.add_style_tag(content=_HIDE_OVERLAYS_CSS)
                page.add_style_tag(content=_PDF_CAPTURE_CSS)
                _wait_for_capture_ready(page)
                stitched = _capture_stitched_image(page)
                _save_paginated_pdf(stitched, target, scale=scale)
            except Exception as exc:
                failures.append(
                    {
                        "url": url,
                        "target": str(target),
                        "error": repr(exc),
                    }
                )
                if warning is not None:
                    warning(url, target, exc)
            if progress is not None:
                progress(url, target)
    return failures


def take_screenshots(
    urls: Iterable[str],
    out_dir: Path,
    *,
    viewport_width: int = DEFAULT_SCREENSHOT_VIEWPORT_WIDTH,
    user_agent: Optional[str] = None,
    progress: Optional[callable] = None,
    warning: Optional[callable] = None,
) -> list[dict[str, str]]:
    """Capture a full-page PNG screenshot of each URL.

    Writes `out_dir/<slug>.png`. The screenshot covers the entire scrollable
    height of the page (`full_page=True`), not just the viewport, so a long
    photo essay comes out as one tall image. Existing PNGs are left untouched
    so rerunning the command resumes from the first missing file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    failures: list[dict[str, str]] = []
    with _open_page(viewport_width=viewport_width, user_agent=user_agent) as page:
        for url in urls:
            slug = _slug_from_url(url)
            target = out_dir / f"{slug}.png"
            if target.exists():
                if progress is not None:
                    progress(url, target)
                continue
            try:
                _goto_with_fallback(page, url)
                _dismiss_overlays(page)
                page.evaluate(_SCROLL_TO_BOTTOM_JS)
                # Re-apply after scroll in case the CMP re-rendered.
                page.add_style_tag(content=_HIDE_OVERLAYS_CSS)
                _wait_for_capture_ready(page)
                _capture_stitched_screenshot(page, target)
            except Exception as exc:
                failures.append(
                    {
                        "url": url,
                        "target": str(target),
                        "error": repr(exc),
                    }
                )
                if warning is not None:
                    warning(url, target, exc)
            if progress is not None:
                progress(url, target)
    return failures
