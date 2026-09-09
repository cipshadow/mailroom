---
description: End-of-session handoff. Runs a pre-flight checklist, writes a structured entry to the relevant SESSION_LOG, commits and pushes the session's work (opening or updating a PR when on a branch), then recaps what it covered and offers to compact.
model: sonnet
user-invocable: true
---

## Pre-Handoff Checklist

Run these checks silently. **Only report items that need action.** Omit any check that comes back clean.

**1. Temp files with useful content**
```bash
ls -t /private/tmp/claude-*/*/*/scratchpad/* 2>/dev/null | head -20
ls /tmp/*.md /tmp/*.txt 2>/dev/null
```
The scratchpad is the real location for this session's temp files; `/tmp` is a fallback for older habits. For anything found, check whether it holds session output worth keeping. If so, offer to save it to a permanent location.

**2. Open loops**
Review this session's conversation for any explicit "next steps", "TODO", "pending", or unresolved decisions. List them — they'll go into the Pending section of the log entry.

**Reporting rule:** If all checks are clean, say "Pre-flight clean." and move on. Do not list individual checks that passed. Only surface items requiring action.

---

## Step 1: Determine which SESSION_LOG(s) to update

Every real project directory under `/Users/cip/` owns its own `SESSION_LOG.md`
at its root (e.g. `Eterauto/SESSION_LOG.md`, `fin-advice/SESSION_LOG.md`,
`kindle-manager/SESSION_LOG.md`). This matches the SessionStart hook
(`~/.claude/hooks/session-log-reader.sh`), which walks up from `$PWD` looking
for the nearest `SESSION_LOG.md` — there is no cross-project catch-all file.

1. Walk up from the current working directory to find the nearest
   `SESSION_LOG.md`. If found, that's the log to update.
2. If none exists yet for this project, create one at the project root
   (the same directory as its `.git/`, or the directory you were invoked
   from if there's no repo) — see the format in Step 2 and use the same
   header pattern as any sibling project's `SESSION_LOG.md` for reference.

If the session spanned multiple project directories, update each one's own
log with only the content relevant to that project.

## Step 1b: Measure time spent

```bash
S=.claude/scripts/session-time.sh; [ -x "$S" ] || S=~/.claude/scripts/session-time.sh
"$S"
```

Reads timestamps straight from the session transcript. Reports wall clock, active
time (gaps over 15 min excluded as breaks), how many turns Cip typed, and an estimate
of reading time from assistant output length.

Use the measured numbers. Only fall back to estimating from turn count and output
length if the script is missing or fails, and say so explicitly when you do.

If the session resumed an earlier transcript, or spanned several, note that the
figure covers only the current one.

## Step 2: Write the handoff entry

Append to the bottom of each relevant SESSION_LOG using this format:

```markdown
### YYYY-MM-DD — [Short title summarizing the session]

**Time:** [Xh Ym active / Xh Ym wall clock] — [N turns from Cip, ~N min reading]

**Goal:** [What this session set out to accomplish]

**What we did:**
- [Concrete actions taken, with links to artifacts created/modified]
- [Decisions made: state the decision, alternatives, and why]

**Key decisions & trade-offs:**
- [Decision]: [What we chose] over [alternatives]. **Why:** [reasoning]
- [Only include if non-obvious decisions were made this session]

**Pending:**
- [Unfinished work, open loops, blocked items — omit section entirely if clean]

**Files involved:**
- [Key files created or modified, with paths and links]

**How to continue:** [Specific instruction for a fresh Claude instance to pick up where we left off]
```

**Learnings extraction:** Before writing the entry, ask yourself: "What did we learn this session that's reusable?" If there's a pattern, technique, insight, or decision rationale that would help future sessions, include a `**Learned:**` section with 1-3 bullet points. If nothing novel was learned, skip the section. These are candidates for memory files or CLAUDE.md updates.

**Research hoarding:** If the session produced research, analysis, or exploration outputs, ensure they're saved to the relevant project folder (not just /tmp or conversation context). Research compounds; don't let it evaporate.

**Brevity rule:** Omit any section that would just say "None" or "N/A". If there are no key decisions, skip that section. If nothing is pending, skip Pending. The entry should be as short as it can be while remaining useful 3 months later.

**Exclusion rule:** Do NOT include /anti-sloppifier (AI-use self-audit) findings, feedback, or coaching observations in the session log. Those live separately in `~/.claude/diary.md`. The session log captures *work done*, not *how AI was used*.

**Overwrite rule:** If an entry for today's date already exists (matching `### YYYY-MM-DD`), replace it entirely rather than appending a duplicate.

**Newest-last:** Entries go at the bottom of the file.

## Step 2b: Update CONTEXT.md

If a CONTEXT.md exists in the project directory, update sections that changed. If none exists, skip.

## Step 3: Commit, push, and open a PR

Runs automatically after the log entry is written. No confirmation prompt.

**Skip entirely if:** not inside a git repo, or the affected repos have nothing
uncommitted and nothing unpushed.

**1. Scope to what this session actually touched**

List the files you created or modified this session, plus the SESSION_LOG and
CONTEXT updates. Map each to its repo root (`git -C <dir> rev-parse --show-toplevel`).
That set of repos is the whole scope.

- Usually one repo. Handle it and stop.
- If the session genuinely touched several, handle each one, in order, with only
  its own files.
- Never touch a repo the session did not modify. Do not sweep `~/vibing`, do not
  walk sibling directories, do not act on a repo just because it has a dirty tree.

Within each repo, stage only the specific paths from this session. Never `git add -A`.
Pre-existing uncommitted work you did not touch stays untouched: note it in the
Pending section of the log entry and report it at Step 4.

Before staging, scan the diff for secrets (API keys, tokens, `.env` contents, private
keys). If anything looks like a credential, stop the git flow for that repo, leave it
unstaged, and report it.

**2. Route by branch**

```bash
git branch --show-current
git rev-parse --abbrev-ref origin/HEAD   # strip the origin/ prefix
```

**On the default branch (master/main):** commit and push inline. No PR, no branch.

```bash
git commit -m "<summary>

<short body>

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git push
```

Do **not** delegate this case. `ce-commit-push-pr` refuses to commit on the default
branch and force-creates a feature branch instead, which is not what we want here.

**On any other branch:** delegate to the `ce-commit-push-pr` skill rather than
reimplementing commit/push/PR. Invoke it via the Skill tool
(`compound-engineering:ce-commit-push-pr`). It handles branch resolution, fork and
detached-HEAD edge cases, the existing-PR lookup, and `gh` failure modes more
carefully than a reimplementation would.

Hand it the session content so the PR body is a session log, per the global
"PR descriptions as session logs" rule. If a PR already exists, the new session
section is appended to the existing body rather than replacing it.

**PR body format:**
```markdown
## Session: YYYY-MM-DD — [Short title]

**Time:** [Xh Ym active / Xh Ym wall clock]

**What was done and why:** [reasoning and motivation, not just a diff summary]

**Links and evidence:** [deploy URLs, screenshots, sources checked, related issues/PRs — omit if none]

**What is left for next time:** [explicit pending/follow-up items — omit if none]

**What was learned:** [surprises, gotchas, decisions worth remembering — omit if none]

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

Reuse the SESSION_LOG entry's content rather than re-deriving it. The two tell the
same story; the PR body reorganizes it under these headings. The 🤖 line goes once at
the bottom, not per section.

**If the plugin skill is unavailable** (cloud session without the plugin installed),
fall back to doing it inline: `git push -u origin HEAD`, then `gh pr create` or
`gh pr edit` with the body above. Say that you fell back.

**If push or PR fails** (no remote, no `gh` auth, protected branch, diverged history),
report the exact error and the state things were left in. Do not retry with force.

## Step 4: Confirm

Tell Cip in 5 lines max:
- Which log(s) were updated
- Commit SHA, branch pushed, and PR URL (or "no PR — on master")
- Any files deliberately left uncommitted
- Any action items from pre-flight (or nothing if clean)
- One-line "how to continue"

## Step 5: Dispatch the anti-sloppifier subagent

Do **not** run `/anti-sloppifier` inline — it would load a 250-line skill plus the
whole audit into this context for output that belongs in a file. Delegate it.

Build the digest first (cheap, and it fails loudly if the transcript is missing):

```bash
S=.claude/scripts/session-digest.sh; [ -x "$S" ] || S=~/.claude/scripts/session-digest.sh
"$S" > /tmp/session-digest-$(date +%s).txt
```

Then spawn the `anti-sloppifier` subagent (`subagent_type: "anti-sloppifier"`,
`run_in_background: true`) with a prompt naming that digest path. It runs on sonnet,
reads the digest itself, writes `~/.claude/diary.md` and `~/.claude/diary-trends.md`,
and returns ~10 lines.

Do not wait for it. Continue to Step 6 immediately; its report arrives as a task
notification. Relay the returned block verbatim when it lands — the subagent's reply
is not shown to Cip automatically.

Nothing from the audit goes in the SESSION_LOG or the PR body.

## Step 6: Recap what /ho just did

Print this block verbatim, filled in. It is a reminder of everything the skill
covers, so Cip can see at a glance what was and was not handled:

```
/ho covered:
  ✓ Pre-flight — scratchpad, open loops        [clean | N item(s) flagged above]
  ✓ Time measured                              [Xh Ym active / Xh Ym wall]
  ✓ SESSION_LOG entry                          [path(s)]
  ✓ CONTEXT.md                                 [updated | none found]
  ✓ Commit                                     [sha | skipped: reason]
  ✓ Push                                       [branch | skipped: reason]
  ✓ Pull request                               [url | no PR — on master | skipped: reason]
  ✓ anti-sloppifier subagent                   [dispatched | skipped]
```

Use `✓` only for steps that actually ran; use `–` for skipped ones. Never mark
a step done that was skipped or that failed.

## Step 7: Offer to compact

/ho usually means a significant piece of work just closed, which is the natural
point to reclaim context. Ask:

> Compact the session? The handoff is written, so nothing above is needed to continue.

Cip runs `/compact` himself — you cannot invoke it. Do not run it, do not
suggest a substitute, and do not wait on the answer before finishing.

If the conversation is short or the session barely used context, skip this step
rather than asking reflexively.

## Step 8: Done

Session stays open. Cip closes manually.
