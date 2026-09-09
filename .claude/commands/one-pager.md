---
model: sonnet
name: one-pager
description: Create a new product & engineering one-pager from a template, or review and improve an existing one against product best practices.
argument-hint: <initiative name to create new> or <Google Doc URL/ID to review existing>
---

# One-Pager

Two modes: **create** a new one-pager from a template, or **improve** an existing one with structured feedback against product best practices.

---

## Mode detection

- If $ARGUMENTS looks like a Google Doc URL or doc ID → **Improve mode**
- If $ARGUMENTS is a name or initiative description → **Create mode**
- If $ARGUMENTS is empty → ask: "Do you want to create a new one-pager or review an existing one?"

---

## Create mode

**Step 1: Get the initiative name**

If the user provided a name, use it. Otherwise ask: "What's the initiative or feature name?"

**Step 2: Copy the template**

Use `copy_google_drive_doc` with:
- Source doc ID: `YOUR_TEMPLATE_DOC_ID`  ← replace with your own one-pager template
- New title: `[initiative name] — one-pager`

**Step 3: Return the link**

Reply with the new doc URL and:

> Fill in DRI, Date, and Status at the top — then work top to bottom, writing the BLUF last.

---

## Improve mode

Read the doc, then evaluate it against the rubric below. Output structured feedback, then offer to apply fixes.

### Step 1: Read the doc

Use `get_google_drive_file` to fetch the content. If the user pasted text instead, use that directly.

### Step 2: Evaluate against the rubric

**Tone:** Be constructive and encouraging. A one-pager doesn't need to be perfect — it's a tool for alignment, not a final answer. The goal is to help the author make it land better, not to produce an exhaustive list of problems. Lead with what's working. Prioritise the 2–3 changes with the highest leverage. Don't flag minor issues. If the doc is mostly solid, say so.

Score each criterion as **Strong**, **Good start**, or **Worth adding**. Reserve **Worth adding** for things that would meaningfully change how the doc lands — not things that are merely absent.

---

#### The rubric

**1. Problem before solution**

The single most common failure. Does the doc spend real time on the problem before proposing anything? The reader should feel the problem is undeniable before they ever see the solution. If the doc opens with what you're building, it hasn't earned it yet.

Look for: a clear description of what's broken or missing, who experiences it, and a concrete example or data point that makes it feel real. Not a general statement — something specific.

**2. Why now**

Could this have been written six months ago? Could it be written six months from now? If yes, the "why now" is missing. The strongest one-pagers make a case rooted in something that recently changed: competitive moves, market shifts, user behavior, a dependency that just unlocked, a deadline that's approaching.

If you can't articulate why this is the right moment, the doc won't land with leadership — they're always choosing between things.

**3. Summary above the fold**

Write the whole doc first, then put a crisp summary at the very top. Someone skimming should understand the recommendation and the key argument without reading further. The detailed analysis — competitive screenshots, market dynamics, technical depth — lives below.

**4. Recommendation first, evidence second**

State what you think should happen, then support it. Don't make the reader assemble ten paragraphs into a conclusion. Lead with the answer, then prove it.

**5. Success criteria**

Are there 1–2 measurable outcomes that tell you whether this worked? Specific enough that in 6 weeks you can point to a number and say yes or no. Vague criteria ("improve conversion", "users love it") don't count.

**6. Non-goals**

What are you explicitly not solving? This is as important as the goals. Naming non-goals prevents scope creep, tells reviewers what debates to drop, and makes the proposal more credible. "We're not solving X in this phase" is a decision worth documenting.

**7. Decisions documented**

A good one-pager becomes the home base for decisions made along the way — not just the initial pitch. Does it record scoping decisions, descoped segments, pivots? Does it link out to relevant research, designs, or technical specs? If not, it'll get stale and stop being useful.

**8. Length and scannability**

Two pages max. Prose, not a 20-page PRD. The most important content is above the fold; deep analysis is pushed below. If someone is scanning quickly, can they get the point? Are there walls of text that should be trimmed or moved to an appendix?

**9. Technical constraints (for engineers)**

If written by an engineer, this is an advantage — use it. Are the key feasibility constraints and tradeoffs called out upfront? Surfacing these early saves weeks of back-and-forth. If it's missing, reviewers will add it in comments anyway.

**10. Alignment questions**

Does the doc close with questions that invite reaction? Something like "does this framing feel right?" or "are there angles we're missing?" turns the one-pager from a pitch into a conversation starter. That's what actually gets buy-in. A doc that ends with a plan and nothing else puts reviewers on the back foot.

---

### Step 3: Output feedback

Open with a short (2–3 sentence) summary of the doc's overall strength. Then present a scored table — only include criteria where there's something worth saying. Skip criteria that are fine.

```
| # | Criterion | Score | Finding |
|---|-----------|-------|---------|
| 1 | Problem before solution | Good start | The problem is there but comes after the solution — swapping the order would make the case feel more earned. |
| 2 | Why now | Strong | Clear competitive trigger with specific data. This is the best part of the doc. |
...
```

For each **Worth adding** item, give one specific suggestion — quote the section, show what a stronger version looks like. Keep it brief. One concrete example beats a paragraph of advice.

End with:
- **What's working:** 2–3 genuine strengths
- **If you only do one thing:** the single highest-leverage change

### Step 4: Offer to apply fixes

Ask: "Want me to apply any of these to the doc directly?"

If yes, use `update_google_drive_doc` to apply the suggested rewrites. Work section by section, confirming each before writing.

---

## Template sections (reference)

| Section | What goes here |
|---------|----------------|
| **BLUF** | Write last. One or two sentences: what you're proposing and the expected return. |
| **Problem & context** | What's broken or missing, who experiences it, why it's timely, and what's at stake if unsolved. |
| **Value** | Business case in numbers — revenue, conversion uplift, cost reduced, users unblocked. Real figures only. |
| **Proposed solution** | High-level approach, not a spec. Link to designs or docs if they exist. |
| **Success metrics** | One or two measurable outcomes tied to the value case. |
| **Effort estimated** | Team size, duration, key dependencies. |
| **Out of scope** | Explicit exclusions. Name future work here rather than leaving it implied. |
| **Open questions** | Unresolved decisions with tagged owners. |
