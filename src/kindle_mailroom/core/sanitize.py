"""Kindle-safe HTML sanitization.

This logic is battle-tested against Amazon's EPUB converter: it removes
constructs Kindle can't render and — critically — empty block elements, which
ebooklib serialises as self-closing tags that Amazon rejects with E999 errors.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Comment

# Zero-width and other invisible characters that inflate word counts and can
# confuse Amazon's converter.
_INVISIBLE_CHARS = "[​-‏­  ﻿ ]"


def style_length(style: str | None, prop: str) -> str | None:
    """Pull a pixel length out of an inline style, e.g. style="width: 14px"
    -> "14". Returns None for percentages, "auto", or a missing property:
    those express "fill the container", not a fixed display size."""
    if not style:
        return None
    m = re.search(rf"(?:^|;)\s*{prop}\s*:\s*(\d+(?:\.\d+)?)\s*px", style, re.I)
    return str(int(float(m.group(1)))) if m else None


def sanitize_html(raw_html: str) -> str:
    raw_html = re.sub(_INVISIBLE_CHARS, "", raw_html)
    soup = BeautifulSoup(raw_html, "lxml")

    # remove comments (includes MSO conditionals)
    for node in soup.find_all(string=lambda t: isinstance(t, Comment)):
        node.extract()

    # remove elements Kindle can't use at all
    for tag in soup(["script", "style", "meta", "link", "form", "iframe", "head", "nav"]):
        tag.decompose()

    # replace HTML5 semantic containers with div/p (Kindle doesn't support them)
    for tag in soup.find_all(["main", "article", "section", "aside", "header", "footer", "figure"]):
        tag.name = "div"
    for tag in soup.find_all(["figcaption", "address"]):
        tag.name = "p"

    # unwrap layout tables (no <th> and no scope/headers = pure layout table)
    for table in soup.find_all("table"):
        if not table.find("th") and not any(
            td.get("scope") or td.get("headers")
            for td in table.find_all(["td", "tr"])
        ):
            for td in table.find_all("td"):
                td.unwrap()
            for tr in table.find_all("tr"):
                tr.unwrap()
            for group in table.find_all(["tbody", "thead", "tfoot"]):
                group.unwrap()
            table.unwrap()

    # Newsletter templates (Substack, Mailchimp) wrap their whole layout in
    # <center> for the benefit of ancient email clients. We strip the align=
    # and style= attributes that would centre things, but the <center>
    # element itself is presentational markup with no attribute to strip -
    # left in place it centres the entire article body on the Kindle.
    for tag in soup.find_all("center"):
        tag.unwrap()

    # remove tracking/spacer images (1x1 or 0x0)
    for img in soup.find_all("img"):
        if img.get("width") in ("0", "1") or img.get("height") in ("0", "1"):
            img.decompose()

    body = soup.body or soup

    # strip attributes, keeping only what Kindle needs
    for tag in body.find_all(True):
        allowed_attrs = {}
        if tag.name == "a" and tag.get("href"):
            allowed_attrs["href"] = tag["href"]
        if tag.name == "img" and tag.get("src"):
            allowed_attrs["src"] = tag["src"]
            allowed_attrs["alt"] = tag.get("alt", "")
            # Keep declared size: Kindle's converter stretches any <img>
            # lacking width/height to fill the column, so dropping these
            # turns small icons into full-width blowups. embed_images()
            # overwrites them with the real embedded pixel size anyway.
            # Many senders declare the size only in CSS (Every's app icons
            # use style="width: 14px"), so fall back to the style attribute
            # before it gets stripped - otherwise a 14px icon looks
            # undeclared and gets embedded at its full 512px source size.
            width = tag.get("width") or style_length(tag.get("style"), "width")
            height = tag.get("height") or style_length(tag.get("style"), "height")
            if width:
                allowed_attrs["width"] = width
            if height:
                allowed_attrs["height"] = height
        tag.attrs = allowed_attrs

    # remove empty block elements: ebooklib round-trips through lxml XML which
    # serialises <div></div> as <div/> - invalid XHTML that Amazon rejects (E999)
    for tag in body.find_all(["div", "p", "span", "li", "blockquote"]):
        if not tag.get_text(strip=True) and not tag.find(["img", "br", "hr"]):
            tag.decompose()

    return str(body)


def count_words(html_body: str) -> int:
    soup = BeautifulSoup(html_body, "lxml")
    text = soup.get_text(separator=" ", strip=True)
    clean = re.sub(_INVISIBLE_CHARS + "+", " ", text)
    return len(clean.split())
