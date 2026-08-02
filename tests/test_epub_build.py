import io
import zipfile
from pathlib import Path

from kindle_mailroom.core import epub_build
from kindle_mailroom.core.epub_build import (
    make_safe_filename,
    message_to_epub,
    messages_to_digest_epub,
    url_to_epub,
)
from kindle_mailroom.core.models import GmailMessage
from kindle_mailroom.core.sanitize import sanitize_html

FIXTURE = (Path(__file__).parent / "fixtures" / "newsletter.html").read_text()


def make_message(msg_id="m1", subject="The Big Idea"):
    return GmailMessage(
        message_id=msg_id,
        thread_id="t1",
        subject=subject,
        sender="Writer <writer@newsletter.com>",
        date="2026-07-10T08:00:00+00:00",
        html_body=sanitize_html(FIXTURE),
    )


def read_epub(path: Path) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(path.read_bytes()))


def test_make_safe_filename():
    assert make_safe_filename("Hello: The/Sequel?", "x") == "Hello TheSequel"
    assert make_safe_filename("   ", "fallback") == "fallback"
    assert len(make_safe_filename("a" * 300, "x")) <= 90


def test_message_to_epub_valid_zip_with_embedded_image(tmp_path, fake_image):
    path = message_to_epub(make_message(), tmp_path)
    assert path.exists() and path.suffix == ".epub"
    zf = read_epub(path)
    names = zf.namelist()
    assert "mimetype" in names
    assert any(n.endswith("message.xhtml") for n in names)
    assert any("images/" in n for n in names)  # chart embedded
    content = zf.read([n for n in names if n.endswith("message.xhtml")][0]).decode()
    assert "The Big Idea" in content
    assert "cdn.example.com" not in content  # src rewritten to in-book path


def test_image_budget_drops_trailing_images(tmp_path, monkeypatch):
    big = b"x" * (4 * 1024 * 1024)  # 4MB fake images: second one busts the 6MB budget

    def fake_fetch(url, idx, declared_width=None, declared_height=None):
        return f"images/img{idx:03d}.jpg", "image/jpeg", big, 300, 200

    monkeypatch.setattr(epub_build, "fetch_image", fake_fetch)
    html_body = (
        "<body><p>" + "word " * 300 + "</p>"
        "<img src='https://x/1.jpg'/><img src='https://x/2.jpg'/><img src='https://x/3.jpg'/></body>"
    )
    msg = make_message()
    msg.html_body = html_body
    path = message_to_epub(msg, tmp_path)
    zf = read_epub(path)
    embedded = [n for n in zf.namelist() if "images/" in n]
    assert len(embedded) == 1  # only the first fits the budget


def test_image_budget_is_not_sticky(tmp_path, monkeypatch):
    # Regression guard: a big image that busts the budget must not zero out
    # every image after it - a later, smaller image should still embed if it
    # fits in whatever room is left. This is what a long, chart-heavy article
    # (e.g. Uncharted Territories) relies on to keep images past the midpoint.
    # SINGLE_IMAGE_BUDGET is 6 * 1024 * 1024 = 6,291,456 bytes.
    sizes = {"1": 6_000_000, "2": 400_000, "3": 100_000}

    def fake_fetch(url, idx, declared_width=None, declared_height=None):
        name = url.rsplit("/", 1)[-1].split(".")[0]
        return f"images/img{idx:03d}.jpg", "image/jpeg", b"x" * sizes[name], 300, 200

    monkeypatch.setattr(epub_build, "fetch_image", fake_fetch)
    msg = make_message()
    msg.html_body = (
        "<body><p>" + "word " * 300 + "</p>"
        "<img src='https://x/1.jpg'/><img src='https://x/2.jpg'/><img src='https://x/3.jpg'/></body>"
    )
    path = message_to_epub(msg, tmp_path)
    zf = read_epub(path)
    embedded = [n for n in zf.namelist() if "images/" in n]
    # image 1 fits (6.0MB), image 2 busts the budget (6.4MB total) and is
    # dropped, image 3 fits in the remaining room (6.1MB total) and embeds
    assert len(embedded) == 2


def test_oversized_epub_rebuilt_without_images(tmp_path, monkeypatch):
    # Incompressible 5MB images: two would fit the 6MB image budget? No — one
    # fits, two exceed. Use 3.5MB so two fit the budget but the EPUB tops 8MB.
    import os

    blob = os.urandom(3 * 1024 * 1024 + 512 * 1024)

    def fake_fetch(url, idx, declared_width=None, declared_height=None):
        return f"images/img{idx:03d}.jpg", "image/jpeg", blob, 900, 600

    monkeypatch.setattr(epub_build, "fetch_image", fake_fetch)
    monkeypatch.setattr(epub_build, "EPUB_SIZE_CEILING", 1024 * 1024)  # force the rebuild path
    msg = make_message()
    msg.html_body = "<body><p>text</p><img src='https://x/1.jpg'/><img src='https://x/2.jpg'/></body>"
    path = message_to_epub(msg, tmp_path)
    zf = read_epub(path)
    assert not [n for n in zf.namelist() if "images/" in n]  # rebuilt image-free
    assert path.stat().st_size < 1024 * 1024


def test_digest_has_toc_and_all_articles(tmp_path, fake_image):
    messages = [make_message("a", "First Post"), make_message("b", "Second Post")]
    path = messages_to_digest_epub(messages, "Newsletter", "2026-07-06", tmp_path)
    zf = read_epub(path)
    names = zf.namelist()
    assert any(n.endswith("toc.xhtml") for n in names)
    assert any(n.endswith("article_00.xhtml") for n in names)
    assert any(n.endswith("article_01.xhtml") for n in names)
    toc = zf.read([n for n in names if n.endswith("toc.xhtml")][0]).decode()
    assert "First Post" in toc and "Second Post" in toc
    assert "2 articles" in toc
    assert "words" in toc


def test_nav_page_not_in_spine(tmp_path, fake_image):
    # Regression guard: nav.xhtml (a bare title + TOC-link page, no real
    # content) must not be in the reading order at all. linear="no" isn't
    # enough on its own - Send-to-Kindle doesn't reliably honor it - so nav
    # must be absent from the spine entirely (it stays in the manifest for
    # EPUB3 validity and is still reachable from Kindle's Go To menu).
    path = message_to_epub(make_message(), tmp_path)
    zf = read_epub(path)
    opf = [n for n in zf.namelist() if n.endswith(".opf")][0]
    content = zf.read(opf).decode()
    assert '<itemref idref="nav"' not in content


def test_digest_nav_page_not_in_spine(tmp_path, fake_image):
    messages = [make_message("a", "First Post"), make_message("b", "Second Post")]
    path = messages_to_digest_epub(messages, "Newsletter", "2026-07-06", tmp_path)
    zf = read_epub(path)
    opf = [n for n in zf.namelist() if n.endswith(".opf")][0]
    content = zf.read(opf).decode()
    assert '<itemref idref="nav"' not in content


def test_url_to_epub_nav_page_not_in_spine(tmp_path):
    path = url_to_epub("A Fine Article", "<p>body text</p>", "https://ex.com/post", tmp_path)
    zf = read_epub(path)
    opf = [n for n in zf.namelist() if n.endswith(".opf")][0]
    content = zf.read(opf).decode()
    assert '<itemref idref="nav"' not in content


def test_message_to_epub_no_duplicate_title(tmp_path, fake_image):
    # Regression guard: confirmed on a real device that the subject line was
    # being injected as an <h1> above content that already carries its own
    # title (and often subtitle/byline) - the title appeared twice on the
    # page. Count <h1>/<h2> tags rather than raw text: ebooklib writes the
    # chapter's `title=` into an invisible <head><title>, which isn't
    # visible reading content and would otherwise look like a duplicate.
    path = message_to_epub(make_message(), tmp_path)  # subject == fixture's own <h1>
    zf = read_epub(path)
    content = zf.read([n for n in zf.namelist() if n.endswith("message.xhtml")][0]).decode()
    assert content.count("<h1") == 1
    assert content.count("<h2") == 0


def test_digest_no_duplicate_title(tmp_path, fake_image):
    messages = [make_message("a", "The Big Idea")]  # subject == fixture's own <h1>
    path = messages_to_digest_epub(messages, "Newsletter", "2026-07-06", tmp_path)
    zf = read_epub(path)
    article = zf.read([n for n in zf.namelist() if n.endswith("article_00.xhtml")][0]).decode()
    assert article.count("<h1") == 1  # the article's own title
    assert article.count("<h2") == 0  # no injected chapter heading


def test_digest_articles_have_page_break_and_position_counter(tmp_path, fake_image):
    # Without an explicit break, several short articles back to back can
    # look like one continuous document once Kindle's converter has run
    # over the EPUB - the "page-break-before: always" on .chapter and the
    # end-of-article mark are both defensive against that.
    messages = [make_message("a", "First Post"), make_message("b", "Second Post"),
               make_message("c", "Third Post")]
    path = messages_to_digest_epub(messages, "Newsletter", "2026-07-06", tmp_path)
    zf = read_epub(path)
    names = zf.namelist()

    css_names = [n for n in names if n.endswith(".css")]
    css = zf.read(css_names[0]).decode()
    assert "page-break-before: always" in css
    assert ".chapter" in css

    for idx, position in enumerate(["1 of 3", "2 of 3", "3 of 3"]):
        article = zf.read([n for n in names if n.endswith(f"article_{idx:02d}.xhtml")][0]).decode()
        assert 'class="chapter"' in article
        assert f"Article {position}" in article
        assert "article-end" in article  # end-of-article mark present
        assert "∿" in article  # the sine-wave end mark itself


def test_embedded_image_gets_explicit_dimensions(tmp_path, fake_image):
    # Regression guard: Kindle's converter stretches an <img> with no
    # width/height to fill the column - the "magnified icon" bug. The
    # embedded image must carry its real pixel size.
    path = message_to_epub(make_message(), tmp_path)
    zf = read_epub(path)
    content = zf.read([n for n in zf.namelist() if n.endswith("message.xhtml")][0]).decode()
    assert 'width="200"' in content and 'height="100"' in content


def test_url_to_epub_includes_source_link(tmp_path):
    path = url_to_epub("A Fine Article", "<p>body text</p>", "https://ex.com/post", tmp_path,
                       image_items=[("images/abc.jpg", "image/jpeg", b"fakejpg")])
    zf = read_epub(path)
    names = zf.namelist()
    article = zf.read([n for n in names if n.endswith("article.xhtml")][0]).decode()
    assert "https://ex.com/post" in article
    assert "A Fine Article" in article
    assert any(n.endswith("images/abc.jpg") for n in names)
