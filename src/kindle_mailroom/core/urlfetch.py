"""Fetch public articles by URL for the URL → Kindle mode."""

from __future__ import annotations

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .images import fetch_image, parse_declared_length
from .sanitize import sanitize_html

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

URL_IMAGE_BUDGET = 6 * 1024 * 1024


def fetch_article(url: str) -> tuple[str, str]:
    """Return (title, html_body) for the article at url."""
    resp = requests.get(url, headers=HTTP_HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    # Title: <title> tag is most reliable (h1 often contains publication name on Substack)
    if soup.title and soup.title.get_text(strip=True):
        raw = soup.title.get_text(strip=True)
        raw = re.sub(r"\s*[-–—]\s*by\s+.+$", "", raw, flags=re.IGNORECASE).strip()
        raw = re.split(r"\s*\|\s*", raw)[0].strip()
        title = raw or "Article"
    else:
        title = "Article"

    # Body: try known article containers in priority order
    body_el = (
        soup.find(class_=re.compile(
            r"available-content|post-content|entry-content|article-body|body-text|body-markup", re.I))
        or soup.find("article")
        or soup.find("main")
    )
    if body_el is None:
        body_el = soup.body

    for tag in (body_el or soup).find_all(["nav", "footer", "aside", "script", "style", "button", "form"]):
        tag.decompose()

    if body_el is None:
        return title, "<p>No content extracted.</p>"

    # Lazy-loaded images keep the real URL in data-src; promote it before
    # sanitizing, which keeps only src on <img>. Without this, sanitising
    # would silently drop every lazy image the old raw path used to embed.
    for img in body_el.find_all("img"):
        if not img.get("src") and img.get("data-src"):
            img["src"] = img["data-src"]

    # The page is third-party content, so it gets the same attribute
    # whitelist as Gmail mode - otherwise onclick/iframe/svg from a fetched
    # article ride straight into the EPUB.
    return title, sanitize_html(str(body_el))


def download_images(html_body: str, page_url: str) -> tuple[str, list[tuple[str, str, bytes]]]:
    """Download images referenced in html_body, rewrite src to in-book paths,
    and return (new_html, [(path, media_type, data), ...]).

    Routes each image through fetch_image, so URL mode gets the same icon
    filtering, downscaling, and recompression as Gmail mode, under a shared
    byte budget."""
    soup = BeautifulSoup(html_body, "lxml")
    images: list[tuple[str, str, bytes]] = []
    seen: dict[str, str | None] = {}  # abs_url -> in-book path (None = dropped)
    bytes_used = 0
    idx = 0

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if not src or src.startswith("data:"):
            img.decompose()
            continue

        abs_url = urljoin(page_url, src)
        if abs_url in seen:
            local = seen[abs_url]
            if local:
                img["src"] = local
                if img.get("srcset"):
                    del img["srcset"]
            else:
                img.decompose()
            continue

        declared_w = parse_declared_length(img.get("width"))
        declared_h = parse_declared_length(img.get("height"))
        result = fetch_image(abs_url, idx, declared_w, declared_h)
        if not result or bytes_used + len(result[2]) > URL_IMAGE_BUDGET:
            seen[abs_url] = None
            img.decompose()
            continue

        path, media_type, data, width, height = result
        images.append((path, media_type, data))
        seen[abs_url] = path
        bytes_used += len(data)
        idx += 1

        img["src"] = path
        # Kindle's converter stretches <img> tags with no width/height to
        # fill the column, turning small icons into full-page blowups.
        # Stamp the real embedded size so it can't do that.
        if width and height:
            img["width"] = str(width)
            img["height"] = str(height)
        else:
            for attr in ("width", "height"):
                if img.get(attr):
                    del img[attr]
        # Remove srcset so Kindle doesn't try external URLs
        if img.get("srcset"):
            del img["srcset"]

    body = soup.find("body")
    return (str(body) if body else str(soup)), images


def get_article_date(url: str) -> str:
    """Fetch the article:modified_time meta tag to use for chronological sorting."""
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=20)
        soup = BeautifulSoup(resp.text, "lxml")
        meta = soup.find("meta", property="article:modified_time")
        if meta and meta.get("content"):
            return meta["content"][:10]
    except Exception:
        pass
    return "9999-99-99"
