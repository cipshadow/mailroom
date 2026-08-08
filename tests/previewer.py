"""Kindle Previewer 3 test harness: invocation + CSV log parsing.

Kindle Previewer is macOS/Windows-only, slow (a real conversion per book),
and not installable on GitHub-hosted Linux CI runners without extra work.
So this module splits cleanly in two:

  - The *parser* (parse_summary_log, parse_book_log, classify) is pure
    Python with no Previewer dependency. It's unit-tested on every OS
    against the real, scrubbed sample output committed in
    tests/fixtures/previewer/ - see PROVENANCE.md there for exactly how
    those samples were captured and why the format assumptions below are
    grounded in a real run rather than the CLI help text alone.
  - The *runner* (run_previewer) shells out to the real binary and is only
    exercised by tests marked `previewer`, which skip everywhere the binary
    isn't present.
"""

from __future__ import annotations

import csv
import io
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

PREVIEWER = shutil.which("kindlepreviewer")

# Amazon's own legend (see the first two lines of every per-book log) only
# documents Error and Notice; Warning is mentioned in Amazon's docs but was
# never observed. Only Error is build-blocking - that's Amazon's own
# definition, not a threshold we invented.
_BLOCKING_TYPES = {"Error"}

_CODE_RE = re.compile(r"^([A-Z]\d{3,5}):\s*")


@dataclass(frozen=True)
class Finding:
    book: str
    type: str  # "Error", "Notice", or whatever Previewer emits
    code: str | None  # e.g. "W14016", or None if the description has no code prefix
    description: str
    source_file: str = ""
    line_number: str = ""

    @property
    def blocking(self) -> bool:
        return self.type in _BLOCKING_TYPES


@dataclass(frozen=True)
class SummaryRow:
    book: str
    conversion_status: str
    error_count: int
    quality_issue_count: int
    log_path: str
    quality_report_path: str


def run_previewer(input_dir: Path, output_dir: Path, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run Previewer once over every book in input_dir (folder-batch mode).

    Batching matters: each invocation pays a fixed JVM/app startup cost, so
    running Previewer once per fixture instead of once for the whole corpus
    is the difference between ~20s and several minutes.
    """
    if PREVIEWER is None:
        raise RuntimeError("kindlepreviewer not found on PATH")
    output_dir.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [PREVIEWER, str(input_dir), "-log", "-qualitychecks", "-output", str(output_dir)],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def parse_summary_log(csv_path: Path) -> dict[str, SummaryRow]:
    """Parse Summary_Log.csv into {book_name: SummaryRow}."""
    text = csv_path.read_text(encoding="utf-8-sig")
    rows: dict[str, SummaryRow] = {}
    for row in csv.DictReader(io.StringIO(text)):
        name = row["Book Name"]
        rows[name] = SummaryRow(
            book=name,
            conversion_status=row["Conversion Status"],
            error_count=int(row["Error Count"]),
            quality_issue_count=int(row["Quality Issue Count"]),
            log_path=row["Log File Path"],
            quality_report_path=row["Quality Report Path"],
        )
    return rows


def parse_book_log(csv_path: Path, book: str) -> list[Finding]:
    """Parse a single <book>_log.csv.

    The first two lines are a human-readable legend, not data - real
    columns start at line 3 (see PROVENANCE.md). Tolerate either 2 or 3
    legend-ish leading lines by finding the header row (starts with "Type")
    rather than hardcoding a skip count, since a Previewer update could
    plausibly add a third legend line for "Warning" without changing
    anything else.
    """
    raw_lines = csv_path.read_text(encoding="utf-8-sig").splitlines(keepends=True)
    header_idx = next((i for i, line in enumerate(raw_lines) if line.startswith('"Type"')), None)
    if header_idx is None:
        raise ValueError(f"{csv_path}: no 'Type' header row found - Previewer log format may have changed")

    findings = []
    for row in csv.DictReader(io.StringIO("".join(raw_lines[header_idx:]))):
        description = row["Description"]
        code_match = _CODE_RE.match(description)
        findings.append(
            Finding(
                book=book,
                type=row["Type"],
                code=code_match.group(1) if code_match else None,
                description=description,
                source_file=row.get("Source File", ""),
                line_number=row.get("Line Number", ""),
            )
        )
    return findings


def parse_quality_report(csv_path: Path, book: str) -> list[Finding]:
    """Parse a single <book>_QualityReport.csv.

    Confirmed real format (see PROVENANCE.md): a legend line, then a
    "Type","Category","Description","Location","Recommended Fix" header,
    then data rows. Quality-check issues are advisory (Summary_Log.csv's
    separate "Error Count" column is what actually blocks a build), so
    every row here is Notice-severity regardless of its own Type column;
    the row's Category becomes the code, since that's the stable
    identifier ("InvalidExternalLinkKey" etc) - the Type column's observed
    values look like unresolved i18n keys, not something to key off of.

    Running with no internet access (the case in this repo's sandbox and
    likely most CI) makes every external link unresolvable, so
    InvalidExternalLinkKey rows are expected noise, not real defects -
    baseline.json tracks that explicitly rather than suppressing it silently.
    """
    text = csv_path.read_text(encoding="utf-8-sig")
    if not text.strip() or "no issues found" in text.lower():
        return []
    lines = text.splitlines(keepends=True)
    header_idx = next((i for i, line in enumerate(lines) if line.startswith('"Type"')), None)
    if header_idx is None:
        # Unrecognized non-empty format: surface it rather than dropping it,
        # so a real Previewer format change is visible instead of silently
        # swallowed the way the naive line-splitting used to do.
        return [Finding(book=book, type="Notice", code="QC-UNPARSED", description=text.strip()[:300])]

    findings = []
    for row in csv.DictReader(io.StringIO("".join(lines[header_idx:]))):
        findings.append(
            Finding(
                book=book,
                type="Notice",
                code=row.get("Category") or "QC-UNKNOWN-CATEGORY",
                description=row.get("Description", ""),
                source_file="",
                line_number=row.get("Location", ""),
            )
        )
    return findings


def parse_run(output_dir: Path) -> dict[str, list[Finding]]:
    """Parse a full Previewer output directory into {book_name: findings}.

    Cross-checks Summary_Log.csv's own error_count against the counted
    blocking findings per book - Summary_Log.csv is what a real KDP publish
    gates on, so a mismatch means this parser's assumptions are wrong, not
    that the book is fine.
    """
    summary_path = output_dir / "Summary_Log.csv"
    if not summary_path.exists():
        raise FileNotFoundError(f"no Summary_Log.csv in {output_dir} - Previewer may not have run")
    summary = parse_summary_log(summary_path)

    results: dict[str, list[Finding]] = {}
    for book, row in summary.items():
        findings = []
        log_path = Path(row.log_path)
        if log_path.exists():
            findings.extend(parse_book_log(log_path, book))
        else:
            findings.append(Finding(book=book, type="Error", code=None, description=f"missing log file: {log_path}"))

        report_path = Path(row.quality_report_path)
        if report_path.exists():
            findings.extend(parse_quality_report(report_path, book))

        counted_errors = sum(1 for f in findings if f.blocking)
        if counted_errors != row.error_count:
            findings.append(
                Finding(
                    book=book,
                    type="Error",
                    code=None,
                    description=(
                        f"harness mismatch: Summary_Log reports {row.error_count} error(s) "
                        f"but the parsed log contains {counted_errors} - Previewer's log format "
                        "may have changed; do not trust this result until investigated"
                    ),
                )
            )
        results[book] = findings
    return results


def load_baseline(path: Path) -> dict[str, int]:
    import json

    if not path.exists():
        return {}
    return json.loads(path.read_text())


def new_warning_codes(findings: list[Finding], baseline: dict[str, int]) -> set[str]:
    """Non-blocking findings whose code never appeared in the baseline.

    This is the regression gate for cosmetic/warning-level output: it lets
    pre-existing Notices (e.g. "cover not specified", tracked until Phase E
    ships cover generation) pass silently while still catching a genuinely
    new class of complaint.
    """
    seen = {f.code or f.description for f in findings if not f.blocking}
    return seen - set(baseline)
