---
name: guardrails
description: "Scan any draft for recurring editorial-review failures: clarity and evidence gaps, argument problems, mechanics red flags, and second-order AI tells. Reports findings with line-level diagnoses and suggested fixes."
user_invocable: true
model: sonnet
---

# Guardrails

## Overview

This skill scans drafts against patterns that recur in pre-publication review. Produces a findings report with flags, diagnoses, and suggested fixes — does **not** rewrite the whole draft.

## Detection categories

### Universal: apply to every draft

1. **Editorial clarity and evidence** — missing "why" or "so what," missing specifics, unidentified people/companies/terms, source and attribution gaps, jargon without translation, muddy connective logic.
2. **Argument-level guardrails** — straw men, false binaries, technical intimidation, false universality.
3. **Mechanics-level guardrails** — hedges, correlative constructions, rhetorical questions as filler, meandering intros, sentimental conclusions, metaphors without payoff, unexplained technical terms.
4. **AI tells beyond the standard lexicon** — aphoristic balance closes, "I don't mean X. I mean Y" redirects, pseudo-Q&A bridges, and reader-projection "Maybe" anaphora.

## Editorial Clarity And Evidence Checks

Run these first on every draft:

- Translate AI-flavored or branded-sounding phrasing into plain English.
- Add the reason when a recommendation or claim leaves the reader asking why it is important.
- Give abstract concepts a concrete example and numbers a meaningful comparison.
- Identify people, companies, acronyms, and specialist terms on first mention.
- Attribute factual claims, statistics, trend statements, and quotes. If no source exists, narrow or cut the claim.
- Define necessary jargon on first use or replace it with plain language.
- State the connection between grouped examples explicitly or cut the grouping.

## Scan workflow

### Step 1: Scan in priority order

1. Editorial clarity and evidence pass
2. Argument-level pass
3. Correlatives pass
4. Hedge pass
5. Rhetorical-question pass
6. Closing pass

### Step 2: Log each finding

For every flag, record:

- **Pattern name**
- **Location** (paragraph number or distinctive opening words)
- **Offending line** (verbatim quote)
- **Diagnosis** (one sentence on why it trips the rule)
- **Suggested fix** (specific rewrite or directional cut)

## Output format

```
# Guardrails scan: [essay title or filename]

## Tier 1 — High priority

These hit the highest-severity rules: editorial clarity and evidence, argument-level issues, correlatives, and AI tells.

### [Pattern name] — [paragraph location]

> "[Offending line, verbatim]"

[One-sentence diagnosis.]

**Fix:** [Specific rewrite or directional cut.]

---

## Tier 2 — Voice tics and mechanics

[Same format.]

## Watch-items

Patterns observed in this draft that don't yet have a named rule.

- [Description + example]

## Summary

- Total flags: [N]
- Tier 1: [N] | Tier 2: [N]
- Top three patterns to address: [list]
```

## Calibration

### What to flag aggressively

- Every unsupported factual claim, unidentified person/company/term, and missing explanation of a load-bearing recommendation
- All correlative constructions and their cousins: "not X, but Y," "I don't mean X. I mean Y"
- Every rhetorical question that isn't reframing the thesis

### What NOT to flag

- Single uses of words that overlap with AI vocabulary but serve the piece ("significant" used precisely)
- Intentional cascades (three or more parallel sentences accreting specifics)
- Parenthetical asides that carry argumentative weight

When in doubt, ask: does this passage sound like the writer thinking out loud, or like a model that found a satisfying rhythm? The first stays. The second flags.
