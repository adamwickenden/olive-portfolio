# theface.com Article Scraper

A standalone Python sub-package for archiving contributor articles from
[theface.com](https://theface.com). It defaults to Olive Pometsey, but you
can point it at other contributors too. Lives alongside the main React
portfolio but is otherwise independent — it does not interact with Firebase,
the website, or any other part of this repo.

## What it does

Given a contributor URL such as
[`/contributors/olive-pometsey`](https://theface.com/contributors/olive-pometsey)
(15 paginated pages):

1. **Discovers** every article URL by walking pages 1 through 15.
   Then verifies each candidate article's visible `Words:` contributor box
   and keeps only pieces credited exclusively to the requested contributor,
   excluding co-authored roundups and staff playlists.
2. **Scrapes** each article and saves four artefacts per piece:
   - `article.html` — the raw, untouched HTML (the most reliable archive).
   - `article.md`   — a clean Markdown render of the body, with headings,
     links, bold/italic, lists, embeds and image placeholders preserved in
     document order.
   - `metadata.json` — title, standfirst, author, date, section, tags, and
     the URLs of every image referenced.
   - `images/` — every hero/inline image, downloaded as the original
     full-resolution file (query parameters stripped from the CDN URL so we
     get the source asset, not a resized variant).
3. **Optionally** renders a pixel-perfect backup of every page using
   headless Chromium (Playwright):
   - `snapshot` → one A4 PDF per article, paginated.
   - `screenshots` → one full-page PNG per article (one tall image of the
     entire scrollable page).

   Use either (or both) as a belt-and-braces backup if the source site
   disappears entirely.

## Output layout

```
scraper/output/
├── olive-pometsey/
│   ├── article_urls.json
│   ├── scrape_summary.json
│   ├── articles/
│   ├── pdfs/
│   └── screenshots/
└── jade-wickes/
    ├── article_urls.json
    ├── scrape_summary.json
    ├── articles/
    ├── pdfs/
    └── screenshots/
```

`output/` is gitignored — none of the scraped content gets committed to the
repo. Move the folder onto a backup drive once the scrape finishes.

## Setup

```bash
cd scraper
uv sync
```

Python 3.10+ is required.
`uv` manages the local `.venv` for you, so there is no manual activation step
and no `requirements.txt` to maintain.

> **Why `brotli`?** theface.com serves Brotli-encoded responses; without the
> `brotli` Python library, `requests` returns gibberish for the listing pages.

For the browser-based backup commands, install Chromium once:

```bash
uv run playwright install chromium
```

## Usage

All commands are run from inside `scraper/` and accept the same global flags
(`--output-dir`, `--max-pages`, `--delay`, `--limit`, `--author-name`,
`--contributor-slug`).

`--author-name` is repeatable and preserves order. If you pass more than one
author, each contributor gets their own subdirectory under `output/`, keyed
by contributor slug.

Repeat `--contributor-slug` once per `--author-name` in the same order. This
script does not guess contributor slugs.

If you omit both flags entirely, the script still defaults to Olive, but now
stores that run under `output/olive-pometsey/`.

### 1. Discover article URLs (fast sanity check)

```bash
uv run theface-scraper discover
```

Walks pages 1–15 of the contributor index, then keeps only articles whose
visible `Words:` credit is exclusively the requested contributor before
overwriting that contributor's saved URL list at `output/<slug>/article_urls.json`.
Useful to eyeball before kicking off the full scrape.

Examples:

```bash
uv run theface-scraper discover --author-name "Jade Wickes" --contributor-slug "jade-wickes"
uv run theface-scraper discover --author-name "Jade Wickes" --contributor-slug "jade-wickes" --author-name "Davy Reed" --contributor-slug "davy-reed"
uv run theface-scraper discover --author-name "Craig McLean" --contributor-slug "craig-mclean"
```

### 2. Scrape everything

```bash
uv run theface-scraper scrape
```

Reads the matching saved `output/<slug>/article_urls.json`, then downloads
HTML + Markdown + metadata + every image for each URL. Run `discover` first
whenever you want to rebuild that list. Re-running is safe — finished
articles get overwritten with fresh copies. To process just the first few
articles while you tune things:

```bash
uv run theface-scraper scrape --limit 3
```

To skip image downloads (much faster, useful for a text-only first pass):

```bash
uv run theface-scraper scrape --skip-images
```

### 3. Render PDF snapshots (optional)

```bash
uv run theface-scraper snapshot
```

Writes one PDF per article into `output/<slug>/pdfs/`. This uses a real headless
browser, so it picks up any client-rendered content that the HTML scraper
might miss (lazy-loaded image variants, embeds, etc.). The PDF renderer now
uses screen media and a slight zoom-out so the page sits a bit more naturally
on A4. This command uses the URLs already saved in `output/<slug>/article_urls.json`.
Existing PDFs are skipped, so rerunning the same command resumes from the first
missing file, and the progress bar starts at the number already on disk.
Individual page failures are logged as warnings and do not abort the batch.
If you want to tune it further:

```bash
uv run theface-scraper snapshot --pdf-scale 0.9 --viewport-width 1366
```

### 4. Take full-page screenshots (optional visual backup)

```bash
uv run theface-scraper screenshots
```

Writes one PNG per article into `output/<slug>/screenshots/`. Each image is the
entire scrollable height of the page (not just the viewport), so a long
photo essay comes out as one tall image. The default capture width is tighter
than before so the article fills more of the frame. Tweak `--viewport-width`
if you want a narrower/wider capture (default 960 px). This command also
uses the URLs already saved in `output/<slug>/article_urls.json`. Existing
PNGs are skipped, so rerunning the same command resumes from the first
missing file, and the progress bar starts at the number already on disk.
Individual page failures are logged as warnings and do not abort the batch.

This is the simplest "if all else fails, we still have pictures of the
pages" backup — the PNG doesn't care about broken selectors, missing
classes, or future site changes.

## Polite behaviour

theface.com is fronted by Cloudflare and will throw 503s if you hammer it.
Defaults are deliberately conservative:

- 1.5 s polite delay (+ jitter) before every request.
- Browser-style `User-Agent` (the Cloudflare layer 403s plain
  `python-requests` UAs).
- Exponential backoff (4 s, 8 s, 16 s, 32 s) on any 5xx or 429 response.
- A real `Referer` header set to the parent listing/article page.

If you hit rate limits, raise `--delay` (e.g. `--delay 3.0`).

## Project layout

```
scraper/
├── README.md             # this file
├── pyproject.toml        # project metadata + dependencies for uv
├── uv.lock               # resolved dependency lockfile
├── scrape.py             # CLI entry point
└── theface/
    ├── __init__.py
    ├── http.py           # session, polite GET, retries
    ├── listing.py        # /contributors/.../pN  →  article URLs
    ├── article.py        # one URL → metadata + Markdown + downloaded images
    └── snapshot.py       # optional Playwright PDF renderer
```

## Extraction strategy (in case you ever need to debug or extend it)

- **Metadata** is read from theface.com's Parsely `<meta name="parsely-*">`
  tags rather than scraping the visible DOM. These are present and consistent
  across every article template (interviews, listicles, photo essays, news,
  reviews) and don't change when the design does.
- **Body** is rendered by walking `.content-builder__block--*` divs in
  document order and converting each block (`heading`, `body`, `images`,
  `embed-code`, `quote`) to Markdown. This preserves the journalist's
  original ordering of prose and imagery.
- **Images** are taken from `<img data-src="...">` (lazy-loaded full size),
  not the inline `src` (which is a 16-pixel placeholder). Query parameters
  are stripped so we get the original asset off the CDN
  (`https://files.thefacecdn.com/images/<filename>`), not a resized derivative.
