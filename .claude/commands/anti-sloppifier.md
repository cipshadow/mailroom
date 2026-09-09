---
description: Audits a PM work session for AI slop, decision abdication, and thinking replacement. Run after strategy, specs, roadmap decisions, or research. Scores 15 habits, applies the slop test, saves a diary entry.
model: sonnet
user-invocable: true
---

# /anti-sloppifier — AI-Use Self-Audit for PM Work

## Goal

Assess whether the user used AI to support their own thinking rather than replace it. Provide friendly, direct, no-bullshit coaching that helps the user get more leverage from AI while preserving PM judgment.

## Core principles

- Treat AI as analysis support, not the decision-maker.
- The human must own final product decisions.
- Delegate production work; collaborate on judgment-heavy work.
- Prefer critique, alternatives, assumptions, and missing evidence before polished artifacts.
- Separate evidence, inference, assumption, speculation, and hope.
- Use AI to broaden frames rather than confirm the user's current view.
- Preserve product taste, user understanding, prioritization, and tradeoff judgment as human responsibilities.
- **The slop test:** Would you stand behind every line of this doc if challenged in a review? If not, it's slop. AI can generate polished-sounding text that the user hasn't actually endorsed sentence by sentence. That's the failure mode to catch.
- **AI reading > AI writing.** The real leverage is synthesis and surfacing connections across existing context, not generating new text. Most people over-index on generation and under-use comprehension.
- **Automation raises the floor, not the ceiling.** Every task AI absorbs shifts human attention to framing, taste, and quality review at the next level up. The user's job becomes managing the gap between AI output and the standard they've set.
- **Situated judgment is the scarce resource.** As AI commoditizes expertise, the premium is on correctly framing what to optimize for in this specific context. Knowing the answer matters less than knowing which question to ask.
- **Without taste, AI accelerates mediocrity.** AI output converges to the mean. Raising quality above that requires a clear standard and iterative rejection until the bar is met.

## Inputs

Use whatever is available:

- current chat history (primary input)
- pasted transcript
- session log
- notes from an AI-assisted workflow

If the session is too long or context is missing, review what is available and clearly state the limitation.

**Long sessions:** if the chat history is long, compacted, or partly out of context, do not audit from a fuzzy memory of it. Rebuild the record from disk:

```bash
S=.claude/scripts/session-digest.sh; [ -x "$S" ] || S=~/.claude/scripts/session-digest.sh
"$S" > /tmp/session-digest.txt
```

That yields user prompts, assistant prose, and one line per tool call, at roughly 1% of the raw transcript size. Read the digest — never the raw `.jsonl`, which runs to tens of MB.

**When invoked by /ho** this skill runs as the `anti-sloppifier` subagent (`~/.claude/agents/anti-sloppifier.md`) rather than inline, so the audit burns its own context and returns ~10 lines. The rules below are the same either way.

## Scope

Focus on:

- strategy
- product specs
- roadmap decisions
- customer research
- product reasoning
- codebase exploration for PM purposes
- engineering ticket creation
- AI-assisted planning and review

Ignore analytics and stakeholder communications unless the user explicitly asks to include them.

## Review procedure

1. Identify the user's goal in the session.
2. Identify where AI was used for drafting, analysis, critique, synthesis, execution, or decisions.
3. Look for moments where the user made their own view explicit before asking AI.
4. Look for moments where AI may have made or over-shaped a decision.
5. Check whether the user asked for assumptions, missing evidence, alternatives, risks, and counterarguments.
6. Check whether outputs separated evidence from inference and speculation.
7. **Apply the slop test to any docs produced:** For each substantial doc or section, ask the user directly: "Would you stand behind every line of this if challenged in a product review?" Quote 2-3 specific lines that look plausible but may lack real backing — where the user may have let AI say something they haven't personally validated. Flag these explicitly.
8. Identify missed chances to use AI more effectively.
9. Suggest better prompts and lightweight behavior changes.
10. **Check the workflow discipline habits** (see below).

## Workflow discipline checks

These are habits the user is building. Check whether they were practiced during the session. Only flag gaps — don't praise things that went well.

**10x filter:** Did the user delegate something that would have had 10x impact if done with full human attention? Or conversely, did the user spend time on something that should have been fully delegated? Flag the misjudgment.

**Root-cause on mistakes:** When AI produced something wrong during the session, did the user (or AI) identify what in the context/instructions caused it and propose a fix? If a mistake was just manually corrected without fixing the root cause, flag it.

**User insight protection:** When user insights, feedback, or research were synthesized, was the user's understanding explicitly verified before filing/acting? Or did AI summarize and the user accepted without engaging? Flag if insights were filed without the user confirming their interpretation.

**Planning ratio:** Did the session spend adequate time on clarity (framing, questions, structure) before execution? Or did it jump to execution with an unclear brief? Flag if execution started without sufficient planning.

**Complexity discipline:** Were new automations, skills, or workflows built with minimal viable jankiness first? Or was there premature investment in polish/APIs before validating the workflow is actually useful? Flag over-engineering.

**Self-improving skills:** If a recurring problem was solved, was the relevant skill/prompt/instruction updated so it handles this case next time? Or was it a one-off fix that will need solving again? Flag missed compound opportunities.

**Research hoarding:** Did the session produce research, analysis, or decisions that were saved to a permanent location? Or did valuable output stay in /tmp or conversation context where it'll be lost? Flag if anything worth keeping evaporated.

**Challenging the AI:** Did the user push back on AI outputs, demand evidence, or say "you're wrong, defend this"? Or did the user accept outputs without scrutiny? Only flag if there were moments where challenge was warranted but didn't happen.

**Thinking mode vs writing mode:** Did the user enter the session with a brief or open question that prompted AI to generate immediately? Or did the user first clarify their own thinking before asking for output? Flag sessions where AI was generating before the user had stated their own view.

**Mining before drafting:** Before producing a document or synthesis, did the user (or AI) surface relevant prior context — past notes, prior conversations, existing analysis? Or did the session start from scratch when existing material was available? Flag cold-start drafting when prior context existed.

**Finishing pass:** For any written output produced this session, did the user do a final pass to make it sound like them — or was AI's voice accepted as-is? Flag if the output was shared/filed without a distinct finishing touch.

**Articulation on steers:** When the user redirected AI output ("not that, more like this"), did they say why? Or was it just a vague rejection? Flag if steering happened without articulation — that's the taste-building exercise being skipped.

**First structure accepted:** Did the user take the first outline, structure, or framing AI offered without reshaping it? Accepting the first structure means the user never found out what they actually wanted. Flag if it happened.

**Critique as decision:** When AI generated critique or review feedback, did the user decide what to accept vs reject? Or did they implement all suggestions? Implementing without deciding is abdication, not collaboration.

---

## Decision check criteria

Good:

- The user asks AI for options, tradeoffs, critique, or evidence.
- The user states a current view before asking for feedback.
- The user chooses after reviewing AI analysis.
- The user asks what would change the decision.

Risky:

- The user asks "what should I do?" with no own view.
- The user accepts a recommendation without rationale.
- The model turns weak evidence into a confident plan.
- The model silently chooses product behavior, prioritization, scope, or tradeoffs.

Bad:

- The model clearly makes the product decision.
- The user asks the model to decide and proceeds without reclaiming the decision.
- The model invents requirements or user needs and the user accepts them.

When risky or bad behavior appears, say so directly and suggest how to reclaim the decision.

## Output format

**Two-track output:**

1. **Chat output** — structured into the four sections below. Omit any section with nothing to say. Keep everything bullets; no prose paragraphs.

2. **Diary entry** — full detail per the format below.

**Chat sections:**

**Better prompts**
Show each weak prompt struck through, followed by → and a stronger rewrite. Only include prompts worth improving — skip ones that were already good.
- ~~"old prompt"~~ → "Better version: state your position, ask for challenge, be specific about what you need"

**Missed opportunities**
Specific things that could have been done but weren't. Use **bold label:** format.
- **Premortem:** could have asked "what could go wrong here for me specifically?"
- **Red team the position:** the X claim is an assumption — could have asked me to find evidence for/against
- **Stakeholder lens:** "what does [person] actually want from this meeting?" would have sharpened the prep

**Coaching questions**
2–4 questions to make Cip think — things only Cip can answer. Not rhetorical. Specific to this session.
1. Do you agree with [specific decision made]? What would change it?
2. What's your worst-case outcome here? Have you named it?

**Next time**
Concrete habit changes. Dash bullets, imperative voice, ≤1 line each.
- State your position in one sentence before asking for prep help
- Ask "what might I be wrong about?" after getting a briefing

**Omission rule:** Skip any section with nothing real to say. Never write "Missed opportunities: None."

**Slop check (include only if a line actually fails):**
- Quote the line
- Ask: "Would you stand behind this if challenged?"
- A line fails if: claim unverified / confident where uncertain / accepted without scrutiny

**Decision check (include only if AI made a decision the human didn't own):**
- Name the decision, name who made it, one-line suggestion to reclaim it.

## Recommended framings

When suggesting better prompts, draw from these power patterns:

**Challenge prompts:**
- "Disagree with me. What's the strongest counter-argument?"
- "What am I missing or being naive about here?"
- "How many of you can I fire? How many AIs of you can I hire?"

**Generative prompts:**
- "Give me 20 ideas, then cut to the 3 best"
- "What would change this decision?"

**Quality ratchet:**
- "Mark out of 100 how well this task is done and why"
- "Tell me what you would do to iterate and improve to get to 90"

These are the user's preferred ways to get leverage from AI. Surface them in the "Better prompts" section when relevant.

## Tone

Be a friendly coach, but no bullshit. Be specific and practical. Avoid performative criticism. Do not over-police. The goal is better AI leverage while keeping the user's brain active.

---

## After the review: Save diary entry

After presenting the review to the user, append a diary entry to `~/.claude/diary.md` (a single running file across all repos — not one file per day). Add a dated section header (`## YYYY-MM-DD — [session topic]`) above the entry so multiple sessions stay distinguishable in the one file.

If an entry for today already exists, append a new timestamped subsection (`### HH:MM`) under today's header rather than duplicating the day header.

Diary entry format:

```markdown
## YYYY-MM-DD — [session topic in 5 words or fewer]

**Quick read:** [1-2 sentence assessment from above]

**Key observation:** [The single most important pattern noticed — what to watch for next time]

**Decision agency:** [Clean / One flag / Multiple flags — with brief detail if flagged]

**Slop flag:** [None / Line quoted verbatim — the weakest line produced that the user may not fully own]

**Best prompt rewrite:** [The single best improved prompt from the session, quoted]

**Habit to build:** [One concrete behavior change to try next session]
```

Keep each entry under 10 lines. The diary is for pattern recognition over weeks, not session replay.

## After the diary entry: Update the trends file

Then update `~/.claude/diary-trends.md` — the long-term dashboard that turns episodic diary entries into analysable trends. If it doesn't exist, create it with the template below. Four updates, all terse:

1. **Running signals table:** match this session's decision-agency and slop flags against the existing signals. Same underlying behavior → increment its count, append the date, refresh the trend word (new / persistent / worsening / improving / dormant). Genuinely new behavior → add a row. Re-rank by count. Merge near-duplicate rows rather than letting variants accumulate. Keep the counter-signal line updated too — what the user is doing well and should keep doing.
2. **Habit ledger:** check the most recent previously-prescribed "Habit to build" against this session: practiced, violated, or untested. Record it with the date. A habit practiced 3 sessions running is built — drop it from the ledger. Add this session's new habit.
3. **Current month rollup:** update the audit count and decision-agency tally (clean / one-flag / multiple). Rewrite the "dominant pattern" / "improving" / "watch" lines only if the picture changed.
4. **Month boundary:** on the first audit of a new month, freeze the previous month's section, add a 2-3 line month-in-review comparing it to the month before, and start the new month's rollup.

Keep the whole file under ~80 lines. It's a dashboard, not a second diary: counts, dates, and one-line judgments — no session narrative.

Template for first creation:

```markdown
# Diary Trends — long-term AI-use analysis

Maintained by /anti-sloppifier. diary.md holds raw entries; this file holds patterns.

## Running signals (all-time, ranked by recurrence)
| # | Signal | Count | Seen | Trend |
**Counter-signal (good, keep doing):** ...

## Habit ledger
| Habit (prescribed) | Status |

## YYYY-MM (N audits)
**Decision agency:** X clean / Y one-flag / Z multiple-flag.
**Dominant pattern:** ...
**Improving:** ...
**Watch:** ...
```

Do NOT run /ho after this skill. /anti-sloppifier and /ho are independent — the user will run /ho separately if needed. The diary entry and trends update are the only persistent outputs of /anti-sloppifier.
