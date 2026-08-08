"""Golden-file snapshots plus structural invariants for generated EPUBs.

Golden tests (marked `golden`) catch *any* byte-level formatting change and
force a reviewed decision about whether it was intentional - see golden.py
for why canonicalize() renders to readable text instead of comparing raw
zip bytes.

Structural-invariant tests are not snapshots: they're fixed contracts that
should fail with a clear message (not a diff) whenever violated, independent
of what the golden files currently say. These are the automated form of the
things a human would visually check in Kindle Previewer, and they run on
every OS in CI (unlike the previewer suite).
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import pytest
from golden import assert_golden
from lxml import etree

from kindle_mailroom.core.epub_build import message_to_epub, messages_to_digest_epub, url_to_epub
from kindle_mailroom.core.models import GmailMessage
from kindle_mailroom.core.sanitize import sanitize_html

FIXTURES = Path(__file__).parent / "fixtures"


def make_message(
    msg_id="m1", subject="The Big Idea", fixture="newsletter.html", sender="Writer <writer@newsletter.com>"
):
    raw = (FIXTURES / fixture).read_text()
    return GmailMessage(
        message_id=msg_id,
        thread_id="t1",
        subject=subject,
        sender=sender,
        date="2026-07-10T08:00:00+00:00",
        html_body=sanitize_html(raw),
    )


def read_epub(path: Path) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(path.read_bytes()))


# ---------------------------------------------------------------------------
# Golden snapshots
# ---------------------------------------------------------------------------

GOLDEN_CASES = [
    ("message_newsletter", "newsletter.html", "The Big Idea"),
    ("message_empty_blocks", "empty_blocks.html", "The Empty Set"),
    ("message_nested_tables", "nested_tables.html", "Six Levels Deep"),
    ("message_data_table", "data_table.html", "Quarterly Numbers"),
    ("message_small_icons", "small_icons.html", "Icons and Small Diagrams"),
    ("message_substack_style", "substack_style.html", "On Writing Slowly"),
    ("message_mailchimp_style", "mailchimp_style.html", "This Week in Review"),
]


@pytest.mark.golden
@pytest.mark.parametrize("case_name,fixture,subject", GOLDEN_CASES)
def test_message_golden(tmp_path, fake_image, golden_update, case_name, fixture, subject):
    msg = make_message(fixture=fixture, subject=subject)
    path = message_to_epub(msg, tmp_path)
    assert_golden(path, case_name, update=golden_update)


@pytest.mark.golden
def test_digest_golden(tmp_path, fake_image, golden_update):
    messages = [
        make_message("a", "First Post", "newsletter.html"),
        make_message("b", "Second Post", "data_table.html"),
    ]
    path = messages_to_digest_epub(messages, "Newsletter", "2026-07-06", tmp_path)
    assert_golden(path, "digest_two_articles", update=golden_update)


@pytest.mark.golden
def test_url_article_golden(tmp_path, golden_update):
    path = url_to_epub(
        "A Fine Article",
        "<p>Body text for a URL-sourced article.</p>",
        "https://example.com/post",
        tmp_path,
    )
    assert_golden(path, "url_article", update=golden_update)


# ---------------------------------------------------------------------------
# Structural invariants (not snapshots - fixed contracts)
# ---------------------------------------------------------------------------

_NS = {
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def _opf(zf: zipfile.ZipFile) -> etree._Element:
    opf_name = next(n for n in zf.namelist() if n.endswith(".opf"))
    return etree.fromstring(zf.read(opf_name))


def _manifest_ids(opf: etree._Element) -> set[str]:
    return {item.get("id") for item in opf.findall(".//opf:manifest/opf:item", _NS)}


def _manifest_hrefs(opf: etree._Element) -> dict[str, str]:
    return {item.get("id"): item.get("href") for item in opf.findall(".//opf:manifest/opf:item", _NS)}


@pytest.fixture(params=["message", "digest", "url"])
def any_epub(request, tmp_path, fake_image):
    """Parametrized fixture so every structural invariant test below runs
    against all three EPUB builders without three copies of each test."""
    kind = request.param
    if kind == "message":
        path = message_to_epub(make_message(), tmp_path)
    elif kind == "digest":
        messages = [make_message("a", "First Post"), make_message("b", "Second Post", "data_table.html")]
        path = messages_to_digest_epub(messages, "Newsletter", "2026-07-06", tmp_path)
    else:
        path = url_to_epub("A Fine Article", "<p>Body text.</p>", "https://example.com/post", tmp_path)
    return kind, read_epub(path)


def test_no_self_closing_block_tags(any_epub):
    # The E999 root cause: ebooklib serialises an empty <div></div> as
    # <div/>, which Amazon's converter rejects outright.
    kind, zf = any_epub
    for name in zf.namelist():
        if not name.endswith((".xhtml", ".html")):
            continue
        content = zf.read(name).decode("utf-8", errors="replace")
        for tag in ("div", "p", "span", "li", "blockquote"):
            assert not re.search(rf"<{tag}(\s[^>]*)?/>", content), (
                f"[{kind}] self-closing <{tag}/> found in {name} - this is exactly "
                "the pattern that triggers Amazon's E999 error"
            )


def test_manifest_hrefs_resolve(any_epub):
    kind, zf = any_epub
    opf = _opf(zf)
    hrefs = _manifest_hrefs(opf)
    zip_names = set(zf.namelist())
    opf_name = next(n for n in zip_names if n.endswith(".opf"))
    opf_dir = opf_name.rsplit("/", 1)[0] if "/" in opf_name else ""
    for item_id, href in hrefs.items():
        full = f"{opf_dir}/{href}" if opf_dir else href
        assert full in zip_names, f"[{kind}] manifest item '{item_id}' href '{href}' does not resolve to a zip entry"


def test_all_hrefs_resolve_to_manifest_or_external(any_epub):
    kind, zf = any_epub
    opf = _opf(zf)
    hrefs = set(_manifest_hrefs(opf).values())
    for name in zf.namelist():
        if not name.endswith((".xhtml", ".html")):
            continue
        content = zf.read(name).decode("utf-8", errors="replace")
        tree = etree.fromstring(content.encode(), parser=etree.HTMLParser())
        for a in tree.findall(".//a[@href]"):
            href = a.get("href")
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            local = href.split("#")[0]
            assert local in hrefs or not local, (
                f"[{kind}] internal link '{href}' in {name} does not resolve to any manifest item"
            )


def test_language_and_creator_present(any_epub):
    kind, zf = any_epub
    opf = _opf(zf)
    lang = opf.find(".//opf:metadata/dc:language", _NS)
    assert lang is not None and lang.text, f"[{kind}] dc:language missing or empty"

    if kind == "url":
        # Known gap: url_to_epub never calls add_author (epub_build.py:277-281).
        # Tracked as a Phase E formatting-quality fix, not fixed here so the
        # harness lands with a documented contract rather than silently
        # weakening it. Remove this branch once url_to_epub sets an author.
        pytest.xfail("url_to_epub does not set dc:creator yet (Phase E)")

    creator = opf.find(".//opf:metadata/dc:creator", _NS)
    assert creator is not None and creator.text, f"[{kind}] dc:creator missing or empty"


def test_nav_not_in_spine(any_epub):
    # Already covered per-builder in test_epub_build.py; kept here too as a
    # cross-cutting invariant now that all three builders share one fixture.
    kind, zf = any_epub
    opf = _opf(zf)
    itemrefs = [ir.get("idref") for ir in opf.findall(".//opf:spine/opf:itemref", _NS)]
    assert "nav" not in itemrefs, f"[{kind}] nav.xhtml must not be in the spine"


def test_opf_is_well_formed_xml(any_epub):
    kind, zf = any_epub
    # _opf() already parses with etree.fromstring, which raises on malformed
    # XML - reaching this line at all is the assertion.
    _opf(zf)
