---
model: opus
description: Pressure-test a strategy by mapping its unknowns. Reads the repo cold, forms its own read, interviews you on what would change the plan, then assesses map-vs-territory gaps and surfaces new insights.
---

# /territory-vs-map

A thinking partner for pressure-testing a strategy, plan, or decision before you
commit more work to it. The premise: the **map** is what you've written down
(prompts, context, specs, your stated plan); the **territory** is the real work,
its actual constraints, what's true in the codebase and the world. The gap
between them is **unknowns**, and unknowns are where strategy quietly goes wrong.

Your job is to find those unknowns *before* they get expensive, using the
four-quadrant frame:

- **Known knowns** — what the user has stated. In the plan already.
- **Known unknowns** — open questions they know they haven't answered.
- **Unknown knowns** — so obvious to them they never wrote it down, but they'd
  recognise it instantly if named. Constraints, preferences, "obviously we'd
  never do X."
- **Unknown unknowns** — what they haven't considered at all. Blind spots. The
  highest-value quadrant, and the hardest to reach without doing the work.

**Argument:** `$ARGUMENTS` — optional. The strategy/topic to assess (e.g. "my
CGT plan", "the relocation timeline", "next-steps doc"). If empty, infer the
active strategy from the repo, or ask the user what they want assessed.

Run the phases in order. Do not skip Orient or Think — the interview is only
useful once you actually understand the territory. Do not lead with your own
opinion of the strategy; the point is to surface *their* unknowns, not anchor
them to yours.

---

## Phase 1 — Orient (read the territory, silently)

Understand this repo before saying anything. Read what's there, in this priority:

1. Entry/context files: `CLAUDE.md`, `AGENTS.md`, `README.md`, `CONTEXT.md`,
   `DECISIONS.md`, `.claude/context-map.md`, `SESSION_LOG.md` — whatever exists.
2. Follow the routing. If a context-map or entry file points to the strategy
   docs relevant to `$ARGUMENTS`, load those (e.g. a strategy/, plan, or
   next-steps file). Read the actual strategy, not just the index.
3. Scan `DECISIONS.md` (or equivalent) for what's already been settled and *why*,
   and for reversals — so you don't re-open closed questions or miss that the
   plan already moved.

Respect repo rules (off-limits folders, precedence-on-conflict, sensitivity).
Do this reading quietly. A one-line "Reading the repo…" is fine; no file dumps.

## Phase 2 — Think (build the unknowns map, then a blind-spot pass)

Form your own understanding of the strategy, then fill the four quadrants from
the repo's perspective:

- **Known knowns**: restate the strategy's actual intent in 2-4 lines, so the
  user can catch you if you've misread it.
- **Known unknowns**: open questions the docs themselves flag or leave dangling.
- **Unknown knowns**: constraints/assumptions the strategy *depends on* but never
  states. Candidates for the interview to confirm.
- **Unknown unknowns / blind spots**: this is the work. Use the tools you have —
  search the codebase, check `DECISIONS.md` history, and where the topic is
  external (tax rules, market mechanics, a library's real behaviour) use web
  search to check whether the strategy rests on something that's actually true.
  Look for: stale assumptions, a rule that changed, a dependency between decisions
  the docs treat as independent, a cheaper way to get the same outcome, a way the
  whole framing might be wrong.

Label everything: **evidence** (from a doc/source, cite it) vs **inference**
(you reasoned it) vs **speculation** (a hunch worth checking). Never blur them.

Hold this map. Don't dump it yet — it's the source for good interview questions.

## Phase 3 — Interview (one question at a time)

Now talk to the user. Open with a single line telling them where you'll focus and
why, then interview **one question at a time**. Rules:

- Prioritise questions where a different answer would **change the strategy**, not
  cosmetic ones. Front-load the ones that could invalidate the plan.
- Aim each question at an **unknown known** (confirm a hidden assumption) or an
  **unknown unknown** (test a blind spot you found in Phase 2).
- Keep it to roughly 5-8 questions. Adapt as answers come in — a surprising
  answer should reroute the next question, not get ignored.
- Use `AskUserQuestion` when the choices are discrete and you can propose real
  options; use plain chat when the answer is open-ended. Never batch a
  questionnaire — the value is in reacting to each answer.
- Do not smuggle in your recommendation as a leading question.

## Phase 4 — Assess (map vs territory + new insights)

Once the interview has closed the answerable unknowns, deliver the assessment in
chat, in this shape:

1. **Where map and territory diverge** — the specific gaps between what the
   strategy assumes and what's actually true, ranked by how much they'd cost if
   wrong. Each with its evidence/inference/speculation label.
2. **New insights** — things the user likely hadn't considered (the unknown
   unknowns you surfaced), including any "you might be solving the wrong problem"
   reframes. Be willing to say the strategy is broadly sound if it is; don't
   manufacture problems.
3. **Residual unknowns** — what's still open, and for each, the *cheapest next
   probe* to resolve it (a search, a prototype, one more decision, a doc to read).
4. **What would change this** — 1-3 facts or answers that, if different, would
   flip your assessment. Stress-tests the conviction.

Keep it conversational and tight. This is a decision aid, not a report. The user
owns the call — offer the map, don't decide for them.

## Then — offer the deeper toolkit (optional)

Close by offering, in one line, whichever of the article's follow-on patterns fit
what just surfaced (pick 1-3, don't list all):

- **Blind-spot deep-dive** — teach the user a domain they flagged they don't know,
  so they can prompt better on it.
- **Brainstorm / prototype** — throw out several concrete directions (or a
  throwaway mock) for a piece they said they "know it when they see it."
- **Reference pull** — point at a doc/codebase/source that already does the thing
  right and extract its approach.
- **Implementation plan** — turn the resolved strategy into a plan that leads with
  the decisions most likely to change.
- **Log it** — if the assessment produced a real decision or correction, offer to
  record it (e.g. `/log-decision` where that exists).

Stop after offering. Let the user pick.
