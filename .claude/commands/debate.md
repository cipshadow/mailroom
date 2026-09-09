---
name: debate
description: Run a multi-round deliberation between reviewers. Unlike /panel (which synthesizes), /debate has reviewers respond to each other's arguments across rounds until tensions resolve or reach acknowledged stalemate.
user_invocable: true
model: sonnet
---

# Debate Review

Orchestrate a structured deliberation between reviewer agents. Reviewers don't just give feedback in parallel—they engage with each other's perspectives, challenge each other's recommendations, and work toward resolution (or acknowledged stalemate).

## When to Use /debate vs /panel

| Use | When |
|-----|------|
| `/panel` | You want multiple perspectives synthesized. Fast. Tensions surfaced for you to decide. |
| `/debate` | You want reviewers to actually argue it out. More thorough. Tensions may resolve through deliberation. |

**Choose /debate when:**
- The piece is high-stakes and worth the extra rounds
- You want to see how perspectives hold up under challenge
- You suspect some tensions might resolve if reviewers engaged each other
- You want proposals and compromises, not just "you decide"

**Choose /panel when:**
- You want comprehensive feedback quickly
- You're comfortable resolving tensions yourself
- Time/tokens are a concern

## The Deliberation Flow

### Round 1: Initial Positions

Same as /panel—all reviewers analyze the draft independently.

### Round 2: Challenges

The moderator identifies tensions and sends challenges to involved reviewers.

### Round 3: Responses

Reviewers respond in character. They may:

- **Concede** — "On reflection, the detail does earn its place. I withdraw."
- **Hold** — "The momentum problem remains. Even good details hurt here."
- **Propose** — "Keep the first image, cut the extended list. Satisfies both."

### Round 4: Resolution

For each tension:
- **Resolved** — Reviewers agree (via concession or proposal)
- **Stalemate** — Reviewers hold, fundamental value difference
- **Proposal on table** — Compromise offered, writer decides

The moderator may run additional rounds if proposals generate new discussion, but caps at 4 rounds.

## Panel Selection for Debate

Debate is most valuable when the panel includes natural tensions:

| Pairing | Tension Type | Good For |
|---------|--------------|----------|
| hemingway + sedaris | Economy vs. Specificity | Deciding what earns its length |
| mom + hitchcock | Clarity vs. Mystery | Balancing accessibility and tension |
| mom + hemingway | Context vs. Brevity | What explanation is necessary |
| sorkin + sedaris | Momentum vs. Observation | Pacing of descriptive passages |
| sorkin + vonnegut | Speed vs. Depth | When to slow for character |
| asshole + sedaris | Rigor vs. Voice | Tone of argument pieces |

**Recommendation:** Include at least one natural tension pair in your panel.

## Token Economics

Debate is more expensive than panel:

| Phase | Approximate Tokens |
|-------|-------------------|
| Round 1: Initial reviews | 4-6 reviewers × ~8K = 32-48K |
| Round 2: Challenges | 3-4 tensions × 2 reviewers × ~4K = 24-32K |
| Round 3: Responses | Same reviewers × ~3K = 18-24K |
| Round 4: Resolution (if needed) | ~10K |
| Synthesis | ~8K |
| **Total** | ~90-120K tokens |

For high-stakes pieces, worth it. For routine editing, use /panel.
