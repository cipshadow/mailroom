---
name: email-scan
description: >
  Scan a Google Takeout mbox email export — both attachments and email body
  text — and classify hits into topic folders (default: financial, health,
  personal-docs/ID). Pass topic(s) as argument to override, e.g.
  "email-scan financial health". Stages matches in `email-inbox/<category>/`
  for review and manual filing. Read-only on the mbox source; nothing in the
  export is moved or deleted.
---

# Scan an email export for topic-specific content

Walk a Google Takeout `.mbox` export, classify every attachment **and every
message body** against a set of target categories, deduplicate against the
destination repos, extract matches, and stage them in
`email-inbox/<category>/` for manual review and filing — same pattern as
`/gdrive-scan`, adapted for an email export as the source instead of Drive.

Read-only on the mbox file(s); nothing in the export is modified or deleted.

## 0. Load context
- `../../../CLAUDE.md` — standing rules.
- Default categories and their filing destinations (override via argument):
  - `financial` → destined for `fin-advice/`
  - `health` → destined for `health/`
  - `personal-docs` → passport/ID/driving licence scans, visa/immigration/
    residency docs, contracts & legal docs, certificates — no existing repo
    destination; stage for the owner to decide where these live.
- Confirm the mbox path with the owner if not given (Takeout exports land in
  `~/Downloads/Takeout/Mail/*.mbox`, one file per label or "All mail").
- Check `active-context.md` (financial/health repo) for an open scan thread
  before starting a new one.
- If `email-inbox/<category>/INVENTORY.md` exists for a category, this is a
  **re-scan**: report only messages not already listed there (by Message-ID).

## 1. Enumerate — full walk, script-driven

mbox files are large and not something to read into context directly. Use a
script (Python's `mailbox`/`email` stdlib, via Bash) to walk it:

1. Open the mbox with `mailbox.mbox()`, iterate every message — no sampling,
   no early stopping. Track a running count of messages seen.
2. For each message, pull: Message-ID, Date, From, To, Subject, plain-text
   body (prefer `text/plain`; fall back to stripped `text/html`), and walk
   MIME parts for attachments (`part.get_filename()` set).
3. Record two working indexes, not yet extracting content:
   - **Attachments**: filename, content-type, size, parent message metadata.
   - **Bodies**: Message-ID + metadata + a short snippet (first ~200 chars
     of plain-text body) for cheap Pass-A triage without holding full body
     text for every message in context at once.
4. If multiple mbox files exist (per-label export), walk each and tag which
   file/label each hit came from.
5. **No silent exclusions:** every mbox file present is either walked or
   explicitly excluded with a stated reason.
6. **Parallel strategy:** if enumeration is slow (100k+ messages), split the
   walk by byte-offset ranges or by mbox file across parallel subagents,
   each reporting a verified attachment + body-snippet index only.

## 2. Classify

Attachments and bodies are classified as two separate candidate streams
against the same category heuristics — a match on one doesn't imply a match
on the other (an attachment can be relevant with a boilerplate body, or vice
versa).

- **Pass A — metadata/snippet only.** Judge from subject + sender +
  attachment filename (for attachments) or subject + sender + body snippet
  (for bodies) against each category's heuristics:
  - `financial`: sender domains/keywords (bank, broker, payroll, tax
    authority, invoice/receipt senders), subject terms (statement, invoice,
    payslip, tax, P60/P45, mortgage, pension), filenames/snippets
    (statement, invoice, payslip, balance, transfer).
  - `health`: sender domains (clinic, hospital, NHS, insurer, lab),
    subject terms (results, referral, prescription, appointment, scan,
    blood test), filenames/snippets matching known result/report language
    (e.g. "your results are ready", dosage/medication mentions).
  - `personal-docs`: subject/sender terms (passport, visa, driving licence,
    certificate, contract, deed, embassy, immigration), filenames/snippets
    matching scan/ID patterns or confirmation language ("your visa has
    been approved", "certificate attached").
  - Obvious match → **accept** into that category. Obvious non-match →
    **reject** with one-line reason. Ambiguous → Pass B.
- **Pass B — content inspection.** For ambiguous attachments, extract the
  bytes and classify from actual content: PDFs/images via the Read tool once
  written to disk; office docs via extracted text first. For ambiguous
  bodies, pull the full plain-text body (not just the snippet) and classify
  from the complete text — do this per-candidate, not for the whole mailbox,
  to avoid loading irrelevant bodies into context.
- **Cross-category:** a single item (attachment or body) can match more than
  one category (rare) — file it in the best-fit category and note the
  runner-up in the inventory rather than duplicating the file.
- **Scale:** if either candidate list is large (dozens+), fan Pass A/B across
  parallel subagents in batches; each returns accept/reject/duplicate +
  category + reason.

## 3. Dedup against the repos
Before extracting, check whether the attachment or an equivalent record of
the body content is already present in the destination repo (`fin-advice/`,
`health/`, or elsewhere) — by filename/subject and rough size/content match.
Mark matches as **duplicate — already filed** in the inventory; don't
re-extract.

## 4. Extract + report
- For each accepted, non-duplicate **attachment**: decode the MIME part,
  write into `email-inbox/<category>/`, keeping the original filename
  (disambiguate collisions with the Message-ID or date suffix).
- For each accepted, non-duplicate **body**: write the plain-text body (plus
  Subject/From/Date header block) as a `.md` file into
  `email-inbox/<category>/bodies/`, named from the date + a slugified
  subject (e.g. `2026-03-14-blood-test-results.md`). Don't fabricate or
  summarize the content — write the body verbatim under the header block.
- Skip extraction (list-only) for attachments over ~50 MB; note the parent
  message's Subject/Date/From so the owner can locate it manually.
- Write/update `email-inbox/<category>/INVENTORY.md`: one row per
  candidate (attachment or body) — type (attachment/body), filename, parent
  email (subject, from, date, linked Message-ID), classification (accepted /
  rejected + reason / duplicate / listed-only + reason), why it matched,
  confidence, suggested destination path inside the target repo. Tag AI
  classification judgments `[AI]`. Include a summary: counts of
  accepted/extracted, duplicate, rejected, listed-only per category, split
  by attachment vs. body, plus total messages walked.

## 5. Privacy check
Before handing off, scan newly extracted files for sensitive data (full
account numbers, national ID numbers, full addresses) and flag findings in
the inventory rather than redacting silently — this is expected for
`personal-docs` and `financial`, so flag rather than treat as an error.

## 6. Record the run
- **First run:** add a row to the relevant `active-context.md` file(s) (e.g.
  "Review `email-inbox/financial/` and file into `fin-advice/`") for each
  category with hits, and append a decision entry to the relevant
  `decisions.md`.
- **Re-scan with new hits:** update the inventory and note the new count in
  `active-context.md`'s existing row.
- **Job done at staging:** filing (moving inbox files into `fin-advice/` and
  `health/` proper, and deciding a home for `personal-docs/`) is manual or a
  separate skill.
