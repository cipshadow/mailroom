# Fixture corpus provenance

Three tiers, per the test-harness design in the project plan. All committed
fixtures are **originally authored for this repo** — none are copied,
scraped, or adapted from any real publication's actual content. See "Why no
scraped Tier 2" below for why the original plan (fetch real public
newsletter HTML, scrub, truncate, commit) was dropped in favor of this.

## Tier 1 — synthetic hazard fixtures (`tests/fixtures/*.html`, committed)

Each file isolates one formatting hazard in `sanitize_html` /
`epub_build.py`:

| File | Hazard |
|---|---|
| `newsletter.html` | Baseline: MSO conditionals, layout table, tracking pixel, script, empty div |
| `empty_blocks.html` | E999 root cause: empty block elements that ebooklib serializes as self-closing tags |
| `nested_tables.html` | Six-level-deep layout tables (Mailchimp/older-ESP pattern) |
| `data_table.html` | A genuine data table (`<th scope>`) that must survive unwrapping — the negative case for the layout-table detector |
| `cid_inline.html` | Gmail inline-attachment images referenced as `cid:` URLs |
| `data_uri_image.html` | Base64 `data:` URI images (common in Ghost/Ghost-based newsletters) |
| `rtl_arabic.html` | `lang="ar" dir="rtl"` — exercises language detection and non-Latin/RTL rendering |
| `small_icons.html` | Small images with and without declared size/alt text — the `ICON_MAX_PX` threshold |
| `substack_style.html` | Nested `<center>` wrapper pattern typical of Substack-family ESPs |
| `mailchimp_style.html` | `role="presentation"` table-per-block pattern typical of Mailchimp campaigns |

Every one of these is fabricated text written to *look like* the markup a
real sender in that category would produce — the prose itself has no
publication of origin.

## Tier 2 — real-world newsletter HTML

**Not built.** The original design fetched the public web-view of real
Substack/Ghost/Beehiiv/Mailchimp posts, scrubbed identifying data, truncated
to ~2 paragraphs, and committed the result as a fixture. On review that
still means shipping excerpts of other people's copyrighted newsletter
prose in this repo indefinitely, which isn't something to do even trimmed
and scrubbed. Tier 1 was expanded instead (`substack_style.html`,
`mailchimp_style.html`) to cover the same *markup* patterns — the actual
target of these tests — without reproducing anyone's actual writing.

If real-world coverage beyond Tier 1 turns out to be necessary, the
Tier-3 mechanism below is the right place for it: point
`KINDLE_MAILROOM_PREVIEWER_CORPUS` at real EPUBs on your own machine.
Nothing under that path is ever committed.

## Tier 3 — local-only regression corpus (never committed)

Set `KINDLE_MAILROOM_PREVIEWER_CORPUS` to a directory of real, already-built
`.epub` files (for example `../../gmail_epubs/` in this monorepo, ~130 real
newsletter EPUBs from personal use) and the Kindle Previewer suite will
additionally validate every file in it. Unset (the default), this tier is
skipped entirely — CI never sees it, and no personal reading material
enters git history.

```bash
export KINDLE_MAILROOM_PREVIEWER_CORPUS="$(cd ../.. && pwd)/gmail_epubs"
pytest -q -m previewer
```
