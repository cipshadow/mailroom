"""Build Kindle-friendly EPUBs from Gmail messages and web articles."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from bs4 import BeautifulSoup
from ebooklib import epub

from .images import fetch_image, parse_declared_length
from .models import GmailMessage, digest_title
from .sanitize import count_words

# Each image is checked against the *remaining* budget rather than a sticky
# cutoff: a long, chart-heavy article shouldn't lose every image past
# whichever one first pushed the running total over budget, when a later,
# smaller image would still fit in the leftover room. The 8MB ceiling
# triggers a full no-image rebuild: Gmail rejects attachments much beyond
# that once base64 overhead is added.
SINGLE_IMAGE_BUDGET = 6 * 1024 * 1024
DIGEST_IMAGE_BUDGET = 7 * 1024 * 1024
EPUB_SIZE_CEILING = 8 * 1024 * 1024

BASE_STYLE = """
body { font-family: Georgia, serif; line-height: 1.55; margin: 1em; }
h1 { font-size: 1.35em; margin-bottom: 0.2em; }
h2 { font-size: 1.15em; margin-top: 1.5em; margin-bottom: 0.3em; border-top: 1px solid #ddd; padding-top: 1em; }
.meta { color: #555; font-size: 0.85em; margin-bottom: 1.5em; }
img { max-width: 100%; height: auto; }
blockquote { border-left: 3px solid #ccc; margin-left: 0; padding-left: 1em; }
pre { white-space: pre-wrap; font-family: monospace; }
.toc { font-size: 0.95em; margin: 2em 0; }
.toc-entry { margin: 0.3em 0; margin-left: 1em; }
"""

ProgressFn = Callable[[str], None]


def _noop(_msg: str) -> None:
    pass


def make_safe_filename(value: str, fallback: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"[^\w .@()-]+", "", value)
    value = value[:90].strip(" .")
    return value or fallback


def _make_css() -> epub.EpubItem:
    return epub.EpubItem(
        uid="style",
        file_name="style/default.css",
        media_type="text/css",
        content=BASE_STYLE.encode("utf-8"),
    )


def _embed_images(book: epub.EpubBook, soup: BeautifulSoup, budget: int,
                  bytes_used: int = 0, uid_prefix: str = "img", idx_offset: int = 0) -> int:
    """Download and embed each remote <img> in soup, rewriting src to the
    in-book path. Returns the updated bytes_used."""
    img_count = 0
    for img in soup.find_all("img", src=True):
        src = img["src"]
        if not src.startswith("http"):
            img.decompose()
            continue
        declared_w = parse_declared_length(img.get("width"))
        declared_h = parse_declared_length(img.get("height"))
        result = fetch_image(src, idx_offset + img_count, declared_w, declared_h)
        if not result:
            img.decompose()
            continue
        epub_path, media_type, data, width, height = result
        if bytes_used + len(data) > budget:
            img.decompose()
            continue
        book.add_item(epub.EpubItem(
            uid=f"{uid_prefix}{img_count:03d}",
            file_name=epub_path,
            media_type=media_type,
            content=data,
        ))
        img["src"] = epub_path
        img["style"] = "max-width: 100%; height: auto;"
        # Kindle's converter stretches <img> tags with no width/height to fill
        # the column width, which is exactly what turns a small icon into a
        # full-page blowup. Stamping the real embedded size prevents that.
        if width and height:
            img["width"] = str(width)
            img["height"] = str(height)
        else:
            for attr in ("width", "height"):
                if img.get(attr):
                    del img[attr]
        bytes_used += len(data)
        img_count += 1
    return bytes_used


def _strip_all_images(html_body: str) -> str:
    soup = BeautifulSoup(html_body, "lxml")
    for img in soup.find_all("img"):
        img.decompose()
    return str(soup.body or soup)


def message_to_epub(message: GmailMessage, out_dir: Path, resend: bool = False,
                    progress: ProgressFn = _noop) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = message.date[:10] if message.date else "0000-00-00"  # YYYY-MM-DD
    prefix = "[resend] " if resend else ""
    title = f"{prefix}{message.subject or 'Gmail Message'}"
    filename = f"{date_str} - {make_safe_filename(title, 'Gmail Message')}.epub"
    out_path = out_dir / filename

    css = _make_css()
    # No <h1> here: the article's own content already carries its title, so
    # repeating the Gmail subject line above it just puts the title twice.
    meta = (
        f"<div class='meta'>From: {html.escape(message.sender)}<br/>"
        f"Date: {html.escape(message.date)}<br/>"
        f"Gmail ID: {html.escape(message.message_id)}</div>"
    )

    def build(with_images: bool) -> epub.EpubBook:
        book = epub.EpubBook()
        book.set_identifier(f"gmail-{message.message_id}")
        book.set_title(title)
        book.set_language("en")
        book.add_author(message.sender or "Gmail")
        book.add_item(css)
        # Download and embed images so Amazon's converter doesn't choke on
        # external URLs. fetch_image drops decorative icons and downscales
        # large images, so the budget can be generous; we just keep the EPUB
        # under Gmail's send limit.
        soup = BeautifulSoup(message.html_body, "lxml")
        if with_images:
            _embed_images(book, soup, SINGLE_IMAGE_BUDGET)
        else:
            for img in soup.find_all("img"):
                img.decompose()
        chapter = epub.EpubHtml(title=message.subject or "Gmail Message", file_name="message.xhtml")
        chapter.content = (meta + str(soup.body or soup)).encode("utf-8")
        chapter.add_item(css)
        book.add_item(chapter)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.toc = [chapter]
        # nav.xhtml (a bare title + TOC-link page, no real content) is kept in
        # the manifest for EPUB3 validity but left out of the spine entirely -
        # Send-to-Kindle doesn't reliably honor linear="no", so it could still
        # surface as the book's opening page if left in the reading order.
        book.spine = [chapter]
        return book

    epub.write_epub(str(out_path), build(with_images=True))

    # if too large for Gmail API, rebuild without images
    if out_path.stat().st_size > EPUB_SIZE_CEILING:
        progress(f"EPUB too large ({out_path.stat().st_size // 1024}KB), rebuilding without images")
        epub.write_epub(str(out_path), build(with_images=False))

    return out_path


def messages_to_digest_epub(messages: list[GmailMessage], sender_name: str, week_start: str,
                            out_dir: Path, progress: ProgressFn = _noop) -> Path:
    """Create a digest EPUB from multiple messages with a table of contents."""
    out_dir.mkdir(parents=True, exist_ok=True)
    title = digest_title(sender_name, week_start)
    # The ISO date prefix keeps files chronologically sortable on disk; it's
    # not what's shown as the book title or the email subject, so it can't
    # produce the "date - name - date" duplication the visible title used to.
    filename = f"{week_start} - {make_safe_filename(title, 'Digest')}.epub"
    out_path = out_dir / filename

    def build(with_images: bool) -> epub.EpubBook:
        css = _make_css()
        book = epub.EpubBook()
        book.set_identifier(f"digest-{sender_name}-{week_start}")
        book.set_title(title)
        book.set_language("en")
        book.add_author(sender_name or "Digest")
        book.add_item(css)

        # Image budget shared across all articles. fetch_image drops decorative
        # icons and downscales large images, so a chart-heavy multi-article
        # digest still fits. Each image is checked against the *remaining*
        # budget rather than a sticky cutoff, so a chart-heavy early article
        # doesn't zero out every image in the articles that follow it.
        image_bytes_used = 0

        chapters = []
        toc_entries = []
        total_word_count = 0

        for msg_idx, message in enumerate(messages):
            soup = BeautifulSoup(message.html_body, "lxml")
            if with_images:
                image_bytes_used = _embed_images(
                    book, soup, DIGEST_IMAGE_BUDGET,
                    bytes_used=image_bytes_used,
                    uid_prefix=f"img{msg_idx}_",
                    idx_offset=msg_idx * 100,
                )
            else:
                for img in soup.find_all("img"):
                    img.decompose()
            body_html = str(soup.body or soup)

            # No <h2> here: the article's own content already carries its
            # title, so repeating the Gmail subject line above it just puts
            # it twice. The TOC entry (built from message.subject below) is
            # what readers use to navigate between articles in the digest.
            meta = (
                f"<div class='meta'>From: {html.escape(message.sender)}<br/>"
                f"Date: {html.escape(message.date[:10] if message.date else '-')}</div>"
            )
            chapter = epub.EpubHtml(
                title=message.subject or f"Article {msg_idx + 1}",
                file_name=f"article_{msg_idx:02d}.xhtml",
            )
            chapter.content = (meta + body_html).encode("utf-8")
            chapter.add_item(css)
            book.add_item(chapter)
            chapters.append(chapter)

            word_count = count_words(message.html_body)
            total_word_count += word_count
            toc_entries.append(
                f"<div class='toc-entry'>{msg_idx + 1}. "
                f"{html.escape(message.subject or 'Article')} ({word_count} words)</div>"
            )

        toc_html = (
            f"<h1>{html.escape(title)}</h1>"
            f"<div class='meta'>Week of {week_start} &#8226; {len(messages)} articles"
            f" &#8226; {total_word_count} total words</div>"
            f"<div class='toc'>{''.join(toc_entries)}</div>"
        )
        toc_chapter = epub.EpubHtml(title="Contents", file_name="toc.xhtml")
        toc_chapter.content = toc_html.encode("utf-8")
        toc_chapter.add_item(css)
        book.add_item(toc_chapter)

        book.toc = [toc_chapter] + chapters
        # nav.xhtml is kept in the manifest (EPUB3 validity) but left out of
        # the spine - see the comment in message_to_epub for why linear="no"
        # isn't reliable enough on its own.
        book.spine = [toc_chapter] + chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        return book

    epub.write_epub(str(out_path), build(with_images=True))

    if out_path.stat().st_size > EPUB_SIZE_CEILING:
        progress(f"Digest EPUB too large ({out_path.stat().st_size // 1024}KB), rebuilding without images")
        epub.write_epub(str(out_path), build(with_images=False))

    return out_path


def url_to_epub(title: str, html_body: str, url: str, out_dir: Path,
                image_items: list[tuple[str, str, bytes]] | None = None) -> Path:
    """Build an EPUB for a fetched web article. image_items are
    (in_book_path, media_type, data) tuples already downloaded by urlfetch."""
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{date_str} - {make_safe_filename(title, 'Article')}.epub"
    out_path = out_dir / filename

    css = _make_css()
    book = epub.EpubBook()
    book.set_identifier(url)
    book.set_title(title)
    book.set_language("en")
    book.add_item(css)

    for path, media_type, data in image_items or []:
        book.add_item(epub.EpubItem(
            uid=path.rsplit("/", 1)[-1].split(".")[0],
            file_name=path,
            media_type=media_type,
            content=data,
        ))

    header = (
        f"<h1>{html.escape(title)}</h1>"
        f"<p class='meta'>Source: <a href='{html.escape(url, quote=True)}'>{html.escape(url)}</a>"
        f" &#183; {date_str}</p>"
    )
    chapter = epub.EpubHtml(title=title, file_name="article.xhtml", lang="en")
    chapter.content = (header + html_body).encode("utf-8")
    chapter.add_item(css)
    book.add_item(chapter)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.toc = [chapter]
    # nav.xhtml is kept in the manifest (EPUB3 validity) but left out of the
    # spine - see the comment in message_to_epub for why linear="no" isn't
    # reliable enough on its own.
    book.spine = [chapter]

    epub.write_epub(str(out_path), book)

    if out_path.stat().st_size > EPUB_SIZE_CEILING:
        book2 = epub.EpubBook()
        book2.set_identifier(url)
        book2.set_title(title)
        book2.set_language("en")
        book2.add_item(css)
        chapter2 = epub.EpubHtml(title=title, file_name="article.xhtml", lang="en")
        chapter2.content = (header + _strip_all_images(html_body)).encode("utf-8")
        chapter2.add_item(css)
        book2.add_item(chapter2)
        book2.add_item(epub.EpubNcx())
        book2.add_item(epub.EpubNav())
        book2.toc = [chapter2]
        book2.spine = [chapter2]
        epub.write_epub(str(out_path), book2)

    return out_path
