# Native Feel — Motion — Design Spec

**Date:** 2026-06-08
**Status:** Approved (pending spec review)
**Topic:** Phase 2 ("feels-native"), motion only — add View Transitions to the key daily HTMX swaps so content animates instead of snapping. Scope deliberately tight: **no haptics, offline, cook timer, or manifest changes** (each is its own future slice).

---

## 1. Goal & context

The app's daily interactions replace content instantly with zero transition, which reads as "website in a shell" rather than a native app — even though `fadeInUp`/`slideUp` keyframes already exist (`app.css`) and HTMX 2.0.4 (loaded) supports the View Transitions API. This slice makes the handful of high-frequency content swaps animate smoothly, with graceful degradation. Pure front-end: **no Python, no new dependencies, no model/URL changes.** It ships to the iOS app via a normal Railway redeploy (remote-webview), no Xcode rebuild.

---

## 2. Scope

### In
View Transitions on five daily content swaps (table below): crossfade for in-place content changes, directional horizontal slide for the two paginated flows. Respect `prefers-reduced-motion`. Graceful no-op where the View Transitions API is unsupported.

### Out (explicitly deferred)
Haptics (needs native `@capacitor/haptics` + Xcode), offline shop/cook caching, shopping-checkmark persistence, cook-mode timer, manifest shortcuts, swipe gestures, contrast/focus pass. Overlay swaps (suggestions, rating sheet, template picker) are **left as-is** — they already slide up via existing keyframes, and applying View Transitions to body-append swaps risks a full-page flash.

---

## 3. Behaviour — what moves, and how

| Interaction | Trigger / swap target | Motion |
|---|---|---|
| Tonight: accept suggestion | `hero_empty.html` form → `#tonight-hero` (innerHTML) | Crossfade |
| Tonight: swap suggestion | `hero_empty.html` Swap → `#tonight-hero` (innerHTML) | Crossfade |
| Week ‹ prev / next › | `week.html` nav → `#main-content` (innerHTML) | Directional slide |
| Cook step ‹ Prev / Next › | `step.html` nav → `#cook-step-content` (innerHTML) | Directional slide |
| Recipe search + pagination | `list.html` input + `search_results.html` → `#recipe-results` (innerHTML) | Crossfade |

The **bottom nav stays put** during the directional slides.

---

## 4. Mechanism — per-swap View Transitions

1. **Opt-in per swap.** Add the htmx modifier `transition:true` to the `hx-swap` on the five swaps above (e.g. `hx-swap="innerHTML transition:true"`). htmx wraps each swap in `document.startViewTransition()`. Crossfade is the View Transitions API default — no custom CSS needed for the crossfade swaps.

2. **Keep the bottom nav fixed.** Give `.bottom-nav` its own `view-transition-name` (e.g. `vt-nav`) in `app.css`. Naming it pulls it out of the `root` snapshot, so it never moves while the rest of the page slides/crossfades. (When the nav is absent — e.g. cook mode using `.screen--no-nav` — this is simply inert.)

3. **Directional slides** for the two paginated flows (week, cook):
   - Mark each prev/next control with `data-vt-dir="back"` (prev) or `data-vt-dir="forward"` (next).
   - A small hook in `app.js` listens for `htmx:beforeRequest`, reads `event.detail.elt.dataset.vtDir`, and sets it on `document.documentElement` (e.g. `<html data-vt-dir="forward">`); it clears it on `htmx:afterSettle`.
   - Scoped CSS slides the `root` snapshot accordingly:
     - `forward`: old → slide out left, new → slide in from right.
     - `back`: old → slide out right, new → slide in from left.
   - Four new `@keyframes` (slide-out-left/right, slide-in-left/right). Swaps **without** `data-vt-dir` (Tonight hero, search) fall through to the default crossfade.

4. **No per-page `view-transition-name` juggling.** Only `.bottom-nav` is named; the directional motion animates the `root` snapshot. This avoids duplicate-name conflicts from `#main-content` (which lives in `base.html` and appears on every page).

---

## 5. Reduced motion & degradation

- **`prefers-reduced-motion: reduce`** — disable the transition animations so swaps are instant. Extend the existing `@media (prefers-reduced-motion: reduce)` block (`app.css`) with:
  `::view-transition-group(*), ::view-transition-old(*), ::view-transition-new(*) { animation: none !important; }`
- **No View Transitions API** (older iOS / browsers) — htmx detects the absence and performs a plain instant swap. **No breakage**, no errors.
- The crossfade baseline is independent of the directional layer: if a directional slide ever misbehaves on a device, removing the `data-vt-dir` hint leaves a clean crossfade.

---

## 6. Files to modify (no Python, no deps)

- `recipes/templates/tonight/partials/hero_empty.html` — `transition:true` on the accept form and the Swap button swaps.
- `recipes/templates/week/week.html` — `transition:true` + `data-vt-dir="back"`/`"forward"` on the prev/next nav links (lines ~16–18 / ~33–35). Leave the `week_suggest` / `list_templates` body-append buttons untouched.
- `recipes/templates/cook/partials/step.html` — `transition:true` + `data-vt-dir` on the Prev/Next buttons (lines ~42–44 / ~53–55).
- `recipes/templates/recipes/list.html` — `transition:true` on the search input's `hx-swap` (lines ~53–56).
- `recipes/templates/recipes/partials/search_results.html` — `transition:true` on the pagination prev/next (lines ~11–13 / ~19–21).
- `recipes/static/recipes/css/app.css` — `.bottom-nav { view-transition-name: vt-nav; }`; four slide `@keyframes`; `html[data-vt-dir="forward"|"back"]::view-transition-old/new(root)` rules; reduced-motion handling.
- `recipes/static/recipes/js/app.js` — the ~10-line `htmx:beforeRequest`/`htmx:afterSettle` direction-hint hook.

Bump the service worker cache name (`sw.js` `CACHE_NAME`) so the updated `app.css`/`app.js` are picked up by installed PWAs.

---

## 7. Testing

- **No behaviour change** → the full existing non-e2e suite must stay green. `transition:true` is a client-side hx modifier and `data-vt-dir` / `view-transition-name` are inert attributes; server responses are byte-for-byte unaffected.
- **Cheap regression test** (`recipes/tests/test_views_*`): assert the rendered week / cook-step / tonight templates contain `transition:true` so the attribute can't silently regress.
- **Browser verification** (Playwright @ iPhone 12 Pro, 390×844): for each of the five swaps, confirm (a) the swap still works and returns the right content, and (b) a View Transition fires — spy on `document.startViewTransition` (assert call count increments on swap) or detect the `::view-transition` pseudo / `data-vt-dir` toggling. Confirm directional slides go the correct way (prev = back, next = forward) and that emulating `prefers-reduced-motion: reduce` disables them.

---

## 8. Risks & edge cases

- **Full-page flash on crossfade swaps.** Root-level crossfade where only a small region changed is smooth in practice (old/new are near-identical). If any specific swap flashes in testing, scope it by giving the changed target (`#tonight-hero` / `#recipe-results`) its own `view-transition-name` so only that region crossfades.
- **Concurrent swaps** could leave a stale `data-vt-dir`. Clearing on `htmx:afterSettle` is sufficient for this single-user-per-screen app; not worth locking.
- **Cook mode nav.** If cook mode renders without `.bottom-nav`, naming it is inert; the whole cook screen slides, which is the intended pager feel.
- **htmx event detail shape.** The triggering element is read from `event.detail.elt` on `htmx:beforeRequest`; verify against htmx 2.0.4 during implementation and adjust if the property differs.
