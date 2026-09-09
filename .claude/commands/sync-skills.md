---
model: sonnet
name: sync-skills
description: Sync the global Claude Code skill set (~/.claude/commands, agents, scripts) into every repo under ~/vibing, committing and pushing so the same skills work in Claude Code web, not just locally.
argument-hint: (optional) a single repo name to sync just that one
allowed-tools: Read, Bash, Edit
---

# Sync Skills

Copy the global Claude Code setup into every repo under `~/vibing/`, then commit and push, so the shared skill set is available in Claude Code web (which has no access to the local `~/.claude` directory — see `~/.claude/commands-README.md` for why this exists).

Three directories travel, not just commands:

| From | To | Why |
| --- | --- | --- |
| `~/.claude/commands/*.md` | `.claude/commands/` | the slash commands themselves |
| `~/.claude/agents/*.md` | `.claude/agents/` | subagents the commands dispatch (e.g. `anti-sloppifier`, called by `/ho`) |
| `~/.claude/scripts/*.sh` | `.claude/scripts/` | helper scripts the commands shell out to (e.g. `session-digest.sh`, `session-time.sh`) |

A command synced without its agent or its scripts fails at runtime in exactly the environment this skill exists to support. Sync all three or none.

**Target:** $ARGUMENTS (if given, only sync that one repo under `~/vibing/`; otherwise all of them)

## Process

For each git repo under `~/vibing/` (skip anything without a `.git` directory):

1. **Copy the files.**
   ```
   mkdir -p .claude/commands .claude/agents .claude/scripts
   cp ~/.claude/commands/*.md .claude/commands/
   cp ~/.claude/agents/*.md   .claude/agents/   2>/dev/null || true
   cp ~/.claude/scripts/*.sh  .claude/scripts/  2>/dev/null || true
   chmod +x .claude/scripts/*.sh 2>/dev/null || true
   ```
   This only adds/updates the shared files — never touches any repo-unique commands, agents, or scripts already sitting in those folders (files that don't exist in the global set).

   Scripts must stay executable after the copy; a synced script without the exec bit fails silently at the call site.

2. **Check for a `.claude` gitignore block.** Run `git check-ignore -v .claude/commands/go.md`, and the same for `.claude/agents/` and `.claude/scripts/` — a rule can cover one and not the others. If any is ignored:
   - Read the `.gitignore` to see if the rule looks like generic scaffold noise (e.g. grouped with `.cache/`, `.tmp/`) rather than a deliberate choice to keep Claude config out of the repo.
   - If so, fix it to `.claude/*` plus `!.claude/commands/`, `!.claude/agents/`, and `!.claude/scripts/` (note: the negations alone do NOT work if the parent `.claude/` is fully excluded — must use `.claude/*` so git still traverses into the directory).
   - If the ignore looks deliberate (e.g. a comment says so, or it's the only entry and clearly intentional), stop and ask before changing it.

3. **Stage and check for real changes.**
   ```
   git add .claude/commands/ .claude/agents/ .claude/scripts/ [.gitignore if changed]
   git diff --cached --quiet && echo "no changes" # skip commit/push if true
   ```

4. **Commit** (only if there's a real diff):
   ```
   git commit -m "Sync shared Claude Code skills, agents, and scripts from ~/.claude

   Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
   ```

5. **Push.** Try `git push -q` first.
   - If rejected as behind remote (`fetch first` / `non-fast-forward`):
     - Check `git status --short` for pre-existing unstaged/uncommitted changes unrelated to this sync.
     - If present: `git stash push -- <those specific files>` (never `git stash -u` blindly — leave untracked junk alone), then `git pull --rebase --no-edit`, then `git stash pop`.
     - If none: just `git pull --rebase --no-edit`.
     - Push again.
   - **If the stash pop produces merge conflicts**, or the rebase itself conflicts: STOP. Do not resolve code conflicts by guessing — leave the stash intact (don't drop it), report which repo and which files conflict, and move on to the next repo. This is real work-in-progress content colliding with newer remote commits; only the user can judge which side to keep.

## Report

At the end, summarize in three groups: repos updated, repos with no changes needed, and repos that need manual attention (with the specific reason — gitignore judgment call, merge conflict, etc.). Don't silently skip a failure — always surface it.
