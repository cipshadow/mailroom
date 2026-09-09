---
model: sonnet
name: context-refresh
description: Weekly maintenance pass for a hub-and-spoke context folder (CLAUDE.md + context-map.md + _inbox/ + INDEX.md pattern). Files _inbox/ drops, renames stray root files, dedupes, regenerates INDEX.md, flags stale/conflicting context.
argument-hint: <folder path(s), e.g. "~/vibing/health ~/vibing/fin-advice">
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent, AskUserQuestion
---

# Context Refresh: Hub-and-Spoke Maintenance Agent

Runs the recurring upkeep pass for a folder organized on the hub-and-spoke
context pattern: a slim `CLAUDE.md`, `.claude/context-map.md`, a drop zone at
root (files land there directly — `_inbox/` also works if the owner wants to
pre-sort), `INDEX.md` manifests in large data folders, and `DECISIONS.md` /
`CONTEXT.md` (or repo-specific equivalents like `active-context.md` /
`decisions.md`).

## Why this pattern, and why the two skills split the way they do

**The shape:** one small hub (`CLAUDE.md`, under ~85 lines) plus a routing
table (`context-map.md`) plus self-contained topic spokes. Root holds only
the entrypoints; everything else is a folder. `.claude/root-allowlist` is the
explicit exception list — genuine cross-cutting docs (a single
source-of-truth file that spans every topic, like a repo-wide `vaccines.md`)
that are allowed to sit at root permanently without being flagged as
clutter.

**Why root discipline matters more than it looks like it should:** a folder
can have every individual file perfectly named and still read as "random" —
that's a *listing*-level problem (too many things flat at once), not a
per-file naming problem, and no amount of renaming fixes it. See `/tidy`'s
"Root / Folder Consolidation" check for the detection logic; that check is
what actually solves it, here we just make sure it runs on a schedule and
gets pointed at this folder's specific conventions (core entrypoints,
`root-allowlist`, naming spec).

**Why this benefits a human:** the folder listing *is* the map. No memorized
structure needed — the name pattern and the topic folder tell you where
something lives, and `context-map.md` is a one-page fallback lookup.

**Why this benefits an agent even more:** context budget is the scarce
resource. `CLAUDE.md` loads every session; `context-map.md` routes a task to
1–3 files instead of the whole repo; `INDEX.md` lets an agent skip opening
files in a large data folder it doesn't need. A cluttered root forces an
agent to `ls` and guess, burning tokens and risking a missed file. Cost scales
with what a task actually touches, not with repo size.

**Why `/tidy` and `/context-refresh` don't duplicate each other:** `/tidy` owns
file-level judgment — is this name clear, is this a duplicate, does this
cluster of files belong in one folder. `/context-refresh` owns the
context-*system* upkeep that only makes sense for a hub-and-spoke folder
specifically — fixing cross-references that renames just broke, keeping
`context-map.md` and `INDEX.md` in sync with what's actually on disk,
flagging stale `CONTEXT.md` entries. It calls `/tidy`'s scan rather than
re-deriving it, so the file-judgment logic has exactly one home.

**Why it's self-healing rather than a one-time cleanup:** every rename or
move breaks some cross-reference somewhere. The link-repair pass (Phase 3
step 2) is what stops that from silently rotting the context map over time
as the folder keeps changing — and it has to be a complete, mechanical,
verified pass (see that step), not spot-fixes based on which renames happen
to be fresh in mind. Ad-hoc fixing is exactly how this broke before: a file
in one folder referenced a filename renamed hours earlier in an unrelated
batch, and nothing caught it until a human noticed the file still "looked
random."

**Target folder(s):** $ARGUMENTS (if not provided, ask the user; default to
`~/vibing/health` and `~/vibing/fin-advice` if the user says "the usual two").

Run each target folder independently; don't cross-reference between them
unless a finding explicitly spans both.

## Process

### Phase 1: Scan (read-only)

For each target folder, **run the full `/tidy` scan first** (naming issues,
duplicates, bloat, misplaced files, security, metadata gaps, root/folder
consolidation, size report — all 8 checks, `/tidy`'s own spec is canonical,
don't re-derive it here). Its "root/folder consolidation" check (#7) is what
catches files dropped straight into root without ever touching `_inbox/` —
that's the primary drop-zone pattern this owner actually uses, so treat any
loose non-entrypoint file at root exactly like an `_inbox/` item: read it,
determine what it is, propose a content-based name
(`YYYY-MM-DD-description.ext` for documents, `YYYY-MM-DD-what-it-shows.ext`
for images — check `.claude/naming-spec.md` if present) and a destination.

Then add these hub-and-spoke-specific checks on top of tidy's scan:

1. **`_inbox/` contents**, if the folder uses one. Same treatment as a root
   drop — read, name, file.
2. **Stale/conflicting cross-references.** Two separate things — don't
   conflate them:
   - **Broken links** (mechanical, fixed automatically in Phase 3 — see the
     algorithm there). Just note the count found here.
   - **Contradictory claims** — two docs asserting different facts about the
     same thing. This needs judgment, not a script. List for the report,
     don't resolve silently.
3. **INDEX.md freshness.** For each large data folder (identified by an
   existing `INDEX.md`/`INVENTORY.md`, or file count > ~15), check whether
   its file list matches what's on disk.
4. **CONTEXT.md / active-context.md staleness.** Check the "last updated"
   date against today; flag if stale past the folder's own staleness rule
   (usually >1 month, or check the file's own header).

### Phase 2: Propose

Present findings as a table grouped by category (same shape as `/tidy`):
`| # | Category | File | Finding | Proposed action |`. Include a duplicates
section listing exact-match pairs slated for auto-delete separately from
ambiguous ones needing a decision.

Ask: "Which actions should I apply? 'all', a list of numbers, or 'all except
N, N, N'." Skip this prompt only if the user invoked with an explicit
`--auto` flag in $ARGUMENTS.

### Phase 3: Execute

1. Apply the approved `/tidy` fixes (renames, dedup, root/folder
   consolidation moves, `_inbox/` filing) per `/tidy`'s own Phase 3. **As each
   move/rename happens, log it** (old-path → new-path, relative to the
   target folder root) into one running list. Don't skip this even for
   "obvious" renames — the list is what step 2 depends on, and an incomplete
   list is exactly how stale references survive a refresh pass.

2. **Fix every broken link in one pass, at the end, using the complete
   rename list from step 1 — not incrementally per-file, not by grepping for
   filenames you remember changing.** Grepping for specific old names is how
   this failed before: a file three folders away referenced an old filename
   from a rename made hours earlier, in a batch nobody thought to re-check.
   The reliable version is mechanical, not memory-based:
   - Enumerate every `.md` file in the target folder **including
     dot-directories** (`.claude/`, `.agents/`) — a plain shell glob
     (`**/*.md`) or `find` without `-not -path` exclusions silently skips
     these; use `find . -name '*.md'` or equivalent, which does not.
   - For every markdown link `[text](target)` in every file, resolve
     `target` relative to that file's own directory (decode `%20`-style
     escaping first; a directory target like `fertility/` is valid, not
     broken).
   - If it doesn't resolve: look up the target's filename in the rename
     list from step 1 first (handles renamed basenames, e.g. `x.md` →
     `topic/README.md`); if not there, search the actual current file tree
     for a unique file with that basename. If ambiguous or genuinely
     missing, leave it and add it to the flagged list — don't guess.
   - When you do have a resolution, **recompute the entire relative path
     from scratch** (from the referencing file's directory to the target's
     real current location) and replace the whole link target. Do not
     prepend `../` onto whatever was already there — a link that was already
     partially or incorrectly fixed compounds into `../../../nonsense` if
     you just keep adding prefixes instead of recalculating.
   - This is naturally a small script (a Bash one-liner won't cut it
     reliably) — write one, run it, don't hand-edit each occurrence.

3. **Verify, don't assume.** Re-run the same broken-link scan from step 2
   (detection only, no fixing) after the fixes land. It must report zero.
   If it doesn't, repeat step 2 rather than reporting success — a fix pass
   that still leaves broken links is not done.

4. Update `.claude/context-map.md`'s routing table and folder index for
   every file that moved or was newly created as a folder. Bump the "last
   verified" date. If a root-level file was deliberately kept (a genuine
   cross-cutting entrypoint, not filed anywhere), add it to
   `.claude/root-allowlist` so the SessionStart nudge stops flagging it — and
   just as importantly, **remove** an entry the moment that file stops
   living at root (moved into a topic folder), so the allowlist can't grow
   stale exceptions for files that no longer need one.
5. Regenerate `INDEX.md` in every folder where Phase 1 found drift.
6. Prune expired/resolved entries from `CONTEXT.md`/`active-context.md`
   (only entries the user confirms are resolved — don't guess).
7. Append a short entry to `SESSION_LOG.md` (or create one if absent):
   date, what was filed/renamed/deleted, what's still flagged.

### Phase 4: Report

Summarize: files filed, renamed, deleted (with reclaimed space), INDEX.md
files regenerated, stale references fixed, and — most importantly — anything
flagged but **not** resolved (conflicting docs, ambiguous duplicates, stale
CONTEXT.md entries needing a human call). This flagged list is the actual
point of running the skill regularly; don't bury it.

## Rules

Same conservatism as `/tidy`: propose before executing (except the explicit
mechanical/auto-delete cases above), read before renaming, never guess at
unidentifiable content (flag it, don't force a name), never touch a
self-governed subtree that has its own `CLAUDE.md` declaring itself
off-limits to reorganization, never print secret/sensitive values in the
report — describe generically instead.
