"""Kindle Previewer harness tests.

Two layers, deliberately split by dependency:

- Parser unit tests run on every OS/CI job, always. They exercise
  tests/previewer.py's CSV parsing against the real, scrubbed sample output
  committed in tests/fixtures/previewer/ (see PROVENANCE.md there) - so the
  parsing logic is verified even though the binary that produced the sample
  can only run on macOS/Windows.
- The `previewer` marked tests actually shell out to kindlepreviewer and
  are skipped wherever it isn't installed. Run explicitly with
  `pytest -m previewer`.
"""

from __future__ import annotations

import platform
from pathlib import Path

import pytest
from previewer import (
    PREVIEWER,
    Finding,
    load_baseline,
    new_warning_codes,
    parse_book_log,
    parse_quality_report,
    parse_run,
    parse_summary_log,
    run_previewer,
)

from kindle_mailroom.core.epub_build import message_to_epub, messages_to_digest_epub, url_to_epub
from kindle_mailroom.core.models import GmailMessage
from kindle_mailroom.core.sanitize import sanitize_html

FIXTURES = Path(__file__).parent / "fixtures"
PREVIEWER_FIXTURES = FIXTURES / "previewer"
BASELINE_PATH = PREVIEWER_FIXTURES / "baseline.json"

def requires_previewer(func):
    """Combine the `previewer` marker (so `-m 'not previewer'`, the default
    addopts, deselects this test) with a skip condition (so an explicit
    `pytest -m previewer` still skips cleanly where the binary is absent)."""
    func = pytest.mark.previewer(func)
    func = pytest.mark.skipif(
        PREVIEWER is None or platform.system() not in ("Darwin", "Windows"),
        reason="Kindle Previewer 3 not installed, or not on macOS/Windows",
    )(func)
    return func

# ---------------------------------------------------------------------------
# Parser unit tests - no Previewer dependency, run everywhere.
# ---------------------------------------------------------------------------


def test_parse_summary_log():
    rows = parse_summary_log(PREVIEWER_FIXTURES / "sample_summary_log.csv")
    assert "Empty Blocks E999 Test" in rows
    row = rows["Empty Blocks E999 Test"]
    assert row.conversion_status == "Success"
    assert row.error_count == 0
    assert row.quality_issue_count == 1


def test_parse_book_log_skips_legend_lines():
    findings = parse_book_log(PREVIEWER_FIXTURES / "sample_book_log.csv", book="Empty Blocks E999 Test")
    assert len(findings) == 2
    assert all(f.type == "Notice" for f in findings)


def test_parse_book_log_extracts_codes():
    findings = parse_book_log(PREVIEWER_FIXTURES / "sample_book_log.csv", book="x")
    codes = {f.code for f in findings}
    assert codes == {"W14010", "W14016"}


def test_finding_blocking_property():
    error = Finding(book="b", type="Error", code="E999", description="boom")
    notice = Finding(book="b", type="Notice", code="W14016", description="fine")
    assert error.blocking
    assert not notice.blocking


def test_new_warning_codes_flags_unbaselined():
    baseline = {"W14016": 1}
    findings = [
        Finding(book="b", type="Notice", code="W14016", description="cover not specified"),
        Finding(book="b", type="Notice", code="W99999", description="a brand new complaint"),
    ]
    assert new_warning_codes(findings, baseline) == {"W99999"}


def test_new_warning_codes_ignores_baselined():
    baseline = {"W14016": 1}
    findings = [Finding(book="b", type="Notice", code="W14016", description="cover not specified")]
    assert new_warning_codes(findings, baseline) == set()


def test_load_baseline_missing_file_returns_empty(tmp_path):
    assert load_baseline(tmp_path / "does-not-exist.json") == {}


def test_current_baseline_file_loads():
    baseline = load_baseline(BASELINE_PATH)
    assert "W14016" in baseline


def test_parse_quality_report_extracts_category_as_code():
    findings = parse_quality_report(PREVIEWER_FIXTURES / "sample_quality_report.csv", book="x")
    assert len(findings) == 1
    assert findings[0].code == "InvalidExternalLinkKey"
    assert findings[0].type == "Notice"
    assert not findings[0].blocking


def test_parse_quality_report_no_issues_returns_empty(tmp_path):
    clean = tmp_path / "clean_QualityReport.csv"
    clean.write_text('"Quality checks completed. No issues found."')
    assert parse_quality_report(clean, book="x") == []


# ---------------------------------------------------------------------------
# Real Previewer integration - opt-in, macOS/Windows only.
# ---------------------------------------------------------------------------


def _fake_fetch_image(url, idx, declared_width=None, declared_height=None):
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (200, 100), (120, 40, 200)).save(buf, "JPEG")
    return f"images/img{idx:03d}.jpg", "image/jpeg", buf.getvalue(), 200, 100


def _make_message(fixture: str, subject: str, msg_id: str = "m1") -> GmailMessage:
    raw = (FIXTURES / fixture).read_text()
    return GmailMessage(
        message_id=msg_id,
        thread_id="t1",
        subject=subject,
        sender="Writer <writer@newsletter.com>",
        date="2026-07-10T08:00:00+00:00",
        html_body=sanitize_html(raw),
    )


ALL_FIXTURES = [
    ("newsletter.html", "The Big Idea"),
    ("empty_blocks.html", "The Empty Set"),
    ("nested_tables.html", "Six Levels Deep"),
    ("data_table.html", "Quarterly Numbers"),
    ("small_icons.html", "Icons and Small Diagrams"),
    ("substack_style.html", "On Writing Slowly"),
    ("mailchimp_style.html", "This Week in Review"),
    ("rtl_arabic.html", "RTL Test"),
]


@pytest.fixture(scope="session")
def previewer_corpus_dir(tmp_path_factory):
    """Build one EPUB per fixture (+ a digest + a URL article + a
    deliberately broken smoke-test book) into a single directory, so the
    real Previewer run is one batched invocation rather than N."""
    mp = pytest.MonkeyPatch()
    mp.setattr("kindle_mailroom.core.epub_build.fetch_image", _fake_fetch_image)
    mp.setattr("kindle_mailroom.core.urlfetch.fetch_image", _fake_fetch_image)

    corpus_dir = tmp_path_factory.mktemp("previewer_corpus")
    try:
        for fixture, subject in ALL_FIXTURES:
            message_to_epub(_make_message(fixture, subject), corpus_dir)

        messages = [
            _make_message("newsletter.html", "First Post", "a"),
            _make_message("data_table.html", "Second Post", "b"),
        ]
        messages_to_digest_epub(messages, "Newsletter", "2026-07-06", corpus_dir)

        url_to_epub(
            "A Fine Article", "<p>Body text for a URL-sourced article.</p>", "https://example.com/post", corpus_dir
        )

        # Deliberately broken book: an unsanitized self-closing-prone body
        # pushed straight through url_to_epub's raw path, to prove the
        # harness can detect a real failure rather than silently returning
        # a clean bill of health forever (see test_smoke_detects_a_problem).
        broken_html = "<div></div>" * 20 + "<p>mostly empty on purpose</p>"
        url_to_epub("Deliberately Broken Smoke Test", broken_html, "https://example.com/broken", corpus_dir)
    finally:
        mp.undo()

    return corpus_dir


@pytest.fixture(scope="session")
def previewer_results(previewer_corpus_dir, tmp_path_factory):
    output_dir = tmp_path_factory.mktemp("previewer_output")
    proc = run_previewer(previewer_corpus_dir, output_dir)
    assert proc.returncode == 0, (
        f"kindlepreviewer exited {proc.returncode}\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    return parse_run(output_dir)


@requires_previewer
def test_smoke_detects_a_problem(previewer_results):
    """Guards against a silently-empty parser: if this ever passes with zero
    findings anywhere, the harness itself is broken, not the books."""
    total_findings = sum(len(f) for f in previewer_results.values())
    assert total_findings > 0, "expected at least one finding across the corpus (e.g. missing-cover notices)"


@requires_previewer
def test_no_blocking_errors(previewer_results):
    blocking = {book: [f for f in findings if f.blocking] for book, findings in previewer_results.items()}
    blocking = {book: f for book, f in blocking.items() if f}
    assert not blocking, f"Previewer reported blocking errors: {blocking}"


@requires_previewer
def test_no_unbaselined_warning_codes(previewer_results):
    baseline = load_baseline(BASELINE_PATH)
    all_findings = [f for findings in previewer_results.values() for f in findings]
    new_codes = new_warning_codes(all_findings, baseline)
    assert not new_codes, (
        f"new warning code(s) not in baseline: {new_codes}. "
        f"If expected, add to {BASELINE_PATH} as a reviewed decision, not a rubber stamp."
    )
