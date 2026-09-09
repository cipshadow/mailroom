---
name: gdrive-scan
description: >
  Scan Google Drive recursively for files matching a given topic/subject.
  Pass topic as argument (e.g., "gdrive-scan medical", "gdrive-scan eterauto invoices").
  Returns comprehensive inventory of matches staged in `gdrive-inbox/` for review and filing.
  Requires Google Drive connector authenticated in session.
---

# Scan Google Drive for topic-specific files

Recursively walk your entire Google Drive, classify files against a given
topic, deduplicate against the repo, download matches, and stage them in
`gdrive-inbox/` for manual review and filing.

Read-only on Drive; nothing moved, deleted, or edited.

## 0. Load context
- `../../../CLAUDE.md` — standing rules.
- Check `../../active-context.md` for an open scan thread for this topic
  before starting a new one.
- If `gdrive-inbox/INVENTORY.md` exists, this is a **re-scan**: report only
  files not already listed there (by Drive file ID).

## 1. Enumerate — full recursive walk

**Keyword/full-text search alone is insufficient** — misses non-obvious
filenames, non-English terms, and unsearchable content (scanned images, third-party
mime types). Use true recursive walk:

1. List `parentId = 'root'` (paginate fully) to get every top-level folder
   and loose file.
2. For every folder, recurse: list children, paginate fully, recurse into
   every subfolder. Use depth-first or breadth-first, but **skip no folder
   without explicit logged reason**. Track visited folder IDs to avoid loops.
3. Separately walk `sharedWithMe = true`, paginating to the end.
4. **Supplementary cross-check:** run keyword sweeps (topic-specific terms,
   English + Romanian) as a backup—anything they surface that the walk
   didn't is a bug in the walk worth investigating.
5. **Parallel strategy:** if the tree is large, fan the walk across parallel
   subagents—one per top-level folder—each reporting verified findings only
   (paths, file IDs, titles, mimeType, size, modified date, viewUrl). Never
   report unverified structure.
6. **No silent exclusions:** every top-level folder is either walked or
   explicitly excluded with stated reason in the inventory (e.g. "excluded:
   pure media dump, zero topic hits on sampling"). Re-confirm prior
   exclusions with the owner rather than assuming they still apply.
7. **Bulk media handling:** for large photo/video dumps, enumerate the full
   folder listing (paginate completely) and report total count skipped. Flag
   individual images/videos for closer inspection only if filename, size, or
   neighbors suggest a relevant document or scan—same heuristic as Pass C
   below, just at appropriate scale.

## 2. Classify

- **Pass A — metadata only.** Judge from title + folder path + search
  snippet.
  - Obvious match (filename, folder structure, snippet clearly topic-relevant)
    → **accept**.
  - Obvious non-match (unrelated content, different project, off-topic
    mentions) → **reject** with one-line reason.
  - Ambiguous → Pass B.

- **Pass B — content inspection.** Use `read_file_content` on ambiguous
  PDFs/docs/spreadsheets and classify from actual text.

- **Pass C — suspicious images only.** Do **not** open every image. Flag as
  "suspicious" only if: it sits alongside other topic hits, filename matches
  known document patterns (e.g. scanned report, photo of printout), or
  size/aspect suggests document rather than snapshot. For flagged images,
  `read_file_content` (visual) to classify. Everything else in bulk photo
  dumps is listed unclassified and noted in the summary; don't silently drop
  the count. Videos: never opened; if the name/folder suggests topic
  relevance, list in inventory as "listed only, not downloaded" with the link.

- **Scale:** if the candidate list is large (dozens+), fan Pass A/B across
  parallel subagents in batches; each returns accept/reject/duplicate + reason.

## 3. Dedup against the repo
Before downloading, check whether the file is already in the repo—by filename
and rough size/content match against existing folders. Mark matches as
**duplicate — already in repo** in the inventory; don't re-download.

## 4. Download + report
- For each accepted, non-duplicate file: use `mcp__claude_ai_Google_Drive__download_file_content`
  (base64; for native Google types set `exportMimeType` to `application/pdf`
  or similar), decode, write into `gdrive-inbox/`, keeping the original
  filename. Organize by category if obvious (e.g. `contracts/`, `invoices/`,
  `notes/`); else `other/`.
- Skip download (list-only) for files over ~50 MB; note the Drive link so
  the owner can grab manually.
- Write/update `gdrive-inbox/INVENTORY.md`: one row per candidate—Drive
  title (linked), folder path, classification (accepted / rejected + reason /
  duplicate / listed-only + reason), why it matched, confidence, suggested
  destination. Tag AI classification judgments `[AI]`. Include summary: counts
  of accepted/downloaded, duplicate, rejected, listed-only, bulk folders
  skipped wholesale.

## 5. Privacy check
Before committing, scan newly downloaded files for sensitive data (full
addresses, account numbers, etc.). Flag findings in the inventory rather than
redacting silently.

## 6. Record the run
- **First run:** add a row to `active-context.md` (e.g. "Review `gdrive-inbox/`
  and file into the right place") and append a decision entry to
  `decisions.md`.
- **Re-scan with new hits:** update the inventory and note new count in
  `active-context.md`'s existing row.
- **Job done at staging:** filing (moving inbox files to final locations and
  updating living docs) is manual or a separate skill.
