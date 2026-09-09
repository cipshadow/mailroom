---
name: panel
description: Convene a panel of reviewers to analyze a draft from multiple perspectives, then synthesize their feedback into consensus findings, productive tensions, and prioritized recommendations.
user_invocable: true
model: sonnet
---

# Panel Review

Convene multiple reviewer agents to analyze a piece, then synthesize their perspectives into a unified analysis that surfaces consensus, tensions, and priorities.

## When to Use

- Before publishing something high-stakes
- When you want multiple perspectives without running reviewers manually
- When you suspect different aspects need different kinds of attention
- When you're too close to the work to know what feedback you need

## The Flow

### 1. Load Context

Read the draft. Understand:
- **piece_type** — essay, argument, explainer, narrative, etc.
- **audience** — general, specialist, insider
- **stage** — early draft, revision, near-final
- **goals** — if stated

### 2. Propose Panel

Based on piece context, propose 4-6 reviewers.

**Selection heuristics:**

| Signal | Suggests Including |
|--------|-------------------|
| Personal/reflective content | sedaris, mom |
| Argumentative content | asshole, vonnegut |
| Technical or jargon-heavy | mom, hemingway |
| Narrative structure | vonnegut, hitchcock, sorkin |
| Feels slow or wandering | sorkin |
| Feels bloated | hemingway |
| High-stakes / pre-publish | asshole, hemingway |
| General audience | mom |
| Early stage | vonnegut (fundamentals) |
| Late stage | hemingway, asshole (polish, stress-test) |

**Present the proposal:**

```
## Proposed Panel

**Draft:** [title or slug]
**Context:** [piece_type] for [audience], currently at [stage]

Based on this context, I recommend:

| Reviewer | Why |
|----------|-----|
| **[name]** | [One-line rationale tied to piece context] |

**Not including:**
- **[name]** — [Why not relevant for this piece]

Proceed with this panel, or adjust?
```

Wait for user confirmation or modification.

### 3. Run Reviewers

Once confirmed, run each reviewer using the appropriate skill (/asshole, /mom, /hemingway, /sedaris, /sorkin, /vonnegut, /hitchcock). Collect all outputs.

### 4. Synthesize

Analyze all reviewer outputs and produce a unified synthesis.

## Available Reviewers

| Reviewer | Focus |
|----------|-------|
| asshole | Logical rigor, unsupported claims |
| mom | Accessibility, jargon, general reader |
| hemingway | Economy, cutting, word-level |
| sedaris | Specificity, humor, voice |
| sorkin | Pacing, momentum, forward motion |
| vonnegut | Story fundamentals, structure |
| hitchcock | Tension, suspense, stakes |

## Default Panels by Piece Type

| piece_type | Default Panel |
|------------|---------------|
| essay / personal | mom, sedaris, vonnegut, sorkin |
| argument / opinion | asshole, vonnegut, hemingway, mom |
| explainer / technical | mom, hemingway, sorkin |
| narrative / story | vonnegut, hitchcock, sorkin, sedaris |
| newsletter | mom, sorkin, hemingway |

## Synthesis Output Format

```
## Panel Synthesis

**Panel:** [reviewer list]
**Piece context:** [type, audience, stage, goal]

---

### Consensus Findings

| Issue | Flagged By | Recommendation |
|-------|------------|----------------|

---

### Productive Tensions

**Tension: [description]**

> "[Quoted passage]"

| Cut it | Keep it |
|--------|---------|
| **[reviewer]:** [position] | **[reviewer]:** [position] |

**What's at stake:** [Framing for the writer to decide]

---

### Unique Insights

- **[reviewer]:** "[Insight only they surfaced]"

---

### Recommended Priorities

1. [Most important fix — flagged by multiple reviewers]
2. [Second priority]
3. [Third priority]

---

### The Hard Question

> [The single most important question the piece hasn't answered]
```
