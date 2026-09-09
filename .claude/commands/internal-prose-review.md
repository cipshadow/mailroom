---
model: sonnet
name: internal-prose-review
description: Review content against Stripe's internal style guide and output a numbered table of corrections.
---
Review content against Stripe's internal style guide and output a numbered table of corrections.

## Input

The user will provide content in one of three ways:
1. **Pasted text** — review it directly
2. **Google Doc ID or URL** — fetch with `get_google_drive_file` (use `include_indices: true` if the user wants fixes applied)
3. **A file path** — read the file

If no content is provided, ask which doc to review.

## Review process

Run a three-pass review:

### Pass 1: Mechanical checks (find-and-replace level)

Scan for violations of these rules. Flag every instance.

**Spelling & terminology:**
- American spelling only (analyze, not analyse; optimize, not optimise; color, not colour)
- "fintech" not "FinTech"
- "ecommerce" not "e-commerce"
- "payment" singular before nouns, EXCEPT before "services", "infrastructure", "platform", "products" where it's "payments"
- Don't use "reach out" — rephrase
- Don't use "fraudsters" — use "fraudulent actors"
- "canceled/canceling" but "cancellation"
- NEVER abbreviate "authentication" to "auth" — use "authn" or spell it out. "Auth" means authorization.

**Numbers:**
- Spell out zero through nine in prose; numerals for 10+
- Use % sign with numerals: 71% (not "71 percent")
- BUT spell out "percent" if the number is spelled out: "seven percent"
- $ before numbers, adjacent: $5 billion, $370K
- Use ¢ for cents: 30¢ (not $0.30)
- Large numbers: $5 billion, 14 million, $370K (K/M/B/T uppercase)
- Commas in numbers over three digits: 1,000
- Non-specific amounts: 15+ (plus sign, no space)
- En dash for ranges: $5–$10, 60–70%, 2019–2024 (not hyphen)
- Spell out numbers starting a sentence (unless a year)
- Always present metrics as trajectory: baseline > target (growth rate). Never a number without context.
- Revenue in dollars, never percentages alone. Pair percentages with absolute numbers.
- Growth rates use specific timeframes: "35% YoY," "39% MoM." Never "growing quickly."
- If you see "significant," "many," or "meaningful" — flag it and ask for a number.

**Punctuation:**
- Oxford comma always: x, y, and z
- Em dash (—) without spaces; max twice per paragraph
- En dash (–) for ranges, no spaces
- Periods and commas inside quotation marks
- No exclamation points (except rare cases)
- Don't use slashes: rewrite "and/or", "risk/reward" → "risk-reward" or rephrase
- Comma after introductory phrases
- Colon followed by lowercase in body copy, uppercase in titles/subtitles
- No terminal punctuation in headers (except question marks)

**Formatting:**
- Sentence case for everything (NOT title case), except book/publication titles
- Don't use bold for emphasis — recast the sentence. Bold marks structural elements (priority names, section leads).
- Don't use italics for emphasis — recast the sentence. Italics mark user voice, caveats, or publication titles.
- American date format: October 15, 2018 (no ordinals: not "October 15th")
- Abbreviations: no periods (US, EU, UK — not U.S., E.U.)
- Tables only for genuinely columnar data. Don't use tables for prose.

**Links:**
- Descriptive link text (2–4 words); never "click here" or "check this out"
- Don't link punctuation
- Every number should link to its source when possible (dashboard, spreadsheet, doc)

**Lists:**
- Period for complete sentences; no punctuation for fragments
- Parallel structure across all items (same tense, same grammatical form)
- Numbered lists only when order matters
- Start items with capital letters
- If one list in the doc uses periods, all lists use periods

### Pass 2: Consistency checks (whole-document level)

Scan the entire document for internal inconsistencies. Flag every instance.

**Tense consistency:**
- Strategy docs: present tense for current state, future tense for plans. Don't drift between "we are building" and "we built" in the same paragraph.
- Within any section, tense should be uniform unless explicitly shifting timeframe.

**Pronoun consistency:**
- If the doc uses "we" for the team, don't switch to "the team" or the product name as subject mid-paragraph.
- Every "it," "this," "that," and "they" must have an unambiguous referent. If two nouns could be the referent, flag it.

**Subject consistency in lists:**
- If a bullet list starts with "We will...", every bullet should start with "We will..." not switch to "The product..." or imperative mood.

**Capitalization consistency:**
- Product names and internal terms must be capitalized the same way throughout. If it's "Data Only" on page 1, it can't become "data only" on page 4.

**Number formatting consistency:**
- Don't spell out "three" in one paragraph and use "3" in the next. Apply the rule uniformly.

**Date formatting consistency:**
- If one place uses "Q3 (Aug)", don't switch to "August 2026" or "Q3 2026" elsewhere without reason.

**Abbreviation consistency:**
- Define on first use, then use the abbreviation everywhere after. Don't re-expand. Don't use before defining.

**Table formatting consistency:**
- Column headers should use the same labels across tables (e.g., always "Impact" not sometimes "Why it matters").
- Cell voice: if one cell is a full sentence, all cells in that column should be full sentences.

**Bullet punctuation consistency:**
- If one list uses periods, all lists in the doc use periods. If one uses no punctuation, all use none.

**Grammar:**
- Subject-verb agreement with collective nouns: "The team ships" (singular) or "The team members ship" (plural), but don't mix.
- Dangling modifiers: "Launching in Q3, the team will..." not "Launching in Q3, the product will reduce..."
- Comma splices: two independent clauses need a period, semicolon, or conjunction. Not just a comma.
- Run-on sentences: if a sentence has more than two clauses or exceeds ~35 words, flag it for splitting.

### Pass 3: Voice and strategy doc craft (sentence-level)

Re-read each paragraph checking against patterns from 20 widely-shared Stripe strategy docs. Only flag issues that meaningfully hurt clarity, persuasiveness, or voice.

**Voice & tone:**
- Plain, confident, matter-of-fact language. No corporate speak.
- Use "we" for Stripe consistently. Never "the company" or passive "it was decided."
- Name problems plainly, then immediately pivot to the response. Never hide behind euphemisms.
- Write like someone who finds the problem genuinely interesting. Use precise language that reveals understanding.
- Confident about the future: "we will," never "we might" or "we hope to consider."
- No hedging when you're not uncertain: "I think", "perhaps", "maybe."
- No filler: "actually", "very", "just", "basically", "essentially."
- No throat-clearing: "It's important to note that...", "I'd be happy to..."
- No filler transitions: "Turning now to," "Another important area is." Sections begin directly.
- Avoid starting sentences with "This" — be specific about the referent.
- Avoid "in order to" — just use "to."
- Active voice for Stripe actions, always. "We will launch," never "will be launched."
- Companies are singular: "Stripe released its..." not "their."
- Lowercase job titles unless directly preceding a name.
- No hyperbolic language. Banned words: "violation," "crisis," "illegal," "masterclass."
- No "dominate" or implying unfair competition. Compete by serving users.

**Argument quality:**
- Lead with observed reality, then derive the strategic claim: [what we see] > [why it matters] > [what we will do]. Claims should feel earned, not asserted.
- Every section should close with the "so what": what we will do about it.
- After explaining the current state, ground it with named users or specific proof points. "A solopreneur in the US shut down their Revolut account" beats "users prefer unified management."
- Before saying what you will do, say what you did. Retrospective before prospective.
- Unvalidated numbers should use `[brackets]`. Missing data uses `[NEED: ...]`. Synthetic placeholders use `[PLACEHOLDER: ...]`.

**Sentence craft:**
- Vary sentence length: long explanatory, then short declarative. "This is only becoming more important."
- Bold the thesis sentence, then explain in regular weight. Reader gets the punchline first.
- Use parallel construction in lists.
- Cut words that don't add meaning. But keep implications, reasoning, and explicit connections.
- If a sentence exceeds ~30 words, consider splitting.

**Structure signals (flag if missing, don't rewrite):**
- BLUF box at the top stating the decision needed
- Numbered priorities (three per section is the sweet spot)
- From > To summary table for long docs
- "What's staying the same / What's changing" frame for strategy updates
- Explicit scoping: what this covers and what it does not
- Named disagreements with attribution, not pretended consensus
- Lookback commitment: when and where metrics will be reviewed

### Pass 4: Paragraph and flow quality (whole-paragraph rewrites)

After the sentence-level pass, re-read the doc as a reader would, focusing on paragraph construction, section flow, and document rhythm. For each issue, provide the full current text and a full rewritten version. Do not change semantics, only style and presentation.

**Sentence overloading:**
- Flag paragraphs where every sentence packs 2-3 ideas joined by commas, colons, or semicolons. One compound sentence per paragraph is fine for punchlines; every sentence doing it is fatiguing.
- Fix: one idea per sentence, then one compound sentence for the punchline.

**Restating the section title:**
- Flag opening sentences that rephrase the heading without adding information. E.g. heading "Authentication: a layer throughout the fabric of Stripe" followed by "Beyond its standalone value, authentication is deeply embedded in the fabric of Stripe."
- Fix: cut the restatement, start with the argument.

**Meta-narration:**
- Flag phrases that describe what the doc is doing rather than making the point: "Below we describe," "Our work interweaves across the three," "We are reframing it as."
- Fix: cut the meta-language, state the content directly. The reader can see the structure; tell them the content.

**Word repetition in sentences:**
- Flag sentences where the same noun appears 3+ times. E.g. "Every new launch expands authentication's surface area; every optimization improves all the products that authentication powers, expanding authentication PV across Stripe."
- Fix: use pronouns or rephrase to eliminate repetition.

**Orphan paragraphs:**
- Flag paragraphs that sit between two sections without clearly belonging to either. E.g. a flywheel paragraph floating between a wins table and the next section heading.
- Fix: suggest moving it into the section it belongs to, or making it a callout box.

**Missing transitions between major sections:**
- Flag abrupt jumps between major doc sections (e.g., from strategy principles to roadmap with only a horizontal rule). The best Stripe strategy docs use a one-sentence bridge.
- Fix: suggest a bridge sentence like "Here's how we plan to deliver against these principles."

**Dense explanation blocks:**
- Flag blocks of 5+ lines of continuous explanation (e.g., chart legends, methodology descriptions) that interrupt the reading flow.
- Fix: suggest converting to a compact key (one line per item), a footnote, or a collapsible section.

**Clichés and borrowed phrases:**
- Flag well-known clichés used as structural devices. E.g. "With great X comes great Y" (Spider-Man), "the best X is the one that never happens."
- Fix: suggest a direct statement that makes the same point without the borrowed phrasing.

**Infinitive-after-colon awkwardness:**
- Flag constructions like "a principle: to run infrastructure that..." — the infinitive after a colon reads awkwardly.
- Fix: recast as "a principle: infrastructure that..." (state the thing, not the act of doing the thing).

**Table subject/voice consistency across tables:**
- Flag when different tables in the same doc use different subject patterns. E.g. one wins table uses third person ("Standalone 3DS reaches...") while another uses first person ("We launched DCAP...").
- Fix: suggest standardizing to "We [past tense]" across all wins tables (the strongest pattern from Stripe strategy docs).

**Duplicate words from editing:**
- Flag obvious editing artifacts: "We shipped agentic commerce authentication ships for Sessions" (duplicate "ships"), stray linebreaks mid-sentence, double spaces.

## Output format

Present results as a numbered table:

```
| # | Location | Issue | Original | Suggested fix |
|---|----------|-------|----------|---------------|
| 1 | Section, paragraph | Brief description | "exact text" | "corrected text" |
```

Group by pass:
- **Mechanical (Pass 1):** spelling, numbers, punctuation, formatting
- **Consistency (Pass 2):** tense, pronouns, capitalization, table formatting
- **Voice & craft (Pass 3):** tone, argument, sentence construction
- **Paragraph & flow (Pass 4):** paragraph rewrites, section transitions, document rhythm

After the table, add:

**Recurring issues:** List patterns that appear multiple times (e.g., "British spelling ×4").

**Structure signals missing:** List any structural elements from the checklist that are absent from the doc.

**Not flagged (by design):** List any style rules you intentionally skipped because they don't apply to the document type (e.g., UI button conventions for a strategy doc, BLUF box for a PRFAQ which has its own structure).

## Applying fixes

If the user asks to apply the fixes:

1. If working with a Google Doc: fetch with `include_indices: true`, then apply edits from bottom to top using `update_google_drive_doc`. Note: table cells cannot be edited via the API — list those separately for manual fix.
2. If working with a local file: use the Edit tool.
3. If working with pasted text: output the corrected version.

## Exclusions

The user may say "exclude N, M" referring to row numbers. Remove those from the list and re-number.

## Sources

The rules in this skill are distilled from your organisation's internal style guides and a corpus of exemplary docs. To adapt this skill:

1. Replace the rules above with conventions from your own style guide
2. Add any organisation-specific terminology rules to Pass 3
3. Add vocabulary to avoid (AI slop, corporate-speak) based on your context
