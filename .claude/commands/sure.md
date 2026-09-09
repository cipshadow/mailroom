---
model: sonnet
description: Confidence check with human checkpoint. Assesses honestly, waits for your input, then improves and reassesses.
---

# Confidence calibration (multi-step)

## Step 1: Assess (use a subagent)

Spawn a fresh agent to review the work you just did. The agent should approach the output cold, without anchoring bias. It must:

1. **Rate confidence (0-100)** that the work is correct, complete, and will achieve its goal
2. **Explain honestly** what drives the score down (be specific, not generic)
3. **List 1-3 actions** that would raise confidence toward 95, and what uncertainty each eliminates

Present the agent's assessment to the user verbatim.

## Step 2: Wait

Tell the user: "Let me know which of these to pursue, or redirect me if something else worries you more."

**Stop here. Do not proceed until the user replies.**

## Step 3: Execute

Based on the user's reply, do the improvements they approved or redirected you toward.

## Step 4: Reassess honestly

After executing, state:
- **New confidence level** (be honest; it's fine if it's not 95)
- **What changed** (concrete delta, not vague "improved quality")
- **Remaining risks** the user should know about

Do not inflate the score to look good. If execution only moved confidence from 68 to 78, say 78.
