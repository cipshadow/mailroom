---
description: Extract user feedback into structured database, or query existing entries. Args: raw text, URL, or subcommand (search/themes/user/recent/stats).
argument-hint: <paste feedback, URL, or subcommand: search/themes/user/recent/stats>
user-invocable: true
---

# /fb — User Feedback Extraction & Storage

Extract user or customer feedback into a structured markdown database, or query existing entries.

## Storage

Single file: `feedback/FEEDBACK.md` (relative to your project root)

Format: Markdown table with columns:
```
| # | Date | Company | User | Area | Severity | Sentiment | Verbatim | Problem | Source |
```

If the feedback file doesn't exist on first use, ask: "Where should I save feedback?"

---

## Determine mode

Check the input ($ARGUMENTS):

- If it starts with `search `, `themes`, `user `, `recent`, or `stats` → **Query mode**
- If it's empty → **Prompt mode** (ask user to paste or reference a source)
- Otherwise → **Extract mode** (treat input as feedback source material)

---

## Extract mode

### Step 1: Fetch source if needed

- Slack URL → fetch the thread
- Google Doc URL/ID → fetch the doc
- Jira ticket ID → fetch the ticket
- Raw text → use directly

### Step 2: Extract and present for validation

For each feedback signal found:

```
Found [N] feedback signal(s):

**Entry [N]:**
- Company: [name]
- User: [person name/handle if known]
- Date: [when the feedback was originally given]
- Area: [product area — infer from content]
- Severity: [blocker | major | minor | nice-to-have]
- Sentiment: [positive | negative | neutral | mixed]
- Verbatim: "[exact quote if available]"
- Problem: [1-2 sentence PM interpretation of underlying need]
- Source: [permalink / doc link / "pasted text"]

Save this? (yes / edit / skip)
```

**Rules:**
- Preserve verbatim quotes exactly. Never clean grammar or rephrase.
- The `Problem` field is your interpretation of the underlying need.
- Multiple distinct points in one source = separate entries.
- No verbatim available → write `_no verbatim_`
- Never invent or embellish quotes.
- `Date` = when feedback was GIVEN, not today.

### Step 3: Save on approval

1. Read feedback file to find last entry number
2. Append new row with next sequential `#`
3. Confirm: "Saved as entry #[N]."

---

## Query mode

### `/fb search <term>`
Search across all columns. Present matching rows as a readable list.

### `/fb themes [area]`
Group by Area or Problem patterns. For each theme: count, sentiment breakdown, representative verbatim.

### `/fb user <name>`
Find all entries where Company or User matches. Present chronologically.

### `/fb recent [N]`
Show the N most recent entries (default 10) with Problem and Verbatim.

### `/fb stats`
Summary table: total entries, breakdown by area, severity, sentiment.

---

## Important

- One table, one file. All feedback lives in a single FEEDBACK.md.
- Never invent or embellish quotes.
- When in doubt about any field value, ask rather than guess.
- Ambiguous source → mark with `[?]` and note.
