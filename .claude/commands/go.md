---
model: sonnet
name: go
description: Switch to a project directory and load its full context. Use at the start of a session to pick up where you left off.
---
Switch to a project directory and load its full context. Use at the start of a session to pick up where you left off.

**Argument:** $ARGUMENTS (project name or alias)

## Project Directory Map

Real projects live directly under `/Users/cip/vibing/` (e.g. `/Users/cip/vibing/health`,
`/Users/cip/vibing/fin-advice`, `/Users/cip/vibing/AEOnow`). Most matching happens via the directory
scan in Step 2; this table is only for aliases that don't match a directory
name directly.

> Add rows here for short aliases you want beyond the directory name itself.

| Name / Alias | Directory |
|-------------|-----------|
| *(add your own short aliases here as you want them)* | |

## Steps

### 1. If no argument provided — interactive picker

**Step 1a:** Use `AskUserQuestion` with one question:

- Question: "Which project?"
- Options: your most recently active projects (check `ls -lt /Users/cip/vibing | head -6` or recent `SESSION_LOG.md` mtimes), plus an "Other" fallback
- (The automatic "Other" option lets the user type any project name.)

After both questions, treat the final selection (or typed answer) as `$ARGUMENTS` and continue to Step 2.

### 2. Match the argument to a project

**The argument may contain a project name followed by a task description** (e.g. `"eterauto can you check the label formatting"`). Extract the project name by trying progressively shorter prefixes until a match is found.

**Matching order — first match wins:**

1. **Alias table** — try the full argument, then each leading word/hyphen-token, against the Name/Alias column (case-insensitive)
2. **`/Users/cip/vibing/` scan** — run `ls /Users/cip/vibing/` and find any subdirectory whose name matches any leading token of the argument (case-insensitive, partial prefix OK if unambiguous).

When a match is found, note the matched project name and treat the **remaining argument text** (after the project name token) as the initial task context — carry it forward into the "What are we working on?" prompt.

If nothing matches after both checks, suggest the closest directory name and ask the user to confirm.

### 3. Change directory and load context in ONE step
Use Bash to `cd` into the directory AND extract the last session entry in a single command:
```bash
cd <dir> && tail -n 80 SESSION_LOG.md 2>/dev/null; echo "---EOF_SESSION---"
```
Then, in the SAME parallel call, read `CONTEXT.md` and `CLAUDE.md` using the Read tool (skip silently if missing).

**Do NOT:**
- Run Glob or ls to discover files
- Read SESSION_LOG.md with the Read tool (use the tail output above)
- Make sequential tool calls when parallel is possible

This means step 3 is exactly **one parallel batch**: one Bash + up to two Reads.

### 4. Print a summary
Keep it SHORT. No tables unless the last session had key metrics. Output:

```
## [Project Name]
**Directory:** [path]
**Last session:** [date from SESSION_LOG]
**Goal:** [goal from last handoff]
**Pending:** [pending items from last handoff]
**How to continue:** [continuation instructions from last handoff]
```

Then ask: "What are we working on?"
