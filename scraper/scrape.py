#!/usr/bin/env python3
"""CLI entry point for archiving Olive Pometsey's articles from theface.com.

Typical usage (run from inside `scraper/`):

    # 1. Sync dependencies into the uv-managed environment
    uv sync

    # 2. List every article URL across all 15 pages (sanity check, fast)
    uv run theface-scraper discover

    # 3. Scrape everything: HTML + Markdown + metadata + downloaded images
    uv run theface-scraper scrape

    # 4. Optionally render a pixel-faithful PDF of every article
    uv run playwright install chromium
    uv run theface-scraper snapshot

    # 5. Or take a full-page PNG screenshot of every article as a visual backup
    uv run theface-scraper screenshots

Outputs land under `scraper/output/` (gitignored).
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import List

from tqdm import tqdm

from theface.article import (
    scrape_article,
    slug_dir_name,
    write_article_to_disk,
)
from theface.http import build_session
from theface.listing import collect_all_article_urls

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "output"


def cmd_discover(args: argparse.Namespace) -> int:
    out_dir: Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    session = build_session()
    print(f"Scanning listing pages 1..{args.max_pages}...", file=sys.stderr)
    urls = collect_all_article_urls(
        session,
        start_page=args.start_page,
        max_pages=args.max_pages,
        delay=args.delay,
        progress=lambda u: print(f"  found {u}", file=sys.stderr),
    )
    index_path = out_dir / "article_urls.json"
    index_path.write_text(json.dumps(urls, indent=2), encoding="utf-8")
    print(f"\nFound {len(urls)} unique articles. Wrote {index_path}.")
    return 0


def _load_or_discover_urls(args: argparse.Namespace, session) -> List[str]:
    out_dir: Path = args.output_dir
    index_path = out_dir / "article_urls.json"
    if not args.refresh and index_path.exists():
        urls = json.loads(index_path.read_text(encoding="utf-8"))
        print(f"Loaded {len(urls)} URLs from {index_path}", file=sys.stderr)
        return urls
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Scanning listing pages 1..{args.max_pages}...", file=sys.stderr)
    urls = collect_all_article_urls(
        session,
        start_page=args.start_page,
        max_pages=args.max_pages,
        delay=args.delay,
    )
    index_path.write_text(json.dumps(urls, indent=2), encoding="utf-8")
    print(f"Discovered {len(urls)} URLs.", file=sys.stderr)
    return urls


def cmd_scrape(args: argparse.Namespace) -> int:
    out_dir: Path = args.output_dir
    articles_dir = out_dir / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)

    session = build_session()
    urls = _load_or_discover_urls(args, session)
    if args.limit:
        urls = urls[: args.limit]

    failures: List[dict] = []
    successes: List[dict] = []

    pbar = tqdm(urls, desc="Scraping articles", unit="art")
    for url in pbar:
        try:
            article = scrape_article(
                session,
                url,
                delay=args.delay,
                download_images_too=not args.skip_images,
            )
            folder = write_article_to_disk(article, articles_dir)
            successes.append(
                {
                    "url": url,
                    "folder": str(folder.relative_to(out_dir)),
                    "title": article.metadata.title,
                    "image_count": len(article.images),
                }
            )
            pbar.set_postfix_str(slug_dir_name(article.metadata)[:40])
        except Exception as exc:  # noqa: BLE001 — best-effort archive
            failures.append({"url": url, "error": repr(exc),
                             "trace": traceback.format_exc(limit=3)})
            tqdm.write(f"  ! failed {url}: {exc}")

    summary = {
        "total": len(urls),
        "succeeded": len(successes),
        "failed": len(failures),
        "successes": successes,
        "failures": failures,
    }
    summary_path = out_dir / "scrape_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"\nDone. {len(successes)}/{len(urls)} succeeded. "
        f"Summary: {summary_path}"
    )
    return 0 if not failures else 1


def cmd_snapshot(args: argparse.Namespace) -> int:
    from theface.snapshot import render_pdfs
    from theface.http import DEFAULT_UA

    out_dir: Path = args.output_dir
    pdf_dir = out_dir / "pdfs"
    session = build_session()
    urls = _load_or_discover_urls(args, session)
    if args.limit:
        urls = urls[: args.limit]
    print(f"Rendering {len(urls)} PDFs into {pdf_dir}...", file=sys.stderr)
    bar = tqdm(total=len(urls), desc="Rendering PDFs", unit="pdf")
    render_pdfs(
        urls,
        pdf_dir,
        user_agent=DEFAULT_UA,
        viewport_width=args.viewport_width,
        scale=args.pdf_scale,
        progress=lambda u, p: bar.update(1),
    )
    bar.close()
    print("Done.")
    return 0


def cmd_screenshots(args: argparse.Namespace) -> int:
    from theface.snapshot import take_screenshots
    from theface.http import DEFAULT_UA

    out_dir: Path = args.output_dir
    shots_dir = out_dir / "screenshots"
    session = build_session()
    urls = _load_or_discover_urls(args, session)
    if args.limit:
        urls = urls[: args.limit]
    print(
        f"Capturing {len(urls)} full-page screenshots into {shots_dir}...",
        file=sys.stderr,
    )
    bar = tqdm(total=len(urls), desc="Taking screenshots", unit="png")
    take_screenshots(
        urls,
        shots_dir,
        user_agent=DEFAULT_UA,
        viewport_width=args.viewport_width,
        progress=lambda u, p: bar.update(1),
    )
    bar.close()
    print("Done.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    from theface.snapshot import (
        DEFAULT_PDF_SCALE,
        DEFAULT_PDF_VIEWPORT_WIDTH,
        DEFAULT_SCREENSHOT_VIEWPORT_WIDTH,
    )

    p = argparse.ArgumentParser(
        description="Scrape Olive Pometsey's articles from theface.com.",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Where to write outputs (default: {DEFAULT_OUTPUT}).",
    )
    p.add_argument("--start-page", type=int, default=1,
                   help="First listing page to scan (default 1).")
    p.add_argument("--max-pages", type=int, default=15,
                   help="Last listing page to scan (default 15).")
    p.add_argument("--delay", type=float, default=1.5,
                   help="Polite delay (seconds) between requests.")
    p.add_argument("--limit", type=int, default=None,
                   help="Process at most N article URLs (for testing).")
    p.add_argument("--refresh", action="store_true",
                   help="Re-scan listing pages even if a cached index exists.")

    sub = p.add_subparsers(dest="command", required=True)

    sp_discover = sub.add_parser(
        "discover", help="List all article URLs (writes article_urls.json)."
    )
    sp_discover.set_defaults(func=cmd_discover)

    sp_scrape = sub.add_parser(
        "scrape",
        help="Download HTML + Markdown + metadata + images for every article.",
    )
    sp_scrape.add_argument("--skip-images", action="store_true",
                           help="Don't download referenced images.")
    sp_scrape.set_defaults(func=cmd_scrape)

    sp_snap = sub.add_parser(
        "snapshot",
        help="Render a PDF snapshot of every article (requires playwright).",
    )
    sp_snap.add_argument(
        "--viewport-width",
        type=int,
        default=DEFAULT_PDF_VIEWPORT_WIDTH,
        help=(
            "Browser viewport width in pixels before printing "
            f"(default {DEFAULT_PDF_VIEWPORT_WIDTH})."
        ),
    )
    sp_snap.add_argument(
        "--pdf-scale",
        type=float,
        default=DEFAULT_PDF_SCALE,
        help=(
            "Scale factor for the printed page; lower zooms out slightly "
            f"(default {DEFAULT_PDF_SCALE})."
        ),
    )
    sp_snap.set_defaults(func=cmd_snapshot)

    sp_shots = sub.add_parser(
        "screenshots",
        help=(
            "Save a full-page PNG screenshot of every article as a visual "
            "backup (requires playwright)."
        ),
    )
    sp_shots.add_argument(
        "--viewport-width",
        type=int,
        default=DEFAULT_SCREENSHOT_VIEWPORT_WIDTH,
        help=(
            "Browser viewport width in pixels for the capture "
            f"(default {DEFAULT_SCREENSHOT_VIEWPORT_WIDTH})."
        ),
    )
    sp_shots.set_defaults(func=cmd_screenshots)

    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
