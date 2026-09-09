---
name: pretty-slides
description: "Create a polished HTML slide deck from a Google Doc, URL, pasted content, or existing HTML. Offers 6 visual styles from glassmorphism to immersive single-file decks with per-slide animation lifecycles."
argument-hint: [Google Doc URL, web URL, file path, or paste content directly]
user-invocable: true
model: sonnet
---

# SLIDES SKILL

Generates a polished slide deck from source content. Always ask the user which style they want before building.

## Style selection

Before generating slides, present the available styles and ask the user to pick one:

> Which visual style do you want for this deck?
>
> 1. **Glassmorphism** — Animated floating orbs with frosted-glass cards. Premium and modern.
> 2. **Particles** — Three.js particle background with mouse reactivity. Big slide numbers as design element.
> 3. **White** — Clean light theme, horizontal slide navigation. Best for data-heavy content and printing.
> 4. **Immersive** (default) — Full environmental deck: subtle grid, glow orbs, cursor-reactive glow, pill nav with progress ring, per-slide animation lifecycles. Zero dependencies. The flagship.
> 5. **Dark** — Same engine as Immersive but noir palette: ember orange + cyan. Dramatic and high-contrast.
> 6. **Midnight** — React + framer-motion + Vite. Beat system for progressive reveals. Spring physics. Requires build step.
>
> Or I can generate **one demo slide in all 6 styles** so you can compare before committing.

If the user says "demo" or "show me all" or "compare", generate a single HTML file with one representative slide rendered in all 6 styles (tabbed or sectioned), open it in the browser, and let them pick.

If the user doesn't specify, default to **Immersive** (style 4).

---

## Navigation (all styles)

**Every style uses horizontal slide-by-slide navigation.** No style is a vertical scroll page. All 6 styles share:
- Arrow keys (left/right), Space (forward), Home/End
- Dot indicators with active state
- Touch swipe (50px threshold)
- Hash deep links (`#3` goes to slide 3)
- Directional transitions (translateX with momentum)

The only difference is implementation: Immersive/Dark inline the nav JS; Glassmorphism/Particles/White use external `slides.js`; Midnight uses React state.

---

### Reference decks

If the user provides an existing HTML deck as a reference, read it and match its structure, component patterns, and CSS variable naming. This is the fastest way to produce consistent output across a team.

If no reference is provided, build from the spec in the Immersive section below.

> **Tip:** Provide an existing HTML deck as a reference for consistent output across a team.

---

## CSP COMPATIBILITY

**Immersive (default):** Single self-contained HTML file. Inline `<style>` and `<script>` are both fine for local use and direct file sharing. Google Fonts via `<link>` is OK. If your deployment target enforces CSP (no inline scripts), split JS into an external `.js` file.

**Multi-file styles (Glassmorphism, Particles, White):** Must be CSP-compatible for strict hosting environments:
- **NO inline `<script>` tags.** All JS in external `.js` files loaded via `<script src="./slides.js"></script>`
- **NO `@import url(...)` for external fonts.** Use system font stack: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif`
- **NO external CDN scripts** unless downloaded locally first
- **Inline `<style>` is OK** (CSP allows `style-src 'unsafe-inline'`)
- Always generate a `slides.js` file alongside multi-file HTML styles

### slides.js (navigation for multi-file HTML styles)

Upgraded with hash-based deep links, directional transitions, MutationObserver entrance triggers, and Home/End support.

```javascript
(function() {
  var slides = document.querySelectorAll('.slide');
  var dotsContainer = document.getElementById('dots');
  var current = 0;
  var direction = 1; // 1 = forward, -1 = backward

  // Build dots
  for (var i = 0; i < slides.length; i++) {
    var d = document.createElement('div');
    d.className = 'dot' + (i === 0 ? ' active' : '');
    d.setAttribute('data-index', i);
    d.addEventListener('click', function() {
      goTo(parseInt(this.getAttribute('data-index')));
    });
    dotsContainer.appendChild(d);
  }

  // MutationObserver: trigger entrance animations when .active is added
  var observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(m) {
      if (m.type === 'attributes' && m.attributeName === 'class') {
        var el = m.target;
        if (el.classList.contains('active') && el.classList.contains('slide')) {
          // Reset staggered children so animations replay
          var animated = el.querySelectorAll('.anim');
          animated.forEach(function(child) {
            child.style.animation = 'none';
            child.offsetHeight; // force reflow
            child.style.animation = '';
          });
        }
      }
    });
  });
  slides.forEach(function(s) {
    observer.observe(s, { attributes: true });
  });

  function goTo(index) {
    if (index < 0 || index >= slides.length) return;
    direction = index > current ? 1 : -1;

    // Directional exit
    slides[current].style.transform = 'translateX(' + (direction * -30) + 'px)';
    slides[current].style.opacity = '0';
    slides[current].classList.remove('active');
    dotsContainer.children[current].classList.remove('active');

    current = index;

    // Directional entrance
    slides[current].style.transform = 'translateX(' + (direction * 30) + 'px)';
    slides[current].style.opacity = '0';
    slides[current].classList.add('active');
    dotsContainer.children[current].classList.add('active');

    // Animate in
    requestAnimationFrame(function() {
      requestAnimationFrame(function() {
        slides[current].style.transform = 'translateX(0)';
        slides[current].style.opacity = '1';
      });
    });

    // Update hash (no scroll)
    history.replaceState(null, '', '#' + (current + 1));
  }

  // Read hash on load (deep link support)
  function readHash() {
    var hash = parseInt(location.hash.replace('#', ''), 10);
    if (hash > 0 && hash <= slides.length && hash - 1 !== current) {
      // Jump without transition on initial load
      slides[current].classList.remove('active');
      dotsContainer.children[current].classList.remove('active');
      current = hash - 1;
      slides[current].classList.add('active');
      dotsContainer.children[current].classList.add('active');
    }
  }
  readHash();
  window.addEventListener('hashchange', readHash);

  // Navigation buttons
  document.getElementById('prev-btn').addEventListener('click', function() { goTo(current - 1); });
  document.getElementById('next-btn').addEventListener('click', function() { goTo(current + 1); });

  // Keyboard: arrows, space, Home, End
  document.addEventListener('keydown', function(e) {
    if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); goTo(current + 1); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); goTo(current - 1); }
    if (e.key === 'Home') { e.preventDefault(); goTo(0); }
    if (e.key === 'End') { e.preventDefault(); goTo(slides.length - 1); }
  });

  // Touch swipe
  var touchStartX = 0;
  document.addEventListener('touchstart', function(e) { touchStartX = e.touches[0].clientX; });
  document.addEventListener('touchend', function(e) {
    var diff = touchStartX - e.changedTouches[0].clientX;
    if (Math.abs(diff) > 50) { diff > 0 ? goTo(current + 1) : goTo(current - 1); }
  });
})();
```

**Slide CSS for directional transitions** (add to all HTML variants):
```css
.slide {
  transition: transform 0.35s ease, opacity 0.35s ease;
}
```

---

## COLOUR SYSTEM

Consistent across all 6 styles:

```
blurple:   #635BFF   (Stripe primary)
blurpleHi: #8B85FF   (highlight)
orange:    #FF5A00   (emphasis, trends)
green:     #34D399   (positive)
blue:      #3B9EFF   (secondary)
lavender:  #a78bfa   (accent)
red:       #ef4444   (negative)
amber:     #f59e0b   (warning/neutral)
cyan:      #06b6d4   (info)
sub:       #cbd5e1   (subtitle text)
dim:       #94a3b8   (muted text)
card:      rgba(255,255,255,0.04)  (dark variants)
border:    rgba(255,255,255,0.08)  (dark variants)
```

---

## TYPOGRAPHY

- Font: system font stack (NO Google Fonts)
- Slide titles: `clamp(32px, 4vw, 42px)`, 700 weight, #fff
- Title slide: `clamp(40px, 5vw, 56px)`, 800 weight
- Eyebrow / section labels (uppercase caps): `clamp(11px, 1vw, 13px)`, uppercase, letter-spacing 0.12em, dim colour — exception to the floor (decorative labels only)
- Subtitles: `clamp(16px, 2vw, 20px)`, 0.95 opacity
- Card titles: `clamp(16px, 2vw, 20px)`, 600 weight
- Card body: `clamp(16px, 1.6vw, 20px)`, 0.95 opacity
- Stat numbers: `clamp(36px, 5vw, 52px)`, 800 weight
- Monospace numbers: use class `.num` with `font-variant-numeric: tabular-nums`

**All variants use `clamp()` for responsive sizing.** Fixed `px` values are fallbacks only.

### Font size floor (non-negotiable)

**Body text minimum is `16px`.** Any inline `font-size` on readable content must use `clamp(16px, 1.6vw, 20px)` or larger. The reference size is a subtitle like "A PM's working setup with Claude Code" — all body copy must be at least that size on screen.

Exceptions (UI chrome only, not readable content):
- Eyebrow / section labels: `clamp(11px, 1vw, 13px)` — uppercase, muted, decorative
- Monospace code in terminal/file-tree blocks: `clamp(13px, 1.3vw, 15px)` — code context
- Nav bar, dots, counter, slide labels: fixed small sizes are fine (not content)

**Never use `font-size` below 13px on any text the audience needs to read.** If content doesn't fit at 16px+, split the slide or trim the content — never shrink the font.

---

## GRAPHIC COMPONENTS (Glassmorphism, Particles, White styles)

Use these when the source content has data, metrics, trends, or comparisons. All implemented as inline SVG + CSS animations in a separate `charts.js` file.

### 1. SVG Line Chart (draw-in animation)

For time series, trends, cohort comparisons. Lines animate in via `stroke-dashoffset`.

```javascript
// In charts.js - call after DOM ready
function drawLineChart(containerId, config) {
  // config: { width, height, series: [{ data: [], color, label, strokeWidth }], xLabels: [], yMin, yMax, yLabels: [] }
  var W = config.width || 700, H = config.height || 280;
  var PAD = { t: 24, r: 140, b: 40, l: 50 };
  var cw = W - PAD.l - PAD.r, ch = H - PAD.t - PAD.b;
  var nx = function(i) { return PAD.l + (i / (config.xLabels.length - 1)) * cw; };
  var ny = function(v) { return PAD.t + ch - ((v - config.yMin) / (config.yMax - config.yMin)) * ch; };

  // Build SVG with grid lines, axes, animated paths, end-labels, dots
  // Animate with: el.style.strokeDasharray = len; el.style.strokeDashoffset = len;
  // setTimeout: el.style.transition = 'stroke-dashoffset 1.4s ease'; el.style.strokeDashoffset = 0;
}
```

Key patterns:
- Grid lines: `stroke: rgba(255,255,255,0.05)`, dashed `3,4`
- Baseline (e.g. 100 index): slightly brighter `rgba(255,255,255,0.12)`, solid
- End-of-line labels: series name + growth stat, collision-resolved (min 22px gap)
- Callout bubbles: rounded rect with coloured border, stat text inside, dashed connector line to data point
- Glow effect on latest data: `<filter id="glow"><feGaussianBlur stdDeviation="3"/></filter>`
- Dots at each data point: `r=3` normally, `r=6` for current quarter, dark stroke

### 2. SVG Bar Chart / Stacked Bar

For mix comparisons, category breakdowns.

- Horizontal or vertical bars
- Animated width/height growth via CSS transition
- Labels inside or beside bars
- Legend below with coloured line + label + growth percentage
- Percentage labels at end of bars

### 3. SVG Donut / Ring Chart

For share/mix visualisation.

- `stroke-dasharray` on circle for segments
- Animated from 0 to target via CSS transition
- Big number in centre
- Legend beside

### 4. Hero Stat Comparison (before -> after)

For dramatic metric changes. Pattern from Kelly's AI revenue share slide.

```html
<div class="hero-compare">
  <div class="hero-stat hero-stat-from">
    <div class="hero-num" style="color: rgba(148,163,184,0.75);">1.9%</div>
    <div class="hero-label">Jan 2025</div>
  </div>
  <div class="hero-arrow">
    <svg><!-- gradient arrow, animated pathLength --></svg>
    <div class="hero-arrow-label">15 months</div>
  </div>
  <div class="hero-stat hero-stat-to">
    <div class="hero-num" style="color: #a78bfa; filter: drop-shadow(0 0 24px rgba(167,139,250,0.55));">4.2%</div>
    <div class="hero-label">March 2026</div>
  </div>
</div>
```

CSS:
```css
.hero-compare { display: flex; align-items: center; justify-content: center; gap: 40px; margin: 16px 0 32px; }
.hero-stat { text-align: center; min-width: 120px; }
.hero-num { font-size: clamp(3.2rem, 6vw, 4.8rem); font-weight: 900; letter-spacing: -0.04em; line-height: 1; }
.hero-label { font-size: 11px; color: #94a3b8; margin-top: 10px; letter-spacing: 0.1em; text-transform: uppercase; }
```

Animate: fade-in the "from" stat, draw the arrow (gradient from dim to accent), fade-in the "to" stat. All via CSS keyframes with delays.

### 5. Variance Table (P&L style)

For financial metrics with actuals, vs budget, YoY.

```html
<div class="var-table">
  <div class="var-header">
    <span>Metric</span><span>Actual</span><span>vs. Budget</span><span>YoY</span>
  </div>
  <div class="var-row">
    <span class="var-label">Revenue</span>
    <span class="var-actual">$8,956M</span>
    <span class="var-badge var-pos">+4.9%</span>
    <span class="var-badge var-pos">+31.6%</span>
  </div>
</div>
```

CSS:
```css
.var-table { width: 100%; }
.var-header { display: grid; grid-template-columns: 2fr 1.1fr 1fr 1fr; gap: 8px; padding: 8px 16px; border-bottom: 1px solid rgba(255,255,255,0.08); }
.var-header span { font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #94a3b8; }
.var-row { display: grid; grid-template-columns: 2fr 1.1fr 1fr 1fr; gap: 8px; padding: 11px 16px; border-bottom: 1px solid rgba(255,255,255,0.08); }
.var-actual { font-size: 14px; font-weight: 700; }
.var-pos { color: #34d399; font-weight: 700; font-size: 13px; }
.var-neg { color: #f87171; font-weight: 700; font-size: 13px; }
.var-neutral { color: #94a3b8; font-weight: 600; font-size: 13px; }
/* Bold rows (totals): background rgba(255,255,255,0.025) */
/* Divider rows: height 1px, margin 6px 16px, background rgba(255,255,255,0.22) */
```

### 6. Slide Header Pattern (eyebrow + title + subtitle)

All slides should use this pattern:

```html
<div class="slide-eyebrow">Q1 FY26 · Topic</div>
<h2 class="slide-title">Title with <span class="text-accent">coloured emphasis</span></h2>
<div class="slide-subtitle">Supporting context line</div>
```

CSS:
```css
.slide-eyebrow { font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: #94a3b8; margin-bottom: 16px; }
.text-accent { color: #635BFF; }
.text-gradient { background: linear-gradient(135deg, #a78bfa, #635bff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
```

---

## BACKGROUND VARIANTS (HTML styles)

### Style 1: Glassmorphism (`glassmorphism.html`)

3 orbs with looping keyframe animations (25-35s, travel 10-20vw/vh, scale 0.92-1.1). Cards get `backdrop-filter: blur(20px)`.

```css
#bg-gradient {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0;
  background: linear-gradient(135deg, #0a2540 0%, #0d1117 50%, #0a1628 100%);
  overflow: hidden;
}
.glass-orb { position: absolute; border-radius: 50%; filter: blur(100px); }
.glass-orb:nth-child(1) { width: 500px; height: 500px; top: -10%; left: 10%; background: rgba(99,91,255,0.25); animation: orbFloat1 30s ease-in-out infinite; }
.glass-orb:nth-child(2) { width: 400px; height: 400px; bottom: -5%; right: 15%; background: rgba(167,139,250,0.18); animation: orbFloat2 25s ease-in-out infinite; }
.glass-orb:nth-child(3) { width: 300px; height: 300px; top: 40%; right: 30%; background: rgba(6,182,212,0.1); animation: orbFloat3 35s ease-in-out infinite; }
@keyframes orbFloat1 { 0% { transform: translate(0,0) scale(1); } 25% { transform: translate(15vw,10vh) scale(1.1); } 50% { transform: translate(5vw,20vh) scale(0.95); } 75% { transform: translate(-10vw,5vh) scale(1.05); } 100% { transform: translate(0,0) scale(1); } }
@keyframes orbFloat2 { 0% { transform: translate(0,0) scale(1); } 25% { transform: translate(-12vw,-8vh) scale(1.08); } 50% { transform: translate(-20vw,5vh) scale(0.92); } 75% { transform: translate(-5vw,-15vh) scale(1.04); } 100% { transform: translate(0,0) scale(1); } }
@keyframes orbFloat3 { 0% { transform: translate(0,0) scale(1); } 25% { transform: translate(10vw,-12vh) scale(1.06); } 50% { transform: translate(-8vw,-8vh) scale(1.1); } 75% { transform: translate(15vw,5vh) scale(0.94); } 100% { transform: translate(0,0) scale(1); } }
```

HTML: `<div id="bg-gradient"><div class="glass-orb"></div><div class="glass-orb"></div><div class="glass-orb"></div></div>`

### Style 2: Three.js Particles (`particles.html`)

Download: `curl -o three.min.js https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js`
Three.js code in external `particles-bg.js`. 300 particles, additive blending, mouse-reactive.

### Shared: Staggered Animation Utilities

All HTML styles should include these utility classes. Elements with class `anim` auto-animate on slide entrance via the MutationObserver in `slides.js`.

```css
/* Staggered entrance delays — add class "anim" + "d1" through "d12" */
.anim {
  opacity: 0;
  transform: translateY(18px);
  animation: fadeUp 0.5s ease forwards;
}
@keyframes fadeUp { to { opacity: 1; transform: translateY(0); } }
@keyframes fadeLeft { to { opacity: 1; transform: translateX(0); } }
@keyframes fadeRight { to { opacity: 1; transform: translateX(0); } }
@keyframes scaleIn { to { opacity: 1; transform: scale(1); } }

.anim.from-left { transform: translateX(-24px); animation-name: fadeLeft; }
.anim.from-right { transform: translateX(24px); animation-name: fadeRight; }
.anim.from-scale { transform: scale(0.85); animation-name: scaleIn; }

/* Delay classes: d1=100ms, d2=200ms, ..., d12=1200ms */
.d1  { animation-delay: 0.1s; }
.d2  { animation-delay: 0.2s; }
.d3  { animation-delay: 0.3s; }
.d4  { animation-delay: 0.4s; }
.d5  { animation-delay: 0.5s; }
.d6  { animation-delay: 0.6s; }
.d7  { animation-delay: 0.7s; }
.d8  { animation-delay: 0.8s; }
.d9  { animation-delay: 0.9s; }
.d10 { animation-delay: 1.0s; }
.d11 { animation-delay: 1.1s; }
.d12 { animation-delay: 1.2s; }
```

Usage: `<div class="anim d3">This fades up after 300ms</div>`

### Shared: Print Stylesheet

Include in all HTML styles for clean printout:

```css
@media print {
  .slide { display: block !important; opacity: 1 !important; transform: none !important;
           page-break-after: always; break-inside: avoid; position: relative !important; }
  #bg-gradient, .glass-orb, #dots, #prev-btn, #next-btn, .nav-bar { display: none !important; }
  body { background: #fff !important; color: #1a1a2e !important; }
  .slide-title, .hero-num, .var-actual { color: #1a1a2e !important; }
  .text-accent, .text-gradient { color: #635BFF !important;
    -webkit-text-fill-color: #635BFF !important; background: none !important; }
}
```

---

### Style 3: Clean White (`white.html`)

Horizontal slide navigation with light theme. Same arrow-key/dot/swipe navigation as other styles. Best for data-heavy content and printing.

- Background: `#fff`, Text: `#1a1a2e`, Accent: `#635bff`
- Cards: `background: #fafafc; border: 1px solid #e8e8ed;`
- Layout: `max-width: 1100px`, centered, each slide is `position: fixed; inset: 0` with horizontal translateX transitions
- Tables with green/red variance badges
- Purple-bordered quote cards
- Uses same `slides.js` navigation pattern as other styles (arrow keys, dots, swipe, hash deep-links)
- Navigation bar: white background with `backdrop-filter: blur(10px)`, accent-coloured active dot
- **NOT a vertical scroll page.** All styles use horizontal slide-by-slide navigation.

---

## STYLE 4: Immersive (`immersive.html` — default)

Zero-dependency immersive deck. CSS-first animations with JS particle effects, squash-stretch physics, environmental atmosphere, and cursor-reactive glow. No libraries. **Reference:** provide your own immersive deck as a template for consistent styling.

### Design Philosophy

- **CSS handles 90% of animation** (keyframes, transitions, staggered delays)
- **JS handles physics-based effects** (particle bursts, cursor glow tracking, procedural SVG, count-up numbers)
- **Every slide has an environmental mood** (ambient particles, gradient shifts, subtle rain/glow, background glows)
- **Transitions feel physical** (squash on exit, stretch on enter, directional momentum)
- **MutationObserver drives per-slide lifecycle** — each slide's animation triggers on `.active` class add/remove, with clean reset when leaving
- **Single HTML file** — everything inline (styles in `<style>`, JS in `<script>`), no build step, shareable as-is

### Colour system

Use semantic color names with a full surface scale. The palette should feel alive, not corporate.

```css
:root {
  /* Background & surfaces (9-level scale) */
  --bg: #0c1210;
  --surface-900: #0c1210;
  --surface-800: #131d19;
  --surface-700: #1c2924;
  --surface-600: #2a3d35;
  --surface-500: #536e65;
  --surface-200: #a8c0b8;
  --surface-50: #f2f7f5;

  /* Accent colours (semantic names) */
  --accent-1: #22c55e;          /* primary accent (green/frog) */
  --accent-1-light: #4ade80;
  --accent-2: #2dd4bf;          /* secondary (teal/pond) */
  --accent-3: #826cff;          /* tertiary (purple/cape) */
  --accent-4: #fbbf24;          /* highlight (amber/lily) */
  --accent-5: #ff8c7a;          /* warm (coral) */

  /* Text hierarchy */
  --text-primary: #f2f7f5;
  --text-secondary: #a8c0b8;
  --text-muted: #6b8a80;

  /* Terminal */
  --term-bg: #0d1117;
  --term-border: #21262d;
}
```

**Adapt this palette to the content's brand.** The structure (bg, surfaces, 5 accents, text hierarchy) stays the same; swap the hex values.

### Font Stack

```css
font-family: 'Outfit', sans-serif;  /* body — load from Google Fonts via <link> */
code, .mono { font-family: 'Space Mono', monospace; }
```

For CSP-restricted environments, swap to system stack: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif`.

### Animation Classes (Shorthand)

Six entrance types + a continuous float. Elements start `opacity: 0` and animate on slide activation.

```css
@keyframes fadeUp    { from { opacity:0; transform:translateY(20px) } to { opacity:1; transform:translateY(0) } }
@keyframes fadeLeft  { from { opacity:0; transform:translateX(-20px) } to { opacity:1; transform:translateX(0) } }
@keyframes fadeRight { from { opacity:0; transform:translateX(20px) } to { opacity:1; transform:translateX(0) } }
@keyframes fadeIn    { from { opacity:0 } to { opacity:1 } }
@keyframes scaleIn   { from { opacity:0; transform:scale(0.85) } to { opacity:1; transform:scale(1) } }
@keyframes bounceIn  { from { opacity:0; transform:scale(0.6) rotate(-15deg) } to { opacity:1; transform:scale(1) rotate(0) } }
@keyframes float     { 0%,100% { transform:translateY(0) } 50% { transform:translateY(-8px) } }

/* Activate ONLY when parent .slide has .active */
.slide.active .au { animation: fadeUp 0.55s cubic-bezier(.22,.68,.36,1) forwards; opacity:0 }
.slide.active .al { animation: fadeLeft 0.5s ease forwards; opacity:0 }
.slide.active .ar { animation: fadeRight 0.5s ease forwards; opacity:0 }
.slide.active .af { animation: fadeIn 0.45s ease forwards; opacity:0 }
.slide.active .as { animation: scaleIn 0.5s cubic-bezier(.22,.68,.36,1) forwards; opacity:0 }
.slide.active .ab { animation: bounceIn 0.7s cubic-bezier(.34,1.56,.64,1) forwards; opacity:0 }
.slide.active .afloat { animation: float 3s ease-in-out infinite }

/* Delay utilities: .d1 through .d12 */
.d1{animation-delay:.1s}.d2{animation-delay:.2s}.d3{animation-delay:.3s}.d4{animation-delay:.4s}
.d5{animation-delay:.5s}.d6{animation-delay:.6s}.d7{animation-delay:.7s}.d8{animation-delay:.8s}
.d9{animation-delay:.9s}.d10{animation-delay:1s}.d11{animation-delay:1.1s}.d12{animation-delay:1.2s}
```

Usage: `<div class="au d3">Fades up after 300ms when slide activates</div>`

### Slide Structure

```html
<div class="slide" data-label="Slide Name" id="slide-N">
  <!-- Background layers (z-index: 0) -->
  <div class="bg-grid"></div>
  <div class="bg-glow" style="top:-20%; right:-10%; background: radial-gradient(circle, rgba(34,197,94,0.06) 0%, transparent 60%)"></div>

  <!-- Content (z-index: 1) -->
  <div class="slide-inner">
    <div class="au d1 label label-green">Eyebrow</div>
    <h1 class="au d2">Title with <span class="grad grad-accent1">gradient text</span></h1>
    <p class="au d3">Body text</p>
  </div>
</div>
```

**Background grid** (subtle repeating lines):
```css
.bg-grid {
  position: absolute; inset: 0; z-index: 0;
  background:
    repeating-linear-gradient(0deg, transparent, transparent 59px, rgba(34,197,94,0.025) 59px, rgba(34,197,94,0.025) 60px),
    repeating-linear-gradient(90deg, transparent, transparent 59px, rgba(34,197,94,0.025) 59px, rgba(34,197,94,0.025) 60px);
}
```

**Background glow orbs** (position 1-3 per slide with varying accent colours):
```css
.bg-glow {
  position: absolute; width: 700px; height: 700px; border-radius: 50%;
  pointer-events: none; z-index: 0; filter: blur(40px);
}
```

### Gradient Text

```css
.grad { -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; background-clip: text !important; display: inline; }
.grad-accent1 { background: linear-gradient(135deg, var(--accent-1-light), var(--accent-2)); }
.grad-accent3 { background: linear-gradient(135deg, var(--accent-3), var(--accent-2)); }
.grad-accent5 { background: linear-gradient(135deg, var(--accent-5), var(--accent-4)); }
```

### Component Library

**Labels (coloured eyebrow pills):**
```css
.label {
  display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: 0.18em;
  text-transform: uppercase; padding: 5px 12px; border-radius: 6px; margin-bottom: 18px;
}
.label-green { color: var(--accent-1); background: rgba(34,197,94,0.1); }
.label-accent3 { color: var(--accent-3); background: rgba(130,108,255,0.1); }
```

**Terminal mockup:**
```css
.terminal {
  background: var(--term-bg); border: 1px solid var(--term-border);
  border-radius: 12px; overflow: hidden; font-family: 'Space Mono', monospace;
  font-size: 13px; line-height: 1.7; width: 100%;
}
.terminal-bar { display: flex; align-items: center; gap: 7px; padding: 12px 16px; background: rgba(255,255,255,0.03); border-bottom: 1px solid var(--term-border); }
.terminal-dot { width: 11px; height: 11px; border-radius: 50%; }
.terminal-dot.r { background: #ff5f57; } .terminal-dot.y { background: #febc2e; } .terminal-dot.g { background: #28c840; }
.terminal-body { padding: 20px 22px; color: var(--text-secondary); }
.terminal-body .prompt { color: var(--accent-1); }
.terminal-body .cmd { color: var(--text-primary); }
.cursor-blink { display: inline-block; width: 8px; height: 16px; background: var(--accent-1); animation: blink 1s step-end infinite; vertical-align: text-bottom; }
@keyframes blink { 0%,100% { opacity:1 } 50% { opacity:0 } }
```

**File tree:**
```css
.file-tree {
  font-family: 'Space Mono', monospace; font-size: 13px; line-height: 2;
  color: var(--text-secondary); background: var(--surface-800);
  border: 1px solid var(--surface-700); border-radius: 12px; padding: 24px 28px;
}
.file-tree .dir { color: var(--accent-1); font-weight: 700; }
.file-tree .special { color: var(--accent-4); }
```

**Cards (hover-lift):**
```css
.card {
  background: var(--surface-800); border: 1px solid var(--surface-700);
  border-radius: 12px; padding: clamp(16px, 2vw, 24px);
  transition: transform 0.2s, box-shadow 0.2s;
}
.card:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
```

**Stat boxes:**
```css
.stat-box {
  text-align: center; background: var(--surface-800); border: 1px solid var(--surface-700);
  border-radius: 14px; padding: clamp(18px, 2vw, 28px) clamp(12px, 1.5vw, 20px);
}
.stat-val { font-size: clamp(28px, 3vw, 44px); font-weight: 900; }
.stat-lbl { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.1em; margin-top: 4px; }
```

**Styled table:**
```css
.styled-table { background: var(--surface-800); border: 1px solid var(--surface-700); border-radius: 14px; overflow: hidden; }
.styled-table th { background: rgba(255,255,255,0.02); padding: 14px 20px; text-align: left; font-size: 11px; font-weight: 700; color: var(--accent-1); text-transform: uppercase; letter-spacing: 0.1em; }
.styled-table td { padding: 14px 20px; font-size: 14px; line-height: 1.5; color: var(--text-secondary); }
.styled-table tr:not(:last-child) td { border-bottom: 1px solid var(--surface-700); }
```

**Blockquote:**
```css
.slide-quote {
  background: var(--surface-800); border-left: 3px solid var(--accent-5);
  border-radius: 0 12px 12px 0; padding: 20px 28px;
  font-size: 16px; font-style: italic; color: var(--text-secondary); line-height: 1.7;
}
```

**Split layout:**
```css
.split { display: flex; gap: clamp(32px, 4vw, 64px); align-items: center; width: 100%; }
.split-left { flex: 1; min-width: 0; }
.split-right { flex: 1; min-width: 0; }
```

### Environmental Effects

**Procedural rain** (80 drops, for dramatic/problem slides):
```css
.rain-container { position: absolute; inset: 0; z-index: 0; overflow: hidden; pointer-events: none; }
.raindrop { position: absolute; width: 2px; background: linear-gradient(to bottom, transparent, rgba(168,192,184,0.5)); top: -20px; }
@keyframes rainFall {
  0% { transform: translateY(-20px); opacity: 0; }
  10% { opacity: 0.6; }
  90% { opacity: 0.3; }
  100% { transform: translateY(100vh); opacity: 0; }
}
```
JS generation:
```javascript
var container = document.getElementById('rain-container');
for (var i = 0; i < 80; i++) {
  var drop = document.createElement('div');
  drop.className = 'raindrop';
  drop.style.cssText = 'left:' + (Math.random()*100) + '%;height:' + (25+Math.random()*40) + 'px;animation:rainFall ' + (1+Math.random()*0.8) + 's linear ' + (-(Math.random()*1.8)) + 's infinite;';
  container.appendChild(drop);
}
```

**SVG brain/node network** (for architecture/system slides):
- Central node + 4-8 outer nodes connected by curved SVG `<path>` elements
- Phased reveal: center first, then outer nodes stagger in with connection lines
- Node pulse animation: `r` and `opacity` oscillate via CSS keyframes
- Connection flow: `stroke-dasharray: 6 4; animation: connectionFlow 1.5s linear infinite`
- Final "workspace ring" appears last (dashed circle + label)
```css
@keyframes nodePulse { 0%,100% { r: 16; opacity: 1; } 50% { r: 18; opacity: 0.85; } }
@keyframes connectionFlow { 0% { stroke-dashoffset: 20; } 100% { stroke-dashoffset: 0; } }
```

**Celebration particles** (SVG circles with radial dispersion):
```javascript
function celebrate(svg, cx, cy, count) {
  var colors = ['#fbbf24','#4ade80','#2dd4bf','#826cff','#ff8c7a','#fff'];
  for (var i = 0; i < count; i++) {
    var c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    c.setAttribute('cx', cx); c.setAttribute('cy', cy);
    c.setAttribute('r', String(1.5 + Math.random() * 3.5));
    c.setAttribute('fill', colors[i % colors.length]);
    c.style.opacity = '0.9';
    var angle = (Math.PI * 2 / count) * i + (Math.random() - 0.5) * 0.8;
    var dist = 60 + Math.random() * 80;
    var tx = Math.cos(angle) * dist, ty = Math.sin(angle) * dist - 30;
    c.style.transition = 'transform 1.2s cubic-bezier(.22,.68,.36,1), opacity 1.5s ease-out';
    svg.appendChild(c);
    (function(el, dx, dy) {
      setTimeout(function() { el.style.transform = 'translate('+dx+'px,'+dy+'px)'; el.style.opacity = '0'; }, 30);
      setTimeout(function() { el.remove(); }, 1800);
    })(c, tx, ty);
  }
}
```

**TV-off CRT effect** (for video endings or dramatic exits):
```css
.tv-off-container { position: relative; }
.tv-off-overlay { position: absolute; inset: 0; z-index: 10; pointer-events: none; background: #000; opacity: 0; }
.tv-off-line {
  position: absolute; left: 0; right: 0; top: 50%; z-index: 11;
  height: 0; background: rgba(167,139,250,0.8); transform: translateY(-50%); pointer-events: none; opacity: 0;
  box-shadow: 0 0 15px rgba(167,139,250,0.6), 0 0 30px rgba(167,139,250,0.3);
}
.tv-off-container.off .tv-off-overlay { animation: tvOffBg 0.4s ease-in forwards; }
.tv-off-container.off .tv-off-line { animation: tvOffLine 0.6s ease-in-out forwards; }
.tv-off-container.off video { animation: tvOffShrink 0.3s ease-in forwards; }
@keyframes tvOffShrink { 0% { transform: scale(1); filter: brightness(1); } 100% { transform: scaleY(0.01); filter: brightness(2); } }
@keyframes tvOffBg { 0% { opacity: 0; } 50% { opacity: 0; } 100% { opacity: 1; } }
@keyframes tvOffLine { 0% { opacity: 0; height: 0; } 30% { opacity: 1; height: 3px; } 70% { opacity: 1; height: 3px; } 90% { opacity: 0.8; height: 1px; } 100% { opacity: 0; height: 0; } }
```

### Advanced JS Patterns

**MutationObserver per-slide lifecycle** (the core pattern — use for every slide with custom animation):
```javascript
(function() {
  var slide = document.getElementById('slide-N');
  if (!slide) return;
  var animated = false;

  function animate() { /* reveal sequence with setTimeout chains */ }
  function reset() { /* restore all elements to initial hidden state */ animated = false; }

  var observer = new MutationObserver(function() {
    if (slide.classList.contains('active') && !animated) { animated = true; animate(); }
    else if (!slide.classList.contains('active')) { reset(); }
  });
  observer.observe(slide, { attributes: true, attributeFilter: ['class'] });
  if (slide.classList.contains('active')) { animated = true; animate(); }
})();
```

**Number count-up** (cubic ease-out):
```javascript
var target = 233, duration = 1200, start = performance.now();
function tick(now) {
  var progress = Math.min((now - start) / duration, 1);
  var eased = 1 - Math.pow(1 - progress, 3);  // ease-out cubic
  counter.textContent = Math.round(eased * target);
  if (progress < 1) requestAnimationFrame(tick);
}
requestAnimationFrame(tick);
```

**Arc jump physics** (for hopping/moving elements between positions):
```javascript
function moveFrog(targetLeft, targetTop, size) {
  // Phase 1: Jump up to peak (0-300ms)
  el.style.transition = 'left 0.4s ease-out, top 0.25s cubic-bezier(.13,.76,.45,1)';
  el.style.left = midLeft + 'px';
  el.style.top = (targetTop - 40) + 'px';  // arc peak
  el.style.transform = 'scaleX(1.15) scaleY(0.85)';  // squash

  // Phase 2: Land (300-650ms)
  setTimeout(function() {
    el.style.transition = 'left 0.35s ease-in, top 0.35s cubic-bezier(.55,.09,.68,.53)';
    el.style.left = targetLeft + 'px';
    el.style.top = targetTop + 'px';
    el.style.transform = 'scaleX(1.12) scaleY(0.88)';  // stretch on land
  }, 300);

  // Phase 3: Settle (650ms+)
  setTimeout(function() {
    el.style.transition = 'transform 0.2s ease-out';
    el.style.transform = 'scaleX(1) scaleY(1)';
  }, 650);
}
```

**Cursor glow** (smooth lerp, disabled on touch):
```javascript
if (!window.matchMedia('(pointer: coarse)').matches) {
  var glow = document.getElementById('cursorGlow');
  var mx = 0, my = 0, gx = 0, gy = 0;
  document.addEventListener('mousemove', function(e) { mx = e.clientX; my = e.clientY; });
  (function tick() {
    gx += (mx - gx) * 0.08;  // lerp factor
    gy += (my - gy) * 0.08;
    glow.style.left = gx + 'px';
    glow.style.top = gy + 'px';
    requestAnimationFrame(tick);
  })();
}
```

HTML: `<div id="cursorGlow" style="position:fixed;width:400px;height:400px;border-radius:50%;pointer-events:none;z-index:0;background:rgba(74,222,128,0.06);mask-image:radial-gradient(circle,black 0%,transparent 70%);-webkit-mask-image:radial-gradient(circle,black 0%,transparent 70%);transform:translate(-50%,-50%);"></div>`

**File tree cascade** (lines appear one by one):
```javascript
var lines = slide.querySelectorAll('.tree-line');
lines.forEach(function(line, i) {
  setTimeout(function() {
    line.style.opacity = '1';
    line.style.transform = 'translateY(0)';
  }, 200 + i * 120);  // 120ms stagger
});
```

**Table row cascade** (rows slide in from left):
```javascript
rows.forEach(function(row, i) {
  row.style.opacity = '0'; row.style.transform = 'translateX(-16px)';
  setTimeout(function() {
    row.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    row.style.opacity = '1'; row.style.transform = 'translateX(0)';
  }, 300 + i * 150);
});
```

**Timeline fill + staggered items:**
```javascript
fill.style.width = '100%';  // CSS transition handles the animation
items.forEach(function(item, i) {
  setTimeout(function() { item.style.opacity = '1'; item.style.transform = 'translateY(0)'; }, 300 + i * 400);
});
```

**Orbital ring** (3-node cycle with rotating dashed arcs):
```html
<svg viewBox="0 0 440 440">
  <g style="transform-origin: 220px 220px; animation: orbitSpin 30s linear infinite;">
    <!-- 3 arc segments with gradient strokes -->
    <path d="M220,50 A170,170 0 0,1 367,305" fill="none" stroke="url(#ringG1)" stroke-width="2" stroke-dasharray="6 10" opacity="0.45"/>
    <!-- ... -->
  </g>
  <!-- 3 solid circles masking the ring at node positions -->
  <circle cx="220" cy="50" r="30" fill="#0c1210" stroke="rgba(34,197,94,0.5)" stroke-width="2"/>
  <!-- Emoji or icon text centered in circles -->
  <text x="220" y="52" text-anchor="middle" dominant-baseline="central" font-size="28">🚀</text>
</svg>
```
```css
@keyframes orbitSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
```

**Per-slide audio** (with fade-out on exit):
```javascript
var audio = document.createElement('audio');
audio.loop = true; audio.volume = 0.3; audio.src = 'ambient.mp3';

function fadeOut() {
  var vol = audio.volume;
  var fade = setInterval(function() {
    vol -= 0.05;
    if (vol > 0.05) { audio.volume = vol; }
    else { audio.pause(); audio.volume = 0.3; clearInterval(fade); }
  }, 80);
}
```

### Navigation System

**Bottom bar** with slide label, pill-shaped dots, counter, progress ring, and branding:

```css
.bottom-bar {
  position: fixed; bottom: 0; left: 0; right: 0; height: 52px;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 2.5rem; background: rgba(12,18,16,0.9);
  backdrop-filter: blur(14px); border-top: 1px solid var(--surface-700); z-index: 100;
}
.dots { display: flex; gap: 5px; align-items: center; }
.dot { height: 10px; border-radius: 5px; cursor: pointer; transition: all 0.3s; background: var(--surface-600); width: 10px; }
.dot.active { width: 28px; background: var(--accent-1); box-shadow: 0 0 8px rgba(34,197,94,0.4); }
```

**Circular prev/next buttons:**
```css
.nav-btn {
  position: fixed; top: 50%; transform: translateY(-50%);
  width: 44px; height: 44px; border-radius: 50%;
  border: 1px solid var(--surface-700); background: rgba(12,18,16,0.9);
  backdrop-filter: blur(10px); color: var(--accent-1);
  cursor: pointer; font-size: 18px; display: flex; align-items: center; justify-content: center; z-index: 100;
}
.nav-btn:hover { border-color: var(--accent-1); background: rgba(34,197,94,0.1); box-shadow: 0 0 20px rgba(34,197,94,0.25); }
```

**Progress ring** (SVG circle with `stroke-dashoffset`):
```javascript
var circumference = 69.115;  // 2 * PI * r (r=11)
var progress = (current + 1) / total;
document.getElementById('progress-circle').style.strokeDashoffset = circumference * (1 - progress);
```

**Directional slide transitions:**
```javascript
function goTo(i) {
  var goingForward = i > current;
  slides[current].classList.remove('active');
  slides[current].style.transform = goingForward ? 'translateX(-30px)' : 'translateX(30px)';
  current = i;
  slides[current].style.transform = goingForward ? 'translateX(30px)' : 'translateX(-30px)';
  slides[current].offsetHeight; // force reflow
  slides[current].classList.add('active');
  slides[current].style.transform = '';
  location.hash = current;
}
```

### Click Preview Overlay

For embedded demos, videos, or iframes within a slide:

```javascript
function togglePreview(type) {
  var overlay = document.getElementById('hover-preview');
  // Show full-screen overlay with iframe/video/image based on type
  // Close button + click-outside-to-dismiss
  overlay.style.display = 'block';
}
```

### Print Stylesheet

```css
@media print {
  * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
  html, body { width: 100%; height: auto; overflow: visible; }
  .slide {
    display: flex !important; position: relative !important;
    width: 100vw; height: 100vh;
    page-break-after: always; break-after: page;
  }
  .slide .au, .slide .al, .slide .ar, .slide .af, .slide .as, .slide .ab {
    animation: none !important; opacity: 1 !important; transform: none !important;
  }
  .nav-btn, .bottom-bar, .dl-btn { display: none !important; }
}
@page { size: landscape; margin: 0; }
```

### Selection Style

```css
::selection { background: rgba(34,197,94,0.3); }
```

### File Output

The immersive variant is a **single self-contained HTML file**. All CSS in `<style>`, all JS in `<script>`. No external dependencies except optional Google Fonts `<link>`. This is its key advantage: drop the file anywhere and it works.

---

## STYLE 5: Dark (`dark.html`)

Same engine as Immersive but with a noir palette. Swap the `:root` CSS variables:

```css
:root {
  --bg: #050507;
  --surface-900: #050507;
  --surface-800: #0d0d12;
  --surface-700: #18181f;
  --surface-600: #2a2a35;
  --surface-500: #5a5e6a;
  --surface-200: #c8cad0;
  --surface-50: #e8eaed;
  --accent-1: #ff6b3d;          /* ember instead of green */
  --accent-1-light: #ff8f6b;
  --accent-2: #06d6d6;          /* cyan */
  --accent-3: #635BFF;          /* blurple becomes tertiary */
  --accent-4: #fbbf24;
  --accent-5: #ff8c7a;
  --text-primary: #c8cad0;
  --text-secondary: #8a8e9a;
  --text-muted: #5a5e6a;
}
```

Cursor glow shifts to warm orange. Cards use deeper glass. Everything else (animation classes, components, navigation, JS patterns) stays identical since it all references CSS variables.

---

## STYLE 6: Midnight (`react/` — React + Framer Motion)

Premium variant with animated transitions, staggered reveals, and interactive charts. Requires Node.js.

### Scaffold

```bash
cd [output-dir]
mkdir react && cd react
npm create vite@latest . -- --template react
npm install framer-motion
```

### Project structure

```
react/
  src/
    App.jsx          # Main app with slide state machine
    components/
      Slide.jsx      # Slide wrapper with padding, centering
      SlideHeader.jsx  # Eyebrow + title + subtitle
      PLTable.jsx    # Animated P&L variance table
      LineChart.jsx  # SVG line chart with draw-in
      CohortChart.jsx  # SVG cohort chart
      HeroCompare.jsx  # Big stat -> arrow -> big stat
      DonutChart.jsx # Ring chart with animated segments
    data.js          # All figures in one place
    colors.js        # Colour constants
  index.html
  vite.config.js
```

### Key patterns from Kelly's deck

**Slide transitions:**
```jsx
<AnimatePresence mode="wait">
  <motion.div
    key={slide}
    initial={{ opacity: 0, x: 40 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: -40 }}
    transition={{ duration: 0.45 }}
  >
    <Slide>{/* content */}</Slide>
  </motion.div>
</AnimatePresence>
```

**Staggered row reveals:**
```jsx
<motion.div
  initial={{ opacity: 0, y: 14 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.45, ease: [0.4, 0, 0.2, 1] }}
>
```

**Number emphasis (scale pulse + sparkles):**
```jsx
<motion.span
  animate={{ scale: [1, 1, 1.5, 1.5, 1] }}
  transition={{ duration: 4.0, ease: 'easeInOut', times: [0, 0.25, 0.4, 0.85, 1] }}
>
```

**Gradient text:**
```jsx
style={{
  background: 'linear-gradient(135deg, #a78bfa, #635bff)',
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
}}
```

**Animated arrow (hero comparison):**
```jsx
<motion.path
  d="M 8,22 L 162,22"
  stroke="url(#gradient)" strokeWidth={2.5}
  initial={{ pathLength: 0 }}
  animate={{ pathLength: 1 }}
  transition={{ delay: 0.85, duration: 0.7 }}
/>
```

**Beat system (progressive reveals within a slide):**
```javascript
// Keyboard: right arrow advances beat first, then slide
const [slide, setSlide] = useState('title');
const [beat, setBeat] = useState(0);
// Each slide defines maxBeats; right arrow increments beat, then moves to next slide
```

### Build and preview

```bash
cd react
npm run build    # outputs to dist/
# For Pages deployment, copy dist/* to sites/<username>/public/
```

### Build for static hosting

Before deploying the React variant:
1. `npm run build` to generate `dist/`
2. Copy `dist/*` to your hosting public directory
3. All assets are self-contained (no CDN references)

---

## PROCESS

### Default flow

1. **Ask which style** — present the style selection prompt from the top of this document. If the user says "demo" or "compare", generate a single HTML file with one slide in all 6 styles (tabbed), open it, and wait for their pick.
2. **Read the source content** — Google Doc (use `get_google_drive_file`), URL (use WebFetch), pasted text, or an existing HTML/markdown file
3. **Read a reference deck if provided** — if the user supplies an existing HTML deck, read it and match its component patterns and CSS variable structure exactly. If none is provided, build from the selected style's spec.
3. **Extract the narrative arc** — title, stats, context, goals, structure, next steps
4. **Map content to slide types** — one clear point per slide. Use these component patterns:
   - Stats/metrics → stat boxes with count-up animation
   - Definitions → grid of cards with `.def-term` / `.def-body`
   - Comparisons → styled-table with row cascade
   - Processes → numbered steps with `.num-step` / `.num-circle`
   - Quotes/insights → `.slide-quote` or `.discovery-insight`
   - Categories → grid of cards with colored top borders + badges
   - Triggers/tags → `.trigger-pill` or `.tag` pills
   - Context banners → `.banner` with `.banner-tag` + `.banner-text`
6. **Choose a colour palette** — Adapt the `:root` variables to the content's brand or the user's preference. If a reference deck was provided, extract its palette. Otherwise pick a palette that fits the subject matter (e.g. Stripe blurple for internal Stripe decks, green for product launches, dark for technical deep-dives). Structure stays the same: bg, surfaces, 5 accents, text hierarchy.
7. **Write a single HTML file** — All CSS in `<style>`, all JS in `<script>`. Include: bg-grid, bg-glow orbs per slide, animation classes, cursor glow, bottom bar with dots + progress ring, circular nav buttons, print stylesheet.
8. **Add per-slide JS animations** using MutationObserver pattern for any slide with:
   - Count-up numbers → `requestAnimationFrame` + cubic ease-out
   - Table rows → cascade with `translateX(-16px)` stagger
   - Flow diagrams → phased SVG reveal with connection flow animation
9. **Build slide by slide** — This is the most important step. Do NOT write all slides in one pass. For each slide:
   - Write the full HTML for that slide (`.slide` div with bg-grid, bg-glow, slide-inner, content)
   - Check: does every text element have an animation class (`au`/`al`/`ar`/`af`/`as`) with a stagger delay (`d1`-`d12`)?
   - Check: are font sizes using `clamp()` and will they fit at 1280x800?
   - Check: is the content density right? One clear point per slide. If a slide has >5 bullet points or >4 cards, consider splitting.
   - Check: is padding consistent with other slides? (`slide-inner` padding is `3vw 5vw 5vw`; cards use `clamp(16px, 2vw, 24px)`)
   - Check: are grid columns appropriate? 4-col grids need smaller text (13px body). 2-col grids can use 15px. Full-width can use 17px.
   - Check: do coloured elements (labels, badges, card borders, stat values) use the accent variables, not raw hex?
   - Add any per-slide JS (count-up, table cascade, SVG animation) as a self-contained MutationObserver IIFE or `cascadeRows()` call
   - Only then move to the next slide
10. **Assemble the full file** — Combine: `<style>` block, all slides in `<div class="deck">`, cursor glow div, nav buttons, bottom bar, `<script>` block with navigation + cursor glow + per-slide animations
11. **Write file** to project directory under `slides/` or the current directory
12. **Open in browser:** `open [path-to-file]`
12a. **Ask: push to Google Slides?**

After opening, ask:

> Want me to push this to Google Slides? I'll screenshot every slide, build a PPTX, and upload it to your Drive as a native Google Slides file.

If yes, run the pipeline below. If no, continue to the QA pass.

### Google Slides pipeline

**Prerequisites** (install in your slides directory):
- `node_modules/puppeteer` — `npm install puppeteer` if missing
- `python-pptx` — `pip3 install python-pptx` if missing

**Step 1: Copy the HTML and any referenced JS to the slides directory**

```bash
cp /path/to/deck.html ~/.claude/slides/
# Also copy any external .js files the HTML references (e.g. slides-nav.js, slides-navigation.js)
# Check for <script src="..."> tags and copy those files too
```

**Step 2: Screenshot every slide**

```bash
cd ~/.claude/slides
node screenshot-slides.js deck.html
```

This produces `screenshots/deck/slide-01.png`, `slide-02.png`, etc. at 3× retina (3840×2160). The script already hides `.nav` and fixes the body background for clean screenshots.

**Step 3: Compress screenshots**

```bash
for f in ~/.claude/slides/screenshots/deck/*.png; do
  sips -Z 1280 "$f" --out "$f" -s format jpeg -s formatOptions 85 2>/dev/null
  mv "${f%.png}.jpeg" "${f%.png}.png" 2>/dev/null || true
done
```

**Step 4: Build PPTX**

```bash
cd ~/.claude/slides
python3 build-pptx.py deck
```

**Step 5: Upload and convert to Google Slides**

```bash
python3 ~/.claude/slides/upload-to-drive.py deck
```

This uploads to your configured Drive folder and converts the PPTX to a native Google Slides file. Prints the URL on success. Set `DEFAULT_SLIDES_FOLDER_ID` in `upload-to-drive.py` to your own Drive folder ID.

**Report back:** Google Slides URL + slide count.

13. **Run the QA pass** — Review the complete deck checking:
    - **Consistent spacing:** padding, gaps, and margins are uniform across all slides (no slide feels cramped or loose compared to others)
    - **Projector contrast:** text colours have enough contrast against the dark background to survive a washed-out projector. Avoid `var(--text-muted)` for anything the audience needs to read. Body text should be `var(--text-secondary)` minimum. Key stats and titles use `var(--text-primary)` or accent colours.
    - **Animation speed:** all entrance animations are 0.4s or under. The `.slide` transition is 0.35s. Count-up durations (1-1.4s) are the only exception. No animation should feel sluggish.
    - **No overflow on smaller laptops:** mentally test at 1280x800 (13" MacBook). Every font uses `clamp()`. Cards and grids must not overflow. `max-width` on text blocks. If a slide has too much content, split it or reduce font sizes. Grid columns: max 4 on dense slides, prefer 2-3.
    - **Label/number consistency:** slide numbers in labels match sequence. `data-label` attributes are meaningful for the bottom bar.
    Fix any issues found, rewrite the file, and reopen.

### CSS-only bar charts

When generating bar charts, use this pattern to ensure bars render at correct heights:

```css
.bar-chart { display: flex; align-items: flex-end; gap: 12px; height: 120px; }
.bar-group { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; flex: 1; height: 100%; }
.bar { width: 100%; border-radius: 4px 4px 0 0; }
```

Critical: `.bar-group` MUST have `height: 100%` and `justify-content: flex-end` — without this, percentage heights on `.bar` elements won't render (they need an explicitly-sized parent).

### Reusable JS helper: `cascadeRows`

Include this once in the `<script>` block, then call for each table:

```javascript
function cascadeRows(slideId, rowsSelector) {
  var s = document.getElementById(slideId); if (!s) return; var rows = document.querySelectorAll(rowsSelector); var done = false;
  function go() { rows.forEach(function(r, i) { r.style.opacity='0'; r.style.transform='translateX(-16px)';
    setTimeout(function() { r.style.transition='opacity 0.4s ease,transform 0.4s ease'; r.style.opacity='1'; r.style.transform='translateX(0)'; }, 300+i*120); }); }
  function reset() { done=false; rows.forEach(function(r) { r.style.transition='none'; r.style.opacity='0'; r.style.transform='translateX(-16px)'; }); }
  var ob = new MutationObserver(function() { if (s.classList.contains('active')&&!done) { done=true; go(); } else if (!s.classList.contains('active')) { reset(); } });
  ob.observe(s, {attributes:true, attributeFilter:['class']}); if (s.classList.contains('active')) { done=true; go(); }
}
// Usage: cascadeRows('s11', '#price-rows tr');
```

### Demo flow (user says "demo" or "compare")

Generate a single HTML file with one representative slide rendered in all 6 styles (tabbed interface). Open it in the browser and wait for the user to pick their preferred style before building the full deck.

---

## QUALITY CHECKS

### Immersive (default)
- Single self-contained HTML file (inline `<style>` + `<script>`)
- Google Fonts via `<link>` (Outfit + Space Mono) — fallback to system stack for CSP
- Every slide has `.bg-grid` + 1-3 `.bg-glow` orbs
- Every content element has an animation class (`au`/`al`/`ar`/`af`/`as`) with delay (`d1`-`d12`)
- Font sizes use `clamp()` for responsive scaling
- Navigation dots dynamically generated in JS
- **Hash deep links work** — `#3` goes to slide 3 on load
- **Animations replay** on slide entrance via MutationObserver lifecycle
- **Print stylesheet included** — shows all slides, disables animations, proper page breaks
- **Cursor glow** tracks mouse with lerp (disabled on touch devices)
- **Progress ring** updates on every slide change
- **Bottom bar** shows: slide label, pill dots, counter, branding, progress ring

### Multi-file styles (Glassmorphism, Particles, White)
- NO inline scripts — all JS in external files
- NO Google Fonts — system font stack only
- NO external CDN references unless downloaded locally

---

## HOSTING

Offer to publish to your hosting target (GitHub Pages, Netlify, internal pages, etc.).

**Before deploying:** verify no inline scripts, no external font imports, no CDN references. Test locally with CSP:

```python
python3 -c "
from http.server import HTTPServer, SimpleHTTPRequestHandler
class H(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Content-Security-Policy', \"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'\")
        super().end_headers()
HTTPServer(('', 8082), H).serve_forever()
"
```

For the React variant, deploy `react/dist/*` contents to Pages.

Ask the user before publishing anywhere that makes the deck publicly accessible.
