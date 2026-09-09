---
name: dev-edit
description: Review a draft for big-picture issues—argument, structure, stakes, and payoff. Invoke with /dev-edit after drafting or with any draft the user provides.
user_invocable: true
model: sonnet
---

# Developmental Edit

## Purpose

Review a draft for big-picture issues: argument, structure, stakes, and payoff. Focus on whether the piece *works*, not whether the sentences are polished.

## What to Look For

Questions to consider (not all apply to every piece):

| Area | Questions |
|------|-----------|
| **Structure** | Does each section earn its place? Does the order make sense? |
| **Argument** | Is it logically clear and supported? Any holes? |
| **Evidence** | What backs each major claim? Personal experience? A linked study? A specific example? Where is the support thin or missing? |
| **Outsider read** | If a reader who doesn't know the writer picked this up cold, what would they push back on? |
| **Opening** | Does the hook work? Is the thesis clear? Is there a promise? |
| **Stakes** | Why should the reader care? Why does the writer care? |
| **Payoff** | Does the piece deliver on what it promises? |

**Use judgment.** A personal essay doesn't need argument scrutiny. A how-to doesn't need stakes analysis. Focus on what matters for this piece.

## The Structural Tests

### The Subsection Summary Test

For each subsection: write a one-sentence summary of what it argues. Then re-read the subsection. Anything not in service of that one sentence — cut it.

When invoked:
1. Identify each subsection (subhead-defined or paragraph-cluster).
2. Generate a one-sentence argument summary per subsection.
3. Flag paragraphs, examples, or asides that don't serve their subsection's summary.
4. Report the summaries alongside the flagged content so the writer can decide what stays.

### The 20-Second Pitch Test

If someone stopped the writer in a hallway, could they explain the piece in 20 seconds? Compare that pitch to the thesis/promise as stated in the intro.

When invoked:
1. Generate a 20-second pitch from the piece as written.
2. Pull the thesis/promise from the intro as stated.
3. Show both side by side. Flag the gap.

## Evidence Check

For each major claim, ask: what is this backed by?

| Support type | Verdict |
|--------------|---------|
| Personal experience the writer lived through | Strong — let it stand |
| A linked study, dataset, or named source | Strong — let it stand |
| An expert quote or named practitioner | Strong — let it stand |
| A specific named example (company, person, moment) | Strong — let it stand |
| "Studies show…" / "experts agree…" without specifics | Weak — flag |
| Only the writer's authority, when not established on this specific thing | Weak — flag |
| Nothing — assertion floats free | Weak — flag |

## Output Format

### Full Report (default)

```
## Developmental Edit Report

### Opening
🔴 **Critical:** [Issue]
[Why it matters]

🟡 **Consider:** [Issue]
[Explanation]

### [Section Name]
🟢 **Minor:** [Issue]
[Explanation]

---

Where would you like to start?
```

**Severity:**
- 🔴 Critical — Piece doesn't work without fixing
- 🟡 Consider — Would strengthen significantly
- 🟢 Minor — Nice to have

### Quick Assessment (for faster feedback)

```
## Quick Dev Edit

**Working well:** [2-3 things]

**Needs attention:**
1. [Main issue + why]
2. [Second issue + why]

**Overall:** [Ready for line edit / Needs another pass / Major restructure needed]
```

## Collaborative Fixing

After the report:
1. Writer picks where to start (or skip straight to line edit)
2. Offer fixes: "Here's how I'd address this—[fix]. Want me to make this change?"
3. Writer accepts, revises themselves, or skips
4. Repeat as needed

**Don't force resolution of every issue.** The writer decides what matters.
