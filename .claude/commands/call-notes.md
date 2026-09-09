---
model: sonnet
description: Turn a call transcript into structured notes. Paste transcript text, or omit to fetch from Zoom.
---

## Input handling

1. If the user pasted a file path, read that file directly.
2. If the user pasted transcript text, use that directly.
3. If no input was given, use Zoom MCP tools to list recent recordings, ask the user to pick one, then fetch its transcript.

## Processing

Extract structured notes from the transcript using this template:

```
# [Meeting Title] — [YYYY-MM-DD]

**Attendees:** [names mentioned or identified from speaker labels]
**Duration:** [estimated from timestamps, or state "unknown"]
**Projects:** [comma-separated list of related projects]

## Context
One sentence: why this meeting happened.

## Decisions made
- [Decision]: [rationale in ≤1 sentence]

## Action items
- [ ] [Owner]: [task] (by [date if mentioned])

## Key discussion points
For each substantive topic (max 5):
### [Topic]
- [2-3 bullets max per topic]
- [Note open questions or disagreements]

## Open questions
- [Unresolved items needing follow-up]
```

## Rules

- Skip pleasantries, small talk, logistics ("can you hear me", "let me share my screen")
- Attribute action items to specific people by name
- If a decision was contested, note dissent in one line
- Preserve exact numbers, dates, product names, commitments verbatim
- Keep output under 400 words for meetings ≤30 min, under 800 for longer
- Sentence case headings only
- No filler, no narration of your process

## Saving

All meeting notes live in one central place:

```
~/.claude/meetings/YYYY-MM-DD-slugified-title.md
```

Create the directory if it doesn't exist.

A meeting can relate to **multiple projects**. Auto-detect relevant projects
by matching the meeting content against real project directory names under
`/Users/cip/` (`ls /Users/cip/`, same approach as the `/go` skill — ignore
`/Users/cip/cip/`, a separate unrelated copy).

For **each matched project**, append a one-line reference to
`/Users/cip/<project>/MEETINGS.md`:

```
- [YYYY-MM-DD — Meeting Title](~/.claude/meetings/YYYY-MM-DD-slugified-title.md): one-line summary
```

Use the absolute `~/.claude/meetings/...` path in the link, not a relative
one — meetings and projects no longer share a common parent directory.
Create `MEETINGS.md` in the project folder if it doesn't exist.

## File format

Each meeting file contains BOTH the structured notes AND the raw transcript in a single file:

```
[Structured notes from template above]

## Transcript

[Full verbatim transcript — no editing, no summarizing, preserve all timestamps and speaker labels]
```

One file = summary at top, raw transcript at bottom.

## Output

1. Show the notes to the user for review.
2. State which projects were detected (no need to ask — auto-detect from content).
3. Save the combined file (notes + transcript) to `~/.claude/meetings/`.
4. Update each matched project's `MEETINGS.md`.
5. Confirm saved path and which `MEETINGS.md` files were updated.
