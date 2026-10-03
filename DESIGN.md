# DESIGN SPECIFICATION: NATURAL / EARTHY

**Project**: Aegis GI — Outcome-Verified GI Prep & Booking Agent  
**Design Persona**: Senior Product Designer + Frontend Engineer + QA Lead  
**Aesthetic Concept**: **Natural / Earthy** (Warm paper, stone, clay, moss, and soft ink)  
**Status**: Committed Specification  

---

## 1. Core Principles

- **Calm, warm, organic**: Derived from physical paper, stone, clay, moss, and ink. No clinical sterility, no tech-bro neon, no synthetic glows.
- **One accent only**: Moss green (`--accent`). Everything else is structured through neutral shades, precise 1px borders, and deliberate typographic rhythm.
- **Zero pure white (`#FFF`) & zero pure black (`#000`)**: Surfaces reflect natural reflectance values of tactile paper and forest charcoal.
- **Strict WCAG AA contrast compliance**: Minimum 4.5:1 for body copy; minimum 3:1 for large display titles and operational markers.
- **Border and spacing over heavy drop-shadows**: Clean, hairline divisions (`--border`) establish structural hierarchy without decorative visual clutter.

---

## 2. Color Token System

All components reference CSS custom properties exclusively; no hardcoded hex codes.

### Light Theme Tokens (Default)
```css
:root {
  --bg:           #F5F1E8;  /* warm paper */
  --surface:      #FBF8F1;  /* raised cards / panels */
  --surface-subtle: #EFE9DC; /* input wells, hover rows */
  --border:       #DDD6C6;  /* hairline rules */
  --border-strong:#C5BCAB;  /* active / focused borders */
  --text:         #24251F;  /* soft ink */
  --text-muted:   #6B6A5E;  /* metadata, secondary labels */
  --text-faint:   #8E8C7E;  /* tertiary annotations */
  --accent:       #4F6B4A;  /* moss green (only accent) */
  --accent-hover: #3F583B;
  --accent-soft:  #E3EBDD;  /* tinted pill backgrounds */
  --warn:         #B7791F;  /* ochre */
  --danger:       #A8432F;  /* terracotta */
  --shadow-soft:  0 2px 8px rgba(36, 37, 31, 0.04);
}
```

### Dark Theme Tokens (`.dark` / `prefers-color-scheme: dark`)
```css
.dark {
  --bg:           #1B1D18;  /* deep forest charcoal */
  --surface:      #23261F;  /* raised surfaces */
  --surface-subtle: #181A15; /* recessed wells */
  --border:       #35392F;  /* hairline rules */
  --border-strong:#4E5445;  /* active borders */
  --text:         #ECE8DC;  /* warm off-white */
  --text-muted:   #A09E8F;  /* secondary labels */
  --text-faint:   #787668;  /* tertiary annotations */
  --accent:       #8FAE86;  /* light moss for contrast */
  --accent-hover: #A5C19C;
  --accent-soft:  #2C3828;  /* tinted backgrounds */
  --warn:         #D9A441;  /* ochre */
  --danger:       #D2735E;  /* terracotta */
  --shadow-soft:  0 2px 8px rgba(0, 0, 0, 0.25);
}
```

---

## 3. Typographic Scale & Rhythm

Two carefully paired typefaces:
- **Headings & Narrative**: `Newsreader` / `Lora` serif fallback or clean `Inter` tuned for editorial reading.
- **Telemetry, Tables & Verification Ledger**: `JetBrains Mono` for tabular numerals, timestamps, and claims.

| Role | Family | Size | Weight | Line Height | Tracking |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Cockpit Title** | Serif / Inter | 18px (1.125rem) | 600 | 24px | -0.015em |
| **Section Header** | Inter | 12px (0.75rem) | 600 | 16px | 0.05em (Caps) |
| **Body Primary** | Inter | 14px (0.875rem) | 400 | 22px | 0 |
| **Body Secondary** | Inter | 13px (0.8125rem) | 400 | 18px | 0 |
| **Code / Telemetry** | JetBrains Mono | 12px (0.75rem) | 500 | 16px | -0.01em |
| **Status Badge** | JetBrains Mono | 11px (0.6875rem) | 700 | 14px | 0.06em (Caps) |

---

## 4. Anti-Slop Implementation Rules

- **Zero glassmorphism / zero backdrop-blur**.
- **Zero glowing neon borders or gradient text**.
- **No decorative emojis**: Clean functional Lucide SVG icons only.
- **Fluid Layout**: No hardcoded pixel heights (`h-[780px]` eliminated). Seamless scaling from 320px mobile to 1440px+ workstations.
- **Touch Targets**: Minimum 44x44px bounding box for all interactive triggers.

---

## 5. Motion Principles

- **Token Settling**: Incoming streamed words fade in smoothly (`opacity: 0 -> 1`, `transform: translateY(2px) -> 0`, 80ms duration).
- **Execution Pipeline**: Completed LangGraph nodes transition with subtle indicator shifting.
- **Tactile Feedback**: Buttons depress slightly on press (`active:scale-[0.98]`).
- **prefers-reduced-motion**: Respected globally to disable motion for sensitive users.
