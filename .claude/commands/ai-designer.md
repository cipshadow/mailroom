---
name: ai-designer
description: Push Claude past generic AI-slop design (purple gradients, text-left/graphic-right, safe symmetric layouts) toward bold, distinctive, studio-quality output. Use whenever the user asks to build or redesign a landing page, app UI, game, or any visual product — especially when they want it to feel unique, premium, or "not obviously AI-generated." Invoke with /ai-designer or automatically when a design/UI-building request would otherwise default to bland output.
user_invocable: true
model: opus
---

# AI Designer

## Why this exists

LLMs are next-token predictors trained to please everyone, so left alone they make the safest, most average design choice at every step: purple gradient, text-left, CTA-below, graphic-right. Great design does the opposite — it takes risks and creates an emotional reaction. Getting there from an LLM requires deliberately injecting variety, judging output from outside its own context, and then cutting back what it over-adds. This skill is a runnable version of that process: Discover → Define → Deliver.

Don't just summarize this to the user — actually run the relevant stage(s) against their current design task.

## Stage 1: Discover — find a direction worth building

Pick ONE of these, based on what the user already told you:

**They have no direction yet → generate one with them (don't invent it for them):**
1. Ask them for a burst of high-level, low-detail design-language ideas (video game HUD, industrial control panel, isometric city, brutalist print, etc.) — generate 10-15 one-line options yourself if they want a starting menu.
2. Have them react: which ones pull them in, which specific details do they like/dislike. Push for specifics ("clicky tactile buttons, not skeuomorphic — that reads tacky").
3. Iterate on the direction using their taste notes until it feels distinct and theirs.
4. Turn the refined direction into one concise build prompt (concrete visual references, not adjectives like "modern" or "clean").

**They want max variety / have no reference in mind → seed-string technique:**
Use this exact structure so the model can't fall back on "random-sounding but actually average" choices:
```
Build [X]. Follow this procedure:
1. Generate a long, random alphanumeric string using a shell script.
2. Define the creative direction (color scheme, layout, typography) based on
   that string — look for subpatterns, repeated characters, anything that
   sparks an idea, not just the surface value.
3. Use your judgment to bring that direction to life and make it look great.
4. Don't reveal the string anywhere in the design — it's only your private
   inspiration.
```

**They already have a concrete reference in mind → ambitious prompting:**
Write the reference directly into the build prompt as something to interpret, not copy: "each section should feel like a still from a video game, yet function as a landing page" / "isometric living 3D city where features are neighborhoods" / "radically asymmetric, dissonant colors, uncomfortable negative space — break the rules but keep it working." Vague asks for "unique" or "random" don't work — an LLM can't act randomly on its own, it needs an actual reference to interpret.

If an idea sounds like it might be bad, try it anyway — that's usually the signal it's worth testing. If it fails, note it and revisit with a newer/different model later rather than discarding it for good.

## Stage 2: Define — give the direction a real identity

Once there's a first working draft, don't ask the same agent/context to judge and improve its own work — it isn't objective about its own decisions. Instead, run a critic loop:

```
Improve this design. Use a [smaller/cheaper model] subagent as a design critic.

At each iteration:
1. Capture a screenshot of the current design.
2. Invoke the critic in a FRESH context — give it only the screenshot, not
   the code, implementation details, or past critiques.
3. Ask it to: name the aesthetic being attempted, imagine how a top design
   studio would execute that exact aesthetic, and list the biggest gaps
   between the two.
4. Ask it for a score out of 10 against that studio-quality bar.

Critic guidance to include in its prompt:
- Judge both overall composition AND fine detail.
- Actively penalize anything that reads as overdone, excessive, or
  generically AI-generated.
- Be specific and concrete, never vague ("tighten the type scale in the
  hero," not "make it feel more polished").
- Be opinionated — favor bold calls over safe ones.

Keep iterating until the critic independently scores 9/10 or higher.
Do not tell the critic that 9/10 is the bar — keep its scoring objective.
Use the identical critic prompt every iteration. Cap it at [5-6] iterations
so it doesn't loop forever if it stalls.
```

Notes when running this:
- Prefer a bigger/pricier model as the critic and a fast, capable model as the implementer — the critic only runs occasionally, so its cost stays small.
- If available, give the critic 1-2 reference images (competitor screenshots, moodboard, concept art) as a quality floor to rank against — never as something to copy outright.
- Keep the critic's rubric objective and comparison-based ("rank these against these reference images") rather than subjective ("is this beautiful and not AI-slop") — subjective rubrics produce wildly inconsistent scores run to run.

**Enrich with real media instead of code-only gradients/shapes.** Coding agents default to CSS gradients and shape primitives because they're easy; push for actual generated imagery instead:
- If the agent has built-in image generation (Codex, Antigravity, Grok Build), tell it to use it — it usually won't unless told.
- If only Claude Code is available but the user has a ChatGPT subscription: "Use the Codex CLI to generate images, billing my ChatGPT subscription, not an API key."
- Otherwise: give the agent an OpenAI or Gemini API key with a tight spend cap, and have it write the key to a gitignored `.env.agents` file (and note in CLAUDE.md/AGENTS.md that it's dev-only and must never ship in the product) rather than pasting it inline repeatedly.

**For motion**, use a model aggregator like fal.ai with one API key so the agent can pick the right video model itself:
- *Layerable animated graphics:* generate a looping clip on a solid background, then remove the background (chroma key or a video matting model) so it composites anywhere in the UI. For effects like glass refraction, render the clip over the real page background first so the refraction bakes in, then matte the background out.
- *Fluid state transitions:* generate an interpolated clip between two keyframe images (e.g. two product stills), then chain the final frame of each clip as the seed for the next transition, so a sequence can be scrubbed frame-by-frame on scroll or swipe.

## Stage 3: Deliver — cut it down to something premium

AI-generated output almost always needs subtraction, not addition. Once the direction and identity are solid, do an explicit pass to remove, not polish:

- Glows, gradients, or shadows that aren't doing compositional work
- Redundant labels/captions when the visual already communicates the point
- Custom-built components (buttons, inputs, toggles) that look worse than the platform's native equivalents — prefer native components unless the custom one is clearly better
- Decorative elements with no functional or emotional purpose

Then do a final "AI tell" pass — flag and fix generic patterns that read as machine-made: repetitive card/section rhythm, the default purple/blue gradient, over-explained copy, filler microcopy, symmetric-everything layouts. State the specific fix per element ("drop the glow on the progress bar, tighten the button copy from 'Get Started Now!' to 'Start'"), don't just say "make it less AI."

Prompt template for this pass:
```
This design is doing too much. Simplify it:
- Cut anything that isn't adding value — count every glow, gradient,
  label, and container and justify keeping it.
- Replace custom components with native platform ones unless the custom
  version is clearly better.
- Point out anything that reads as a generic AI design pattern and fix it
  specifically.
Aim for restraint over decoration — less on screen should communicate more.
```

## Quick reference

| Situation | Do this |
|---|---|
| Blank page, no idea yet | Discover: co-develop a direction with the user |
| Want guaranteed non-generic output fast | Discover: seed-string technique |
| Already have a strong reference in mind | Discover: ambitious prompting, straight to build |
| First draft feels flat/generic | Define: critic subagent loop |
| Output looks code-generated (flat gradients/shapes) | Define: image/video generation |
| Design feels cluttered or "AI-ish" | Deliver: subtractive edit + AI-tell pass |

Source: "How to turn your AI into a world-class designer," Anshu Chimala, Lenny's Newsletter, Sep 2026.
