---
name: every-review
description: Full editorial workflow conductor. Sequences craft reviewers (dev-edit, panel, asshole, hemingway, etc.) based on the draft's current stage, then hands off to internal-prose-review for mechanics. Use at any stage of a draft.
user_invocable: true
model: sonnet
---

# Every Roundtable

Full editorial workflow for Every drafts — from rough shape to publish-ready. This skill sequences the right tools in the right order based on where your draft actually is, rather than making you know the toolkit upfront.

**What this is NOT:** `/every-style-editor` handles grammar, punctuation, and Every mechanics compliance. Run that at the very end. Everything before it is this skill's domain — whether the piece works, moves, argues, lands, and sounds like you.

---

## Phase 0: Intake

Before doing anything, I need to know where you are. Answer these:

1. **Stage:** First real draft / Has structure but needs polish / Near-final, just stress-testing
2. **Piece type:** Essay / Argument-opinion / Explainer-technical / Narrative / Newsletter
3. **Audience:** General / Every readers / Specialists
4. **Goal:** What do you most want the piece to do? (land emotionally / convince / teach / entertain / something else)
5. **Biggest worry:** What feels weakest or most uncertain to you?

Your answers determine which reviewers run and in what order. Skip them and I'll infer from the draft — but you'll get better routing if you answer.

---

## The Workflow

### Stage A: Structure first (early draft)

If the piece is rough, messy, or you're unsure it holds together, run structure checks before any craft lenses. Polishing sentences on a broken frame wastes time.

**Tools in order:**
1. `/dev-edit` — Argument, structure, stakes, evidence check. Are the bones solid? Run this first.
2. Fix what's broken, or decide what to ignore.
3. **Gate:** Does the piece have a clear argument/promise, a payoff, and no major structural holes? If yes, proceed. If no, iterate on structure before moving on.

### Stage B: Craft pass (revision stage)

Once structure holds, bring in the lens reviewers. The right set depends on piece type:

| Piece type | Recommended panel |
|------------|------------------|
| Personal essay | sedaris, mom, sorkin, vonnegut |
| Argument / opinion | asshole, vonnegut, hemingway, mom |
| Explainer / technical | eli5, mom, hemingway, sorkin |
| Narrative | vonnegut, hitchcock, sorkin, sedaris |
| Newsletter | mom, sorkin, hemingway |

**Tools in order:**
1. Run the panel with `/panel` (orchestrates all lens reviewers + synthesizes)
2. Review the synthesis — look at the consensus findings and productive tensions
3. Decide which tensions to resolve yourself; use `/debate` on specific tensions if you want reviewers to argue them out rather than you deciding cold
4. Apply fixes

### Stage C: Stress-test (near-final or high-stakes)

Before you think you're done, put it through the hardest reads:

1. `/asshole` — Hostile read. Every claim, every logical gap, every piece of thin evidence. If your piece can't survive this, don't publish it.
2. `/hitchcock` — Is the tension visible? Are stakes established early, or buried? (Skip for explainers)
3. **Gate:** Can you defend every claim? Does it move? Is the ending earned?

### Stage D: Polish pass

Once content is solid, tighten the language:

1. `/hemingway` — Kill everything that doesn't earn its place. Especially dangerous after Stage B adds nuance that creates bloat.
2. `/line-edit` — Sentence-level: rhythm, voice, AI tells, hedge words, passive constructions. Delivers a clean draft + change log so you can revert anything.

### Stage E: Mechanics (final)

Last step, only after everything above:

1. `/every-style-editor` — Grammar, punctuation, capitalization, Every-specific style rules. This is compliance, not craft. Run it on the final draft only.

---

## Quick Reference: Which tool for which problem

| Problem | Tool |
|---------|------|
| "The piece feels like it doesn't hold together" | `/dev-edit` |
| "I don't know what feedback I need" | `/panel` |
| "Is my argument actually good?" | `/asshole` |
| "Specialists get it but I'm worried it loses everyone else" | `/mom` or `/eli5` |
| "It's fine but forgettable / too serious" | `/sedaris` |
| "It feels slow midway through" | `/sorkin` |
| "The ending doesn't land" | `/hitchcock` or `/vonnegut` |
| "It's too long / overwritten" | `/hemingway` |
| "Two reviewers disagreed and I'm not sure who's right" | `/debate` |
| "Sentence-level cleanup before publishing" | `/line-edit` |
| "Mechanics: comma usage, caps, Every style rules" | `/every-style-editor` |

---

## When to shortcut

Not every draft needs all five stages. If you're doing a short newsletter riff:
- Skip Stage A if the structure is simple
- Run 2-3 lens reviewers manually instead of `/panel`
- Go straight to `/line-edit` + `/every-style-editor`

If it's a major essay going to Katie or the main feed:
- Do all five stages
- Run `/asshole` at Stage C even if it hurts

---

## The key distinction: craft vs. mechanics

The skills in this roundtable ask: *does the piece work?*

`/every-style-editor` asks: *is it correctly written per Every's rules?*

Correct mechanics on a piece that doesn't work = polished garbage. The roundtable first, style-editor last, every time.
