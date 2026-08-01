"""URL → Kindle mode.

The URL itself is user-supplied and trusted, but the page content at that URL
is third-party, so it has to clear the same attribute whitelist as Gmail mode
before it reaches the EPUB.
"""

from kindle_mailroom.core import urlfetch


class _FakePage:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def _fetch(monkeypatch, html):
    monkeypatch.setattr(urlfetch.requests, "get", lambda *a, **kw: _FakePage(html))
    return urlfetch.fetch_article("https://good.example/post")


def test_title_extracted_and_cleaned(monkeypatch):
    title, _ = _fetch(
        monkeypatch,
        "<html><head><title>Real Article - by Someone</title></head>"
        "<body><article><p>Body</p></article></body></html>",
    )
    assert title == "Real Article"


def test_active_markup_stripped_from_article(monkeypatch):
    _, body = _fetch(
        monkeypatch,
        """<html><head><title>T</title></head><body><article>
             <p onclick="steal()" data-track="x">Body text</p>
             <iframe src="https://evil.example/frame"></iframe>
             <a href="javascript:alert(1)">Click</a>
             <a href="https://good.example/more">More</a>
           </article></body></html>""",
    )
    assert "onclick" not in body
    assert "data-track" not in body
    assert "<iframe" not in body
    assert "javascript:" not in body
    # legitimate content and links survive
    assert "Body text" in body
    assert "https://good.example/more" in body


def test_lazy_image_survives_sanitization(monkeypatch):
    # sanitize_html keeps only src on <img>, so data-src has to be promoted
    # first or every lazy-loaded image silently disappears.
    _, body = _fetch(
        monkeypatch,
        '<html><head><title>T</title></head><body><article>'
        '<img data-src="https://cdn.example/lazy.png" width="800" height="400">'
        "</article></body></html>",
    )
    assert "lazy.png" in body


def test_missing_body_returns_placeholder(monkeypatch):
    _, body = _fetch(monkeypatch, "<html><head><title>T</title></head></html>")
    assert "No content extracted" in body
