"""EPUB golden-file (snapshot) comparison helpers.

EPUBs are ZIPs, and ZIPs aren't byte-reproducible: ebooklib stamps
dcterms:modified with the current time, generates a UUID identifier when one
isn't supplied, and zip entry order/mtimes can vary. Naive byte comparison
fails on every run even with zero real changes.

canonicalize() renders an EPUB into a deterministic, human-readable text
blob instead: sorted zip listing, pretty-printed XHTML/OPF with sorted
attributes, volatile fields redacted, and binary content replaced by a
`<type WxH ~NKB>` stub. The point of readability is that a PR diff should
show *what* changed ("the digest TOC gained href attributes"), not just
"binary files differ" - a golden file nobody can read in a diff review is
just a tripwire, not a review tool.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from lxml import etree

GOLDEN_DIR = Path(__file__).parent / "golden"

# Fields that legitimately vary run to run and carry no formatting signal.
_VOLATILE_PATTERNS = [
    (re.compile(r'(<meta property="dcterms:modified">)[^<]*(</meta>)'), r"\1REDACTED\2"),
    (re.compile(r'(<dc:identifier[^>]*>)urn:uuid:[0-9a-f-]+(</dc:identifier>)'), r"\1REDACTED-UUID\2"),
    # url_to_epub stamps today's fetch date into visible article metadata
    # (epub_build.py's "Source: ... · YYYY-MM-DD" line) - redact any bare
    # ISO date so the golden file doesn't rot one day after it's recorded.
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "REDACTED-DATE"),
]

_TEXT_MEDIA_TYPES = {
    "application/xhtml+xml",
    "application/oebps-package+xml",
    "application/x-dtbncx+xml",
    "text/css",
}


def _pretty_xml(data: bytes) -> str:
    try:
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.fromstring(data, parser=parser)
    except etree.XMLSyntaxError:
        # Not XML (or malformed) - fall back to the raw decoded text so the
        # golden file still shows *something* diffable instead of raising.
        return data.decode("utf-8", errors="replace")
    for el in tree.iter():
        if el.attrib:
            sorted_items = sorted(el.attrib.items())
            el.attrib.clear()
            for k, v in sorted_items:
                el.set(k, v)
    return etree.tostring(tree, pretty_print=True, encoding="unicode")


def _stub_binary(name: str, data: bytes) -> str:
    size_kb = max(1, len(data) // 1024)
    ext = name.rsplit(".", 1)[-1] if "." in name else "bin"
    return f"<binary {ext} ~{size_kb}KB>"


def canonicalize(epub_path: Path) -> str:
    """Render an EPUB into a deterministic, reviewable text blob."""
    zf = zipfile.ZipFile(epub_path)
    lines: list[str] = []
    names = sorted(zf.namelist())
    lines.append("FILES:")
    for name in names:
        lines.append(f"  {name}")
    lines.append("")

    for name in names:
        data = zf.read(name)
        lines.append(f"=== {name} ===")
        if name.endswith((".xhtml", ".html", ".opf", ".ncx", ".css")) or name == "mimetype":
            if name.endswith((".xhtml", ".html", ".opf", ".ncx")):
                text = _pretty_xml(data)
            else:
                text = data.decode("utf-8", errors="replace")
            for pattern, repl in _VOLATILE_PATTERNS:
                text = pattern.sub(repl, text)
            lines.append(text.rstrip())
        else:
            lines.append(_stub_binary(name, data))
        lines.append("")

    return "\n".join(lines) + "\n"


def assert_golden(actual_epub: Path, case_name: str, update: bool = False) -> None:
    """Compare an EPUB against tests/golden/<case_name>.txt.

    With update=True (wired to `pytest --golden-update`), rewrite the
    golden file instead of asserting. CI never runs with --golden-update:
    checked-in goldens must always match, and regenerating them is a
    reviewed, deliberate step (see CONTRIBUTING.md), not a fix for a
    failing test.
    """
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    golden_path = GOLDEN_DIR / f"{case_name}.txt"
    actual = canonicalize(actual_epub)

    if update or not golden_path.exists():
        golden_path.write_text(actual)
        return

    expected = golden_path.read_text()
    if actual != expected:
        raise AssertionError(
            f"Golden mismatch for '{case_name}' ({golden_path}).\n"
            "If this change is intentional, review the diff carefully, then "
            "regenerate with: pytest --golden-update -k " + case_name
        )
