# Previewer log fixtures

`sample_summary_log.csv`, `sample_book_log.csv`, and `sample_quality_report.csv` are real output from
Kindle Previewer 3.106.0 (`kindlepreviewer -log -qualitychecks`), captured
2026-08-04 on macOS, run against a deliberately built test EPUB (the
`empty_blocks.html` fixture pushed through `url_to_epub`, which does not
yet call `sanitize_html` - see Phase E). Local temp paths were replaced
with `SCRUBBED_TMP_PATH`/`SCRUBBED_OUT_DIR` placeholders; the book name
`"2026-08-04 - Empty Blocks E999 Test"` was trimmed to
`"Empty Blocks E999 Test"`. No other content was altered.

These exist so `tests/previewer.py`'s CSV parser has a real-format target
to be unit-tested against on Linux CI, where Kindle Previewer itself can
never run (macOS/Windows only).

Observed format notes (informed the parser design):
- `-log` still produces a KPF file despite the CLI help text implying it
  wouldn't ("generate only the log files ... without generating a KPF").
- The per-book log's first two lines are a human-readable legend, not CSV
  header/data - the real header is line 3.
- The observed `Type` values are `Notice` and `Error`; `Warning` appears in
  Amazon's own documentation but wasn't observed directly. The parser does
  not hardcode an enum - only `Error` is treated as build-blocking, per the
  legend text itself, and everything else is baseline-tracked.
- `Summary_Log.csv`'s `Error Count` / `Quality Issue Count` columns are the
  authoritative pass/fail signal - they're what gates a real KDP
  publish, so the parser cross-checks them against counted rows in the
  per-book log rather than trusting either source alone.
- `sample_quality_report.csv` (from `-qualitychecks`, still beta per
  Amazon's own CLI help) is a *second* CSV with a different shape: a legend
  line, then a `Type,Category,Description,Location,Recommended Fix` header,
  then rows. The observed `Type` column value looks like an unresolved i18n
  key concatenation (`"CategoryNavigationKey"`), so the parser keys off
  `Category` (`"InvalidExternalLinkKey"`) instead, which reads as the
  intended stable identifier. `-qualitychecks` needs network access to
  validate external links; every run in this sandbox (and likely most CI)
  has none, so `InvalidExternalLinkKey` rows are expected noise from that,
  not real defects - see `baseline.json`.

## baseline.json

Non-blocking warning codes seen on a real, full-corpus `pytest -m previewer`
run (2026-08-04) and deliberately accepted rather than fixed:

- `W14016` ("Cover not specified") - every book, until Phase E ships
  `set_cover()`. Remove once that lands; a code disappearing from real
  output is harmless even if it lingers in the file.
- `W14001` / `W14002` (hyperlink not resolved) - from `mailchimp_style.html`,
  which contains a real-looking link that can't be validated offline.
- `InvalidExternalLinkKey` - the `-qualitychecks` beta external-link check,
  same root cause: no network access to the sandbox/CI runner.

If a *new* code appears beyond these four, treat it as a real signal worth
investigating before adding it here - that's the point of the gate.
