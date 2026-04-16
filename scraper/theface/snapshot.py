"""Optional Playwright-powered PDF snapshots.

Some readers prefer a pixel-faithful PDF of every article alongside the
extracted HTML/Markdown. This module is intentionally optional: it imports
playwright lazily so the rest of the scraper still runs if the dep is missing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional


def render_pdfs(urls: Iterable[str], out_dir: Path,
                *, viewport_width: int = 1280,
                user_agent: Optional[str] = None) -> None:
    """Render each URL to `out_dir/<slug>.pdf` using headless Chromium.

    Requires `playwright` to be installed and `playwright install chromium`
    to have been run.
    """
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "playwright is not installed. Install it with:\n"
            "  pip install playwright && playwright install chromium"
        ) from exc

    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": viewport_width, "height": 900},
            user_agent=user_agent,
        )
        page = context.new_page()
        for url in urls:
            slug = url.rstrip("/").rsplit("/", 1)[-1] or "page"
            target = out_dir / f"{slug}.pdf"
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
            except Exception:
                # Some pages never settle — fall back to domcontentloaded.
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
            # Force any remaining lazy images to load by scrolling to bottom.
            page.evaluate(
                "async () => {"
                "  await new Promise(resolve => {"
                "    let total = 0;"
                "    const step = 400;"
                "    const id = setInterval(() => {"
                "      window.scrollBy(0, step);"
                "      total += step;"
                "      if (total >= document.body.scrollHeight) {"
                "        clearInterval(id); resolve();"
                "      }"
                "    }, 80);"
                "  });"
                "}"
            )
            page.pdf(
                path=str(target),
                format="A4",
                print_background=True,
                margin={"top": "12mm", "bottom": "12mm",
                        "left": "10mm", "right": "10mm"},
            )
        browser.close()
