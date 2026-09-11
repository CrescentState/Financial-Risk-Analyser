# Chrimatos — UI Design Document
## "Research Brief" Identity: making it look intentional

### Design for TWO audiences (the core constraint)

The product has two users, and they read the same page differently:

| | **Normal user** (curious retail, first visit) | **Analyst** (recurring, knows the domain) |
|---|---|---|
| Reads first | **The verdict** — "Is this safe?" | Metrics, rule IDs, confidence, thresholds |
| Wants | A plain-language answer + one clear number | The audit trail — *why* is the score what it is |
| Leaves happy when | They can repeat the conclusion to someone else | They find the number they came to check |
| Fails with | Jargon = mistrust | Missing detail = mistrust |

**The strategy: progressive disclosure — one interface, three layers of depth.**

1. **Layer 1 — The Verdict (everyone, first 5 seconds).** Hero: company, risk level in plain words ("Low risk"), the score, confidence, and a 2-sentence plain-language summary. No jargon in this layer. A normal user can stop here and be correctly served.
2. **Layer 2 — The Brief (interested users).** The plain-English narrative the synthesis agent already produces, news headlines as one-liners, the metric groups with *interpreted* labels ("High debt" next to "D/E 2.4").
3. **Layer 3 — The Desk (analysts).** Full ledger with raw figures, threshold language, triggered rule IDs, pipeline trace with timings, data-source footnotes. Opt-in: collapsed by default, one click or keyboard shortcut (`d`) to reveal.

**Concretely:** every Layer-3 element gets a plain-language neighbor in Layer 2. "P/E 28.4" renders next to "**Expensive** — 28× yearly earnings vs. ~19× typical." Analysts get the number; normal users get the meaning. Same DOM, CSS reveals per section — no "basic/advanced mode" toggle complexity (add later only if wanted).

Language rules for Layers 1–2:
- Never "D/E", always "debt compared to its size"
- Never "P/E > 25 flagged", always "trades above typical pricing"
- Rule IDs (R-04) appear only in Layer 3; Layer 2 says "3 caution checks triggered"
- Confidence always shown as a sentence: "94% confident — all data sources agreed"

> **The problem:** the current UI is competent but anonymous. Inter font, Tailwind-gray
> palette, Material status colors (`#00C851/#FF4444`), 8 metric cards, Plotly gauge,
> rounded pill badges. Every one of those choices is the *default* — which is exactly
> what makes it read as AI-generated. Nothing is wrong; nothing is *chosen*.
>
> **The fix:** commit to one strong editorial identity that fits both audiences: a
> **research brief** — the way a quality financial publication presents analysis.
> Ink-on-paper typography, hairline rules, one accent color used with restraint.
> Analysts get a terminal-grade data layer underneath; normal users get a readable
> brief on top. The look is deliberately editorial (FT/notebook), not SaaS-dashboard:
> density is available, never imposed.

---

## 1. Design principles (the "why" — say these in an interview)

1. **Typography IS the interface.** A risk report is a reading experience. Every
   visual decision serves the hierarchy of information, not decoration.
2. **One accent color, used with discipline.** Risk levels carry the color (green→amber→red),
   everything else is ink-on-paper neutrals. No rainbow of status colors.
3. **Numbers are sacred.** Financial figures use tabular monospace, right-aligned,
   never reflow. The layout never shifts when data changes.
4. **Density over decoration.** Analysts want information, not whitespace theater.
   Bloomberg-dense, not SaaS-airy.
5. **Every element explains itself.** A tooltip on every non-obvious metric ("Debt-to-Equity
   > 2.0 = leveraged balance sheet"). The UI teaches while it reports.
6. **Two audiences, three layers.** The verdict is self-sufficient for a normal user;
   the analyst's numbers are one click away. Neither audience pays for the other's
   needs (see "Design for TWO audiences" above).

---

## 2. What makes the current UI "scream AI" (concrete diagnosis)

| # | Element | Current | Why it reads as AI-made | Replace with |
|---|---|---|---|---|
| 1 | Font | Inter everywhere | The single strongest "made by AI" signal in 2024–26 | **IBM Plex Sans + IBM Plex Mono** (or Geist Mono / JetBrains Mono for figures) |
| 2 | Palette | `#1e3a8a` navy + Tailwind grays + Material green/red | Default-adjacent, zero personality | **Ink paper theme**: `#0D0D0D` text on `#FAFAF7` warm paper; single accent **`#B91C1C`** (editorial red) reserved for risk/danger only; risk scale uses one hue (green→amber→red) |
| 3 | Cards | Rounded-2xl white cards, shadow-sm, 8-up metric grid | The "8 identical cards" is the most AI-ish layout alive | **Data table with rules** — metrics as a *ledger*: hairline rules, right-aligned mono figures, group headers ("Valuation / Solvency / Performance") |
| 4 | Risk gauge | Plotly default gauge (green→red arc) | Plotly default styling screams "I dropped in a library" | **Custom SVG arc** — thin stroke, tick marks, needle with the score in 56px mono. One component, 100 lines, huge payoff |
| 5 | Badges | Rounded pill badges with pastel backgrounds | Tailwind default look | **Text labels with 2px left border** (FT/newspaper style): `▌HIGH RISK` in 11px caps, letterspaced |
| 6 | Buttons | Rounded-lg primary buttons | Default | **Square/2px radius, 1px border, uppercase 12px letterspaced labels** |
| 7 | Layout | 1200px centered, generic grid | "AI app template" | **Asymmetric grid**: 2/3 brief + 1/3 sidebar of metrics; report reads like a research document |
| 8 | Spacing | Even 2rem gaps everywhere | Mechanical rhythm | **Editorial rhythm**: tight section headers (mt 2), generous between sections (mt 6), rule lines instead of boxes |
| 9 | Empty/loading states | Spinner | Default | **Skeleton ledger rows** + "Computing…" in mono, matching the report aesthetic |
| 10 | Icons | lucide-react defaults everywhere | Default library = anonymous | Fewer icons; use **small caps labels** + numbers; icons only for interactive affordances |

---

## 3. Design tokens

```css
:root {
  /* Ink-on-paper neutrals */
  --paper: #FAFAF7;         /* warm off-white, not pure white */
  --ink: #0D0D0D;           /* near-black text */
  --ink-2: #44403C;         /* secondary text (warm gray) */
  --ink-3: #78716C;         /* muted */
  --rule: #E7E5E0;          /* hairlines */
  --rule-strong: #0D0D0D;   /* section dividers */

  /* The ONE accent */
  --accent: #B91C1C;        /* editorial red — risk, danger, highlights */

  /* Risk scale (single-hue ramp, not Material colors) */
  --risk-low:      #15803D;
  --risk-moderate: #A16207;
  --risk-elevated: #C2410C;
  --risk-high:     #B91C0C;

  /* Type */
  --font-sans: "IBM Plex Sans", "Inter", sans-serif;
  --font-mono: "IBM Plex Mono", monospace;

  /* Type scale — editorial sizes */
  --fs-hero: 2.75rem;      /* 44px ticker heading */
  --fs-section: 0.75rem;   /* 12px uppercase letterspaced section labels */
  --fs-metric: 1.375rem;   /* 22px mono figures */
  --fs-body: 0.9375rem;    /* 15px */
  --fs-small: 0.8125rem;   /* 13px */
}
```

### Type rules
- All **figures, tickers, dates, scores**: `--font-mono`, right-aligned in tables
- Section labels: 12px uppercase, letter-spacing 0.08em, `--ink-3`
- Ticker hero: 44px, weight 500 (not 700 — confidence, not shouting)
- Body: 15px/1.6 — readable report prose

---

## 4. Layout spec

```
┌──────────────────────────────────────────────────────────────┐
│ CHRIMATOS  [search──────────────]        HEALTH ● LIVE  GITHUB│  56px header, 1px bottom border
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  AAPL                          ▌LOW RISK                     │  ticker + risk label, baseline-aligned
│  Apple Inc. · NASDAQ           score 18/100 · conf 94%      │  meta row in mono
│                                                              │
│  ────────────────────────────────────────────────────────   │  1px rule
│                                                              │
│  ANALYST BRIEF                                    RISK ▸    │  section label + link
│  ┌──────────────────────────────┬───────────────────────┐   │
│  │                              │ VALUATION             │   │
│  │  Synthesis narrative         │ P/E 28.4     ● above  │   │
│  │  (2/3 width)                 │ D/E 0.9      ● below  │   │  metrics as LEDGER
│  │                              │ SOLVENCY              │   │  (right-aligned mono,
│  │  Pull-quote: "Verdict..."    │ Rev growth −2.1% ●    │   │   hairline rules between
│  │                              │ …                     │   │   rows, group headers)
│  └──────────────────────────────┴─────────────────────┘   │
│                                                              │
│  ────────────────────────────────────────────────────────   │
│  RULES TRIGGERED  (4)                         collapse ▾    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ R-04  Negative equity        triggered    detail ▸   │   │  mono rule IDs
│ R-07  Revenue contraction    triggered    detail ▸   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  SENTIMENT  (14 articles · 72% positive)        collapse ▾  │
│  ┌──────────────────────────────────────────────────────┐ collapsible,
│  │ ● headline · source · ▲ +0.42                        │   │ headline rows
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  PIPELINE TRACE  4 agents · 1.2s                  collapse ▾│  audit trail as first-class
│  financial ✓ 0.4s → sentiment ✓ 0.3s → risk ✓ 0.1s → …    │  (trust signal!)
│ ────────────────────────────────────────────────────────   │
│  © 2026 Chrimatos · data: Alpha Vantage, Finnhub · live demo│  quiet footer
└──────────────────────────────────────────────────────────────┘
```

**Key layout moves (two-audience split):**
- **Layer 1 verdict zone** at the top: hero ticker + plain-language verdict sentence + score + confidence. A normal user's visit can END here, successfully.
- **Analyst content (ledger, rules, trace) defaults collapsed** under a "Show analyst detail" affordance — the top of the page stays clean for everyone, the depth is one click away
- **Asymmetric 2/3 + 1/3**: brief narrative left, metric ledger right — reads like a research note, not a dashboard
- **Rules instead of boxes**: sections separated by hairlines + strong black rule for major sections; no card shadows anywhere
- **Ledger-style metrics**: group headers (VALUATION / SOLVENCY / PERFORMANCE), right-aligned mono figures, inline status dots (●) with meaning
● above median / green = healthy / red = flagged by a rule
- **Score always visible in header zone**: user never scrolls to find the verdict

---

## 5. Component-by-component spec

### 5.1 Header
- 56px, `--paper` bg, 1px `--rule` bottom border
- Left: wordmark "CHRIMATOS" (uppercase, 14px, letterspaced 0.15em)
- Center: search — underline-only input (no boxed field); typeahead rows: ticker (mono) + name + exchange; **kbd hint**: `↵ analyze`
- Right: pipeline health dot (green pulse when healthy; gray = degraded; red = down), GitHub link
- On mobile: search collapses to full-width row below

### 5.2 Ticker header (hero)
- Ticker in 44px mono, company name 15px in ink-2
- Right side: risk label `▌LOW RISK` (11px caps, left 2px border in risk color) + `score 18/100 · confidence 94%` in 13px mono
- 1px rule below

### 5.3 The Metric Ledger (replaces MetricsCards)
```html
<section class="ledger">
  <div class="ledger-group">VALUATION</div>
  <div class="ledger-row">
    <span class="ledger-label">P/E</span>
    <span class="ledger-value">28.4</span>
    <span class="ledger-flag dot-red" title="P/E > 25 → rich valuation rule R-01"/>
  </ valuation section... (abridged)
```
- Group header 11px caps letterspaced
- Each row: label (ink-2, 13px) · value (mono, 22px, right) · status dot + tooltip
- Rules between rows: 1px `--rule`; groups separated by 6px gap
- **8 metrics → 3 groups of readable hierarchy** (Valuation: P/E, Market cap; Solvency: D/E, Current ratio, Cash; Performance: Revenue, growth, Net income)

### 5.4 Custom RiskGauge (SVG, replaces Plotly)
```svg
Semi-circular arc, stroke 3, ticks every 10 points, 0–100 scale,
needle + center score in 44px mono, risk band colors under the arc
```
- ~100 lines of SVG/React; no Plotly (~2.5MB JS saved!)
**Payoff line for interviews:** "I replaced a 2.5 MB Plotly import with a 100-line SVG component — same information, 5KB."
- Animation: needle sweeps to value on load (600ms ease-out)

### 5.5 Rules-triggered list
- Mono rule IDs (`R-04`), rule name, status word ("triggered", 11px caps), expandable detail row
- Each row 44px, 1px rules; hover = `--paper` darken 2%
- Detail expands inline with the exact threshold language from the backend ("D/E 2.4 > threshold 2.0 → leverage rule R-04")

**Why this matters:** the **audit trail becomes a first-class UI feature** — the backend already computes it; the current UI buries it. "Every number has a citation" = trust through transparency.

### 5.6 News Sentiment
- Headline rows: 1px rules, source in 11px caps, ▲/▼ arrow glyph in risk colors, sentiment score in mono
- No cards; a tight list with collapse ("show 4 more")

### 5.7 Pipeline trace
- One line: `financial ✓ 0.4s → sentiment ✓ 0.3s → risk ✓ 0.1s → synthesis ✓ 0.4s` in mono 13px
- Degraded agents show `⚠` instead of ✓, with tooltip on hover
- **Trust through transparency** — nobody's UI shows this; yours does.

### 5.8 Alerts (Degraded/Error)
- No red banner backgrounds. Instead: `▌DEGRADED` label + one-line explanation + link
- Error state: editorial-style, full-width rule + message; never a screaming red box

### 5.9 Buttons & inputs
- Buttons: 2px radius, 1px ink border, transparent bg, uppercase 12px letterspaced; hover fills ink
- Search: underline-only field, focus = 2px ink underline; no box, no shadow

---

## 6. Micro-interactions

| Interaction | Spec |
|---|---|
| Analyze → report | 600ms needle sweep + staggered fade-up of ledger rows (40ms/row) |
| New ticker | Brief text cross-fades (150ms); ticker hero swaps with slide-up 200ms |
| Hover on metric row | Row background `#F5F5F1`; status dot scales 1.2 |
| Tooltip | 1px border, paper bg, mono 12px, small arrow, 120ms fade |
| Collapse/expand | Height animation 200ms; chevron rotates |
| Loading state | **Skeleton ledger rows** (paper-darken bars) + "computing…" in mono, not a spinner |
| Health dot | Green pulse 2s loop; gray on degrade; red on down |
| Empty search | "No companies matched — try Apple, or ticker AAPL" (real copy, not "No results") |

---

## 7. Accessibility & craft details (this is what "intentional" means)

- Contrast: ink `#0D0D0D` on paper `#FAFAF7` = 17.8:1 (AAA); risk colors checked at 4.5:1+
- Focus: 2px ink outline everywhere (`:focus-visible`)
- Never color-only encoding: every status dot has a text label + tooltip
- Tabular figures: `font-variant-numeric: tabular-nums` so columns never shift
- Reduced-motion: respect `prefers-reduced-motion` (skip needle sweep)
- Touch targets ≥ 44px; mobile: ledger goes single column, gauge above brief
- Print stylesheet: the brief prints as a clean research note (huge for demo)

**This section is your interview ammo:** "I care about tabular-nums so numbers don't jitter, focus-visible rings, and a print stylesheet so the brief can be printed as a research note."

---

## 8. Implementation roadmap (concrete, in order)

| # | Task | Files | Effort | Impact |
|---|---|---:|---|---|
| 1 | **Design tokens** (`index.css` rewrite) | `index.css` | 30 min | ⭐⭐⭐ foundation |
| 2 | **Font swap**: IBM Plex Sans + Mono via Google Fonts | `index.css`, remove `Inter` import | 15 min | ⭐⭐⭐ |
| 3 | **MetricsCards → Metric Ledger** | `MetricsCards.tsx` + new `.css` | 2–3 hrs | ⭐⭐⭐ |
| 4 | **Custom SVG RiskGauge** (drop Plotly) | `RiskGauge.tsx` | 2 hrs | ⭐⭐⭐ |
| 5 | Asymmetric grid in App.css | `App.css` | 1 hr | ⭐⭐ |
| 6 | Rules-triggered list upgrade | `RiskGauge`/App layout | 1 hr | ⭐⭐ |
| 7 | Header underline search + health dot | `Header.tsx` | 1 hr | ⭐⭐ |
| 1 [truncated, 37 chars omitted]|
| 9 | Micro-interaction pass (skeletons, transitions) | all | 2 hrs | ⭐⭐ |
|  | **Total** | | **~1.5–2 days** | |

**Day 1:** tokens + fonts + ledger + gauge → the UI will already be transformed. **Day 2:** grid, alerts, trace, micro-interactions, polish. |  |

---

## 9. The one-paragraph pitch (use in README + interviews)

> "I wanted the interface to feel like a research terminal, not an admin dashboard. The design uses ink-on-paper neutrals with a single editorial red reserved for risk; metrics render as a ledger (right-aligned tabular mono figures, hairline rules) instead of 8 identical cards; the risk gauge is a 100-line custom SVG that replaced a 2.5MB Plotly dependency; and the pipeline trace is first-class UI — every agent's status and timing is visible, because for a risk tool, showing your work IS the interface. Typography is the interface."

**And the interview answer for "UI looks AI-made" — now it doesn't:**
> "The first version was every default: Inter, Tailwind grays, 8 cards, Plotly. It worked, but it was anonymous. I rebuilt it as a research terminal: IBM Plex, ink-on-paper, a metric ledger, custom SVG gauge, and the audit trail as a first-class element. Every choice is now a *choice*."

---

## 10. Quick wins if you have only 3 hours

1. Font swap to IBM Plex (15 min) — biggest single visual change
2. Token rewrite in `index.css` (30 min) — kills the Tailwind-gray look instantly
3. Verdict-first hero + collapsed analyst layer (2 hrs) — the signature element for both audiences

Quick wins kill the "AI-look" alone; the full doc is a day-two polish for the live demo.
