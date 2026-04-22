"""Extract metadata, body text, and inline images from a single article."""

from __future__ import annotations

import html as html_lib
import json
import mimetypes
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

from .http import polite_get


# ---------------------------------------------------------------------------
# Metadata model
# ---------------------------------------------------------------------------


@dataclass
class ArticleMetadata:
    url: str
    slug: str
    section: Optional[str]
    title: Optional[str]
    standfirst: Optional[str]
    author: Optional[str]
    publication_date: Optional[str]
    tags: List[str] = field(default_factory=list)
    hero_image_url: Optional[str] = None
    image_urls: List[str] = field(default_factory=list)


@dataclass
class ScrapedArticle:
    metadata: ArticleMetadata
    raw_html: str
    markdown: str
    images: List[Tuple[str, bytes, str]]  # (filename, bytes, content_type)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _meta(soup: BeautifulSoup, name: str) -> Optional[str]:
    tag = soup.find("meta", attrs={"name": name})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


def _meta_property(soup: BeautifulSoup, prop: str) -> Optional[str]:
    tag = soup.find("meta", attrs={"property": prop})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


def _slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    # Take the trailing path component, e.g. "music/foo-bar" -> "foo-bar".
    return path.rsplit("/", 1)[-1] if "/" in path else path


def _section_from_url(url: str) -> Optional[str]:
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    return parts[0] if len(parts) >= 2 else None


def _strip_image_query(url: str) -> str:
    """Drop the resize / focal-point / cache-bust params to get the original."""
    if "?" in url:
        return url.split("?", 1)[0]
    return url


def _best_image_src(img: Tag) -> Optional[str]:
    """Pick the highest-quality src from a (possibly lazy-loaded) <img>.

    Theface lazy-loads with `data-src` + `data-srcset`. The non-lazy `src` on
    those images is just a 16px placeholder — useless. Prefer data-src.
    """
    for attr in ("data-src", "src"):
        val = img.get(attr)
        if not val:
            continue
        val = val.strip()
        # Skip tiny placeholders and gallery-deferred references.
        if val.startswith("#"):
            continue
        if "thefacecdn" not in val:
            # Inline base64 placeholder, tracking pixel, etc. — skip.
            if val.startswith("data:"):
                continue
        return val
    return None


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


_INLINE_TAGS = {"a", "strong", "b", "em", "i", "span", "u"}


def _inline_to_md(node) -> str:
    """Render an inline element (or text node) to Markdown."""
    if isinstance(node, NavigableString):
        return str(node)
    if not isinstance(node, Tag):
        return ""

    name = node.name.lower()
    inner = "".join(_inline_to_md(c) for c in node.children).strip()

    if name == "a":
        href = node.get("href", "").strip()
        if href and inner:
            return f"[{inner}]({href})"
        return inner
    if name in {"strong", "b"}:
        return f"**{inner}**" if inner else ""
    if name in {"em", "i"}:
        return f"*{inner}*" if inner else ""
    if name == "br":
        return "\n"
    # Default: pass through inner text.
    return inner


def _block_to_md(block: Tag) -> str:
    """Render one content-builder block to Markdown."""
    classes = block.get("class", []) or []
    kind = next(
        (c for c in classes if c.startswith("content-builder__block--")),
        None,
    )

    if kind == "content-builder__block--heading":
        # Use the inner heading element (h2/h3/...) if present.
        heading = block.find(["h2", "h3", "h4", "h5"])
        text = (heading.get_text(" ", strip=True) if heading else
                block.get_text(" ", strip=True))
        if not text:
            return ""
        level = int(heading.name[1]) if heading and heading.name[0] == "h" else 2
        return f"\n{'#' * level} {text}\n"

    if kind == "content-builder__block--body":
        parts: List[str] = []
        for child in block.find_all(["p", "h2", "h3", "h4", "blockquote",
                                      "ul", "ol"], recursive=True):
            tag = child.name
            if tag == "p":
                text = "".join(_inline_to_md(c) for c in child.children).strip()
                if text:
                    parts.append(text)
            elif tag in {"h2", "h3", "h4"}:
                level = int(tag[1])
                text = child.get_text(" ", strip=True)
                if text:
                    parts.append(f"\n{'#' * level} {text}")
            elif tag == "blockquote":
                text = child.get_text(" ", strip=True)
                if text:
                    parts.append("> " + text.replace("\n", "\n> "))
            elif tag in {"ul", "ol"}:
                bullet = "-" if tag == "ul" else "1."
                items = []
                for li in child.find_all("li", recursive=False):
                    li_text = "".join(_inline_to_md(c) for c in li.children).strip()
                    if li_text:
                        items.append(f"{bullet} {li_text}")
                if items:
                    parts.append("\n".join(items))
        return "\n\n".join(parts)

    if kind in {"content-builder__block--images",
                "content-builder__block--image"}:
        # Images are referenced separately in the metadata; just leave a
        # placeholder so the reader knows where they sat in the flow.
        srcs = [
            _best_image_src(img)
            for img in block.find_all("img")
        ]
        srcs = [s for s in srcs if s]
        if not srcs:
            return ""
        lines = [f"![]({_strip_image_query(s)})" for s in srcs]
        return "\n\n".join(lines)

    if kind == "content-builder__block--quote":
        text = block.get_text(" ", strip=True)
        return f"> {text}" if text else ""

    if kind == "content-builder__block--embed-code":
        # Embeds (Spotify, YouTube, Twitter, etc.) aren't usefully convertible
        # to text — note the URL if there's a recognisable one.
        iframe = block.find("iframe")
        if iframe and iframe.get("src"):
            return f"[Embedded media]({iframe['src']})"
        link = block.find("a", href=True)
        if link:
            return f"[Embedded link]({link['href']})"
        return ""

    # Skip "read-this-next", related-articles, etc.
    return ""


def _render_markdown(meta: ArticleMetadata, soup: BeautifulSoup) -> str:
    parts: List[str] = []
    if meta.title:
        parts.append(f"# {meta.title}")
    if meta.standfirst:
        parts.append(f"_{meta.standfirst}_")
    byline_bits = []
    if meta.author:
        byline_bits.append(f"By {meta.author}")
    if meta.publication_date:
        byline_bits.append(meta.publication_date)
    if meta.section:
        byline_bits.append(meta.section)
    if byline_bits:
        parts.append(" · ".join(byline_bits))
    parts.append(f"[Original article]({meta.url})")
    if meta.hero_image_url:
        parts.append(f"![Hero image]({meta.hero_image_url})")

    # Walk every content-builder block in document order. This preserves the
    # interleaving of headings, body copy and inline images the journalist
    # laid down.
    for block in soup.select(".content-builder__block"):
        rendered = _block_to_md(block)
        if rendered.strip():
            parts.append(rendered.strip())

    return "\n\n".join(parts).strip() + "\n"


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------


def _extract_standfirst(soup: BeautifulSoup) -> Optional[str]:
    # Prefer the JSON parsely-metadata field (HTML-encoded in attribute).
    raw = _meta(soup, "parsely-metadata")
    if raw:
        try:
            data = json.loads(raw)
            sf = data.get("standfirst")
            if sf:
                # The standfirst may itself be HTML — strip tags for the plain
                # version we surface in Markdown / metadata.json.
                return BeautifulSoup(html_lib.unescape(sf), "lxml").get_text(
                    " ", strip=True
                )
        except json.JSONDecodeError:
            pass
    sf_div = soup.select_one(".standfirst")
    if sf_div:
        return sf_div.get_text(" ", strip=True)
    return None


def _extract_image_urls(soup: BeautifulSoup) -> Tuple[Optional[str], List[str]]:
    """Return (hero_url, [inline_url, ...]) — all stripped of query params."""
    hero: Optional[str] = None

    # Hero: parsely-image-url is the original, no resize params. Fall back to
    # the first .image-box__image on the page.
    parsely_img = _meta(soup, "parsely-image-url")
    if parsely_img:
        hero = _strip_image_query(parsely_img)
    else:
        hero_img = soup.select_one(".image-box__image")
        if hero_img:
            src = _best_image_src(hero_img)
            if src:
                hero = _strip_image_query(src)

    seen: set[str] = set()
    if hero:
        seen.add(hero)
    inline: List[str] = []

    # Inline images live in image / images content-builder blocks. Walk those
    # in document order so the order matches the article.
    for block in soup.select(
        ".content-builder__block--images, .content-builder__block--image"
    ):
        for img in block.find_all("img"):
            src = _best_image_src(img)
            if not src:
                continue
            clean = _strip_image_query(src)
            if clean in seen:
                continue
            seen.add(clean)
            inline.append(clean)

    return hero, inline


def parse_article(url: str, html: str) -> Tuple[ArticleMetadata, str]:
    """Parse an article's HTML, returning metadata and Markdown body."""
    soup = BeautifulSoup(html, "lxml")

    title = _meta(soup, "parsely-title") or _meta_property(soup, "og:title")
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(" ", strip=True)

    author = _meta(soup, "parsely-author")
    pub_date = _meta(soup, "parsely-pub-date")
    section = _meta(soup, "parsely-section") or _section_from_url(url)
    tags_raw = _meta(soup, "parsely-tags") or ""
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    standfirst = _extract_standfirst(soup)
    hero_url, inline_urls = _extract_image_urls(soup)

    meta = ArticleMetadata(
        url=url,
        slug=_slug_from_url(url),
        section=section,
        title=title,
        standfirst=standfirst,
        author=author,
        publication_date=pub_date,
        tags=tags,
        hero_image_url=hero_url,
        image_urls=inline_urls,
    )
    markdown = _render_markdown(meta, soup)
    return meta, markdown


# ---------------------------------------------------------------------------
# Image download
# ---------------------------------------------------------------------------


_SAFE_FN = re.compile(r"[^A-Za-z0-9._-]+")


def _filename_for(idx: int, url: str, fallback_ext: str = ".jpg") -> str:
    """Pick a safe local filename for a downloaded image."""
    parsed = urlparse(url)
    base = parsed.path.rsplit("/", 1)[-1] or f"image-{idx:02d}"
    base = _SAFE_FN.sub("_", base)
    if "." not in base:
        base += fallback_ext
    return f"{idx:02d}_{base}"


def _ext_from_response(resp: requests.Response, default: str = ".jpg") -> str:
    ct = resp.headers.get("Content-Type", "").split(";")[0].strip()
    if ct:
        guess = mimetypes.guess_extension(ct)
        if guess:
            return guess
    return default


def download_images(
    session: requests.Session,
    meta: ArticleMetadata,
    *,
    delay: float = 0.4,
    referer: Optional[str] = None,
) -> List[Tuple[str, bytes, str]]:
    """Download every image referenced in the metadata.

    Returns a list of `(filename, bytes, content_type)`. Failures are logged
    by skipping — we'd rather lose one image than fail the whole article.
    """
    referer = referer or meta.url
    targets: List[Tuple[str, str]] = []
    if meta.hero_image_url:
        targets.append(("hero", meta.hero_image_url))
    for url in meta.image_urls:
        targets.append(("inline", url))

    out: List[Tuple[str, bytes, str]] = []
    for idx, (kind, url) in enumerate(targets):
        try:
            resp = polite_get(
                session,
                url,
                delay=delay,
                referer=referer,
                stream=True,
                max_retries=2,
            )
        except requests.RequestException:
            continue
        if resp.status_code != 200:
            continue
        content_type = resp.headers.get("Content-Type", "image/jpeg")
        ext = _ext_from_response(resp)
        prefix = "00_hero" if kind == "hero" else f"{idx:02d}"
        # Re-derive a clean filename — preserve the source basename if any.
        base = _filename_for(idx, url, fallback_ext=ext)
        if kind == "hero":
            base = "00_hero" + (Path(base).suffix or ext)
        try:
            data = resp.content
        except Exception:
            continue
        out.append((base, data, content_type))
    return out


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def scrape_article(
    session: requests.Session,
    url: str,
    *,
    delay: float = 1.5,
    download_images_too: bool = True,
) -> ScrapedArticle:
    """Fetch one article, parse it, and (optionally) download its images."""
    resp = polite_get(session, url, delay=delay, referer="https://theface.com/")
    resp.raise_for_status()
    raw_html = resp.text
    metadata, markdown = parse_article(url, raw_html)
    images: List[Tuple[str, bytes, str]] = []
    if download_images_too:
        images = download_images(session, metadata, referer=url)
    return ScrapedArticle(
        metadata=metadata, raw_html=raw_html, markdown=markdown, images=images
    )


# ---------------------------------------------------------------------------
# Disk persistence
# ---------------------------------------------------------------------------


def slug_dir_name(meta: ArticleMetadata) -> str:
    """Build a tidy folder name like `2024-10-18_lexa-gates-...`."""
    date = (meta.publication_date or "").split("T")[0]
    if date:
        return f"{date}_{meta.slug}"
    return meta.slug


def write_article_to_disk(article: ScrapedArticle, root: Path) -> Path:
    """Persist a scraped article + its images to disk. Returns the dir path."""
    folder = root / slug_dir_name(article.metadata)
    (folder / "images").mkdir(parents=True, exist_ok=True)

    (folder / "article.html").write_text(article.raw_html, encoding="utf-8")
    (folder / "article.md").write_text(article.markdown, encoding="utf-8")
    (folder / "metadata.json").write_text(
        json.dumps(asdict(article.metadata), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    for filename, data, _ct in article.images:
        (folder / "images" / filename).write_bytes(data)
    return folder
