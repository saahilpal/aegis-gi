# Changelog: Natural / Earthy Design System & UI Rebuild

All UI layers of the **Outcome-Verified GI Prep & Booking Agent** have been redesigned and rebuilt from first principles.

---

## 1. Natural / Earthy Color System Implementation

### Tokens (Strictly Defined as CSS Variables)
- **Light Theme**:
  - `--bg`: `#F5F1E8` (warm paper)
  - `--surface`: `#FBF8F1` (raised panels)
  - `--surface-subtle`: `#ECE6D8` (wells and insets)
  - `--border`: `#DDD6C6` (hairlines)
  - `--border-strong`: `#C4BCAF` (active borders)
  - `--text`: `#24251F` (soft ink, WCAG AAA 13.4:1 contrast on `--bg`)
  - `--text-muted`: `#6B6A5E` (WCAG AA 4.95:1 contrast on `--surface`)
  - `--text-faint`: `#8A887A`
  - `--accent`: `#4F6B4A` (moss green, the single accent)
  - `--accent-hover`: `#3F583B`
  - `--accent-soft`: `#E3EBDD` (tinted backgrounds)
  - `--warn`: `#B7791F` (ochre)
  - `--danger`: `#A8432F` (terracotta)
- **Dark Theme**:
  - `--bg`: `#1B1D18` (deep forest charcoal)
  - `--surface`: `#23261F` (raised panels)
  - `--surface-subtle`: `#171914` (wells and insets)
  - `--border`: `#35392F` (hairlines)
  - `--border-strong`: `#4B5143` (active borders)
  - `--text`: `#ECE8DC` (WCAG AAA 13.0:1 contrast on `--bg`)
  - `--text-muted`: `#A09E8F` (WCAG AA 5.48:1 contrast on `--surface`)
  - `--text-faint`: `#747265`
  - `--accent`: `#8FAE86` (lighter moss for contrast)
  - `--accent-hover`: `#A5C19C`
  - `--accent-soft`: `#2C3828`
  - `--warn`: `#D9A441` (ochre)
  - `--danger`: `#D2735E` (terracotta)

### Theme Switching & Anti-FOUC
- Added automatic detection via `prefers-color-scheme` in `globals.css`.
- Added persistent manual toggle in `Header.tsx` saving to `localStorage` (`aegis_theme`).
- Added blocking theme detection script in `layout.tsx` `<head>` to prevent Flash of Unstyled Content (FOUC).

---

## 2. Server-Sent Events (SSE) Real-Time Streaming
- Implemented `streamChatMessage` in `frontend/src/lib/api.ts` consuming `/api/chat/stream`.
- Handled events: `status`, `trace_step`, `token`, `outcome`, `ehr_diff`, `done`.
- Added word/token settling animation (`.animate-settle`) with graceful entry (`120ms ease-out`).
- Connected `AbortController` to cancel in-flight requests on new prompt submission.
- Preserved synchronous fallback to `/api/chat` if stream network connection fails.

---

## 3. Responsive Layout & Elimination of Rigid Pixel Constraints
- Eliminated hardcoded `h-[780px]` in `page.tsx`.
- Constructed fluid split-screen grid (`min-h-[calc(100vh-80px)]` on desktop, flowing gracefully on mobile).
- Internal pane scrollbars with custom subtle warm styling (`::-webkit-scrollbar`).

---

## 4. Accessibility & Anti-Slop Polish
- Zero pure black (`#000`), zero pure white (`#FFF`), zero gradients, zero neon glows, zero decorative glassmorphism.
- All touch targets >= 44x44 px via `.touch-target`.
- Visible focus rings via `.earth-focus` (`0 0 0 2px var(--bg), 0 0 0 4px var(--accent)`).
- Modal accessibility: `role="dialog"`, `aria-modal="true"`, `Escape` key dismiss listener.
- Screen reader accessibility: `aria-live="polite"` on incoming message stream.

---

## 5. Verification & Testing
- `npm run build`: Zero errors, static optimization passed.
- `pytest -v`: 15/15 unit and integration tests passing in 0.02s.
- `python -m backend.app.evaluation.ci_check`: 36/36 benchmark scenarios passing with 0.0% False Resolution Rate.
