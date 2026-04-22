#!/usr/bin/env python3
"""CLI entry point for archiving contributor articles from theface.com.

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
from dataclasses import dataclass
from pathlib import Path
from typing import List

from tqdm import tqdm

from theface.article import (
    scrape_article,
    slug_dir_name,
    write_article_to_disk,
)
from theface.http import build_session
from theface.listing import (
    DEFAULT_CONTRIBUTOR_SLUG,
    EXPECTED_AUTHOR,
    collect_all_article_urls,
    contributor_base_url,
    filter_exclusive_article_urls,
)

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "output"


@dataclass(frozen=True)
class ContributorTarget:
    author_name: str
    contributor_slug: str
    output_dir: Path

    @property
    def contributor_base(self) -> str:
        return contributor_base_url(self.contributor_slug)


def _author_check_delay(delay: float) -> float:
    """Use a shorter, still-polite delay for credit-box verification fetches."""
    return max(0.4, delay * 0.5)


def _write_url_index(index_path: Path, urls: List[str]) -> None:
    index_path.write_text(json.dumps(urls, indent=2), encoding="utf-8")


def _load_url_index(index_path: Path) -> List[str]:
    raw = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not all(isinstance(url, str) for url in raw):
        raise ValueError(f"Unexpected URL index format in {index_path}")
    return raw


def _build_targets(args: argparse.Namespace) -> List[ContributorTarget]:
    if args.author_name is None and args.contributor_slug is None:
        author_names = [EXPECTED_AUTHOR]
        contributor_slugs = [DEFAULT_CONTRIBUTOR_SLUG]
    elif args.author_name is None or args.contributor_slug is None:
        raise ValueError(
            "Provide both `--author-name` and `--contributor-slug`, in the same order."
        )
    else:
        author_names = args.author_name
        contributor_slugs = args.contributor_slug

    if len(contributor_slugs) != len(author_names):
        raise ValueError(
            "Provide `--contributor-slug` once per `--author-name`, in the same order."
        )

    targets: List[ContributorTarget] = []
    for idx, raw_author_name in enumerate(author_names):
        author_name = " ".join(raw_author_name.split())
        if not author_name:
            raise ValueError("`--author-name` must not be empty.")
        contributor_slug = contributor_slugs[idx].strip()
        if not contributor_slug:
            raise ValueError("`--contributor-slug` must not be empty.")
        output_dir = args.output_dir / contributor_slug
        targets.append(
            ContributorTarget(
                author_name=author_name,
                contributor_slug=contributor_slug,
                output_dir=output_dir,
            )
        )
    return targets


def _print_target_header(target: ContributorTarget, *, multi: bool) -> None:
    if multi:
        print(
            f"\n==> {target.author_name} ({target.contributor_slug})",
            file=sys.stderr,
        )


def _discover_urls(
    args: argparse.Namespace, session, target: ContributorTarget
) -> List[str]:
    out_dir = target.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    total_pages = max(0, args.max_pages - args.start_page + 1)
    print(
        f"Scanning listing pages {args.start_page}..{args.max_pages} for "
        f"{target.author_name}...",
        file=sys.stderr,
    )
    page_bar = tqdm(total=total_pages, desc="Scanning listing pages", unit="page")

    def _on_page(page: int, new_count: int) -> None:
        page_bar.update(1)

    candidate_urls = collect_all_article_urls(
        session,
        start_page=args.start_page,
        max_pages=args.max_pages,
        delay=args.delay,
        contributor_base=target.contributor_base,
        expected_author=None,
        page_progress=_on_page,
    )
    page_bar.close()
    print(
        f"Verifying visible `Words:` credit across {len(candidate_urls)} "
        f"candidate URLs for {target.author_name}...",
        file=sys.stderr,
    )
    verify_bar = tqdm(
        total=len(candidate_urls),
        desc="Verifying `Words:` credit",
        unit="url",
    )

    def _on_verify(url: str, authors: List[str], keep: bool) -> None:
        verify_bar.update(1)

    urls = filter_exclusive_article_urls(
        session,
        candidate_urls,
        expected_author=target.author_name,
        contributor_base=target.contributor_base,
        delay=_author_check_delay(args.delay),
        progress=_on_verify,
    )
    verify_bar.close()
    index_path = out_dir / "article_urls.json"
    _write_url_index(index_path, urls)
    print(
        f"\nFound {len(urls)} articles credited only to {target.author_name}. "
        f"Wrote {index_path}."
    )
    return urls


def _load_saved_urls(target: ContributorTarget) -> List[str]:
    index_path = target.output_dir / "article_urls.json"
    if not index_path.exists():
        raise FileNotFoundError(
            f"Missing {index_path} for {target.author_name}. "
            "Run `theface-scraper discover "
            f"--author-name \"{target.author_name}\" "
            f"--contributor-slug \"{target.contributor_slug}\"` first."
        )
    urls = _load_url_index(index_path)
    print(
        f"Loaded {len(urls)} URLs for {target.author_name} from {index_path}.",
        file=sys.stderr,
    )
    return urls


def cmd_discover(args: argparse.Namespace) -> int:
    try:
        targets = _build_targets(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    session = build_session()
    multi = len(targets) > 1
    for target in targets:
        _print_target_header(target, multi=multi)
        _discover_urls(args, session, target)
    return 0


def cmd_scrape(args: argparse.Namespace) -> int:
    try:
        targets = _build_targets(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    session = build_session()
    multi = len(targets) > 1
    exit_code = 0
    for target in targets:
        _print_target_header(target, multi=multi)
        out_dir = target.output_dir
        articles_dir = out_dir / "articles"
        articles_dir.mkdir(parents=True, exist_ok=True)

        try:
            urls = _load_saved_urls(target)
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            exit_code = max(exit_code, 2)
            continue
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
            "author_name": target.author_name,
            "contributor_slug": target.contributor_slug,
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
            f"\nDone for {target.author_name}. {len(successes)}/{len(urls)} "
            f"succeeded. Summary: {summary_path}"
        )
        if failures:
            exit_code = max(exit_code, 1)
    return exit_code


def cmd_snapshot(args: argparse.Namespace) -> int:
    from theface.snapshot import partition_existing_outputs, render_pdfs
    from theface.http import DEFAULT_UA

    try:
        targets = _build_targets(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    multi = len(targets) > 1
    exit_code = 0
    for target in targets:
        _print_target_header(target, multi=multi)
        out_dir = target.output_dir
        pdf_dir = out_dir / "pdfs"
        try:
            urls = _load_saved_urls(target)
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            exit_code = max(exit_code, 2)
            continue
        if args.limit:
            urls = urls[: args.limit]
        existing_urls, missing_urls = partition_existing_outputs(
            urls,
            pdf_dir,
            suffix=".pdf",
        )
        if existing_urls:
            print(
                f"Skipping {len(existing_urls)} existing PDFs for {target.author_name}.",
                file=sys.stderr,
            )
        print(
            f"Rendering {len(missing_urls)} PDFs for {target.author_name} into {pdf_dir}...",
            file=sys.stderr,
        )
        bar = tqdm(
            total=len(urls),
            initial=len(existing_urls),
            desc="Rendering PDFs",
            unit="pdf",
        )
        failures = render_pdfs(
            missing_urls,
            pdf_dir,
            user_agent=DEFAULT_UA,
            viewport_width=args.viewport_width,
            scale=args.pdf_scale,
            progress=lambda u, p: bar.update(1),
            warning=lambda u, p, e: tqdm.write(f"  ! failed {u}: {e}"),
        )
        bar.close()
        if failures:
            print(
                f"Done for {target.author_name} with {len(failures)} PDF failures.",
                file=sys.stderr,
            )
            exit_code = max(exit_code, 1)
        else:
            print("Done.")
    return exit_code


def cmd_screenshots(args: argparse.Namespace) -> int:
    from theface.snapshot import partition_existing_outputs, take_screenshots
    from theface.http import DEFAULT_UA

    try:
        targets = _build_targets(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    multi = len(targets) > 1
    exit_code = 0
    for target in targets:
        _print_target_header(target, multi=multi)
        out_dir = target.output_dir
        shots_dir = out_dir / "screenshots"
        try:
            urls = _load_saved_urls(target)
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            exit_code = max(exit_code, 2)
            continue
        if args.limit:
            urls = urls[: args.limit]
        existing_urls, missing_urls = partition_existing_outputs(
            urls,
            shots_dir,
            suffix=".png",
        )
        if existing_urls:
            print(
                f"Skipping {len(existing_urls)} existing screenshots for "
                f"{target.author_name}.",
                file=sys.stderr,
            )
        print(
            f"Capturing {len(missing_urls)} full-page screenshots for {target.author_name} "
            f"into {shots_dir}...",
            file=sys.stderr,
        )
        bar = tqdm(
            total=len(urls),
            initial=len(existing_urls),
            desc="Taking screenshots",
            unit="png",
        )
        failures = take_screenshots(
            missing_urls,
            shots_dir,
            user_agent=DEFAULT_UA,
            viewport_width=args.viewport_width,
            progress=lambda u, p: bar.update(1),
            warning=lambda u, p, e: tqdm.write(f"  ! failed {u}: {e}"),
        )
        bar.close()
        if failures:
            print(
                f"Done for {target.author_name} with {len(failures)} screenshot failures.",
                file=sys.stderr,
            )
            exit_code = max(exit_code, 1)
        else:
            print("Done.")
    return exit_code


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Where to write outputs (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument("--start-page", type=int, default=1,
                        help="First listing page to scan (default 1).")
    parser.add_argument("--max-pages", type=int, default=15,
                        help="Last listing page to scan (default 15).")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="Polite delay (seconds) between requests.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Process at most N article URLs (for testing).")
    parser.add_argument(
        "--author-name",
        action="append",
        default=None,
        help=(
            "Contributor name to match in the visible `Words:` box. Repeat to "
            "process multiple contributors in order."
        ),
    )
    parser.add_argument(
        "--contributor-slug",
        action="append",
        default=None,
        help=(
            "theface contributor slug for each `--author-name`. Repeat once per "
            "author and keep the same order. Required whenever you pass "
            "`--author-name`."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    from theface.snapshot import (
        DEFAULT_PDF_SCALE,
        DEFAULT_PDF_VIEWPORT_WIDTH,
        DEFAULT_SCREENSHOT_VIEWPORT_WIDTH,
    )

    p = argparse.ArgumentParser(
        description="Scrape contributor articles from theface.com.",
    )
    common = argparse.ArgumentParser(add_help=False)
    _add_common_args(common)

    sub = p.add_subparsers(dest="command", required=True)

    sp_discover = sub.add_parser(
        "discover",
        parents=[common],
        help="List all article URLs (writes article_urls.json).",
    )
    sp_discover.set_defaults(func=cmd_discover)

    sp_scrape = sub.add_parser(
        "scrape",
        parents=[common],
        help="Download HTML + Markdown + metadata + images for every article.",
    )
    sp_scrape.add_argument("--skip-images", action="store_true",
                           help="Don't download referenced images.")
    sp_scrape.set_defaults(func=cmd_scrape)

    sp_snap = sub.add_parser(
        "snapshot",
        parents=[common],
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
        parents=[common],
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
