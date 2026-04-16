# theface.com Article Scraper

A standalone Python sub-package for archiving every article Olive Pometsey
wrote for [theface.com](https://theface.com) before the publication shuts
down. Lives alongside the main React portfolio but is otherwise independent —
it does not interact with Firebase, the website, or any other part of this
repo.

## What it does

Given the contributor URL
[`/contributors/olive-pometsey`](https://theface.com/contributors/olive-pometsey)
(15 paginated pages):

1. **Discovers** every article URL by walking pages 1 through 15.
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
3. **Optionally** renders a pixel-perfect PDF snapshot of every page using
   headless Chromium (Playwright). This is the closest thing to "screenshot
   every page" — useful as a belt-and-braces backup if the source site
   disappears entirely.

## Output layout

```
scraper/output/
├── article_urls.json        # cached URL index (re-discover with --refresh)
├── scrape_summary.json      # per-article success/failure log
├── articles/
│   └── 2024-10-18_lexa-gates-interview-new-album-elite-vessel/
│       ├── article.html
│       ├── article.md
│       ├── metadata.json
│       └── images/
│           ├── 00_hero.jpg
│           ├── 01_some-image.jpg
│           └── ...
└── pdfs/                    # only if you run `snapshot`
    └── lexa-gates-interview-new-album-elite-vessel.pdf
```

`output/` is gitignored — none of the scraped content gets committed to the
repo. Move the folder onto a backup drive once the scrape finishes.

## Setup

```bash
cd scraper
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.10+ is required.

> **Why `brotli`?** theface.com serves Brotli-encoded responses; without the
> `brotli` Python library, `requests` returns gibberish for the listing pages.

## Usage

All commands are run from inside `scraper/` and accept the same global flags
(`--output-dir`, `--max-pages`, `--delay`, `--limit`, `--refresh`).

### 1. Discover article URLs (fast sanity check)

```bash
python scrape.py discover
```

Walks pages 1–15 of the contributor index and writes the full URL list to
`output/article_urls.json`. Useful to eyeball before kicking off the full
scrape.

### 2. Scrape everything

```bash
python scrape.py scrape
```

For every URL in the index, downloads HTML + Markdown + metadata + every
image. Re-running is safe — finished articles get overwritten with fresh
copies. To process just the first few articles while you tune things:

```bash
python scrape.py scrape --limit 3
```

To re-discover URLs (e.g. if she's published something new):

```bash
python scrape.py scrape --refresh
```

To skip image downloads (much faster, useful for a text-only first pass):

```bash
python scrape.py scrape --skip-images
```

### 3. Render PDF snapshots (optional)

```bash
pip install playwright
playwright install chromium
python scrape.py snapshot
```

Writes one PDF per article into `output/pdfs/`. This uses a real headless
browser, so it picks up any client-rendered content that the HTML scraper
might miss (lazy-loaded image variants, embeds, etc.).

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
├── requirements.txt
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
