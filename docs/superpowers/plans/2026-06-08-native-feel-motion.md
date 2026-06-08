# Native Feel — Motion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add View Transitions to the five daily HTMX swaps so content animates (crossfade for in-place changes, directional slide for the week and cook-step pagination) instead of snapping, with graceful degradation and reduced-motion support.

**Architecture:** Front-end only. Per-swap opt-in via htmx's `transition:true` modifier (wraps each swap in `document.startViewTransition()`). The bottom nav is excluded from the transition via its own `view-transition-name`, so the `root` snapshot can slide while the nav stays put. A ~12-line `app.js` hook reads `data-vt-dir` from the triggering prev/next control and exposes it on `<html>` so scoped CSS can slide left/right. No Python, no new dependencies, no model/URL changes.

**Tech Stack:** HTMX 2.0.4 (loaded), CSS View Transitions API, vanilla JS. Tests: Django `TestCase` + `Client` (attribute regression) + Playwright browser verification. Format/lint: `black` + `isort` + `flake8`.

**Conventions:**
- Activate venv first: `source venv/bin/activate`.
- Run a test module: `python manage.py test recipes.tests.test_motion -v2`.
- These changes are CSS/JS/template attributes; the **only** automated tests are attribute-presence regressions (motion itself is verified in-browser in Task 3).

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `recipes/tests/test_motion.py` (create) | Regression: `transition:true` / `data-vt-dir` stay on the daily swaps | 1, 2 |
| `recipes/templates/tonight/partials/hero_empty.html` | Tonight accept/swap → crossfade | 1 |
| `recipes/templates/recipes/list.html` | Recipe search input → crossfade | 1 |
| `recipes/templates/recipes/partials/search_results.html` | Search pagination → crossfade | 1 |
| `recipes/static/recipes/css/app.css` | Nav exclusion, reduced-motion, slide keyframes + directional rules | 1, 2 |
| `recipes/templates/week/week.html` | Week prev/next → directional slide | 2 |
| `recipes/templates/cook/partials/step.html` | Cook step prev/next/done → directional slide | 2 |
| `recipes/static/recipes/js/app.js` | Direction-hint hook on htmx events | 2 |
| `recipes/static/recipes/sw.js` | Bump cache name so updated CSS/JS propagate | 2 |

---

## Task 1: Crossfade layer + nav exclusion + reduced-motion

The independent baseline: in-place swaps crossfade, the nav is pulled out of transitions, and reduced-motion disables everything. Works on its own even without Task 2.

**Files:**
- Create: `recipes/tests/test_motion.py`
- Modify: `recipes/templates/tonight/partials/hero_empty.html`, `recipes/templates/recipes/list.html`, `recipes/templates/recipes/partials/search_results.html`, `recipes/static/recipes/css/app.css`

- [ ] **Step 1: Write the failing tests**

Create `recipes/tests/test_motion.py`:

```python
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from recipes.models import Recipe
from recipes.models.household import Household, HouseholdMembership


class MotionAttributeTests(TestCase):
    """Regression: the View Transition hx modifiers must stay on the daily swaps."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="m", password="pw")
        self.household = Household.objects.create(name="Home")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Stir Fry",
            steps="Chop veg.\nHeat wok.\nToss and serve.",
            cook_time=15,
        )
        self.client.login(username="m", password="pw")

    def test_tonight_hero_swaps_use_transition(self):
        # No dinner today -> confirm-or-swap hero whose swaps use transition:true.
        response = self.client.get(reverse("home"))
        self.assertContains(response, "transition:true")

    def test_recipe_search_input_uses_transition(self):
        response = self.client.get(reverse("recipe_list"))
        self.assertContains(response, "transition:true")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test recipes.tests.test_motion -v2`
Expected: FAIL — neither template contains `transition:true` yet.

- [ ] **Step 3: Add `transition:true` to the crossfade swaps**

In `recipes/templates/tonight/partials/hero_empty.html`, the accept form (line ~21):
```django
      <form hx-post="{% url 'tonight_accept' %}" hx-target="#tonight-hero" hx-swap="innerHTML transition:true"
            style="margin-top: var(--space-md);">
```
and the Swap button (line ~33):
```django
        <button class="btn btn-outline btn-sm flex-1"
                hx-get="{% url 'tonight_swap' %}?{% for id in exclude_for_swap %}exclude={{ id }}&{% endfor %}"
                hx-target="#tonight-hero" hx-swap="innerHTML transition:true">
```

In `recipes/templates/recipes/list.html`, the search input (line ~56): change `hx-swap="innerHTML"` to:
```django
           hx-swap="innerHTML transition:true"
```

In `recipes/templates/recipes/partials/search_results.html`, both pagination links (lines ~13 and ~21): change each `hx-swap="innerHTML"` to:
```django
         hx-swap="innerHTML transition:true">Prev</a>
```
```django
         hx-swap="innerHTML transition:true">Next</a>
```

- [ ] **Step 4: Add nav exclusion + reduced-motion to `app.css`**

In `recipes/static/recipes/css/app.css`, insert a new section immediately **before** the `29. REDUCED MOTION` block:
```css
/* ============================================================
   VIEW TRANSITIONS
   ============================================================ */
/* Keep the bottom nav fixed while the rest of the page transitions. */
.bottom-nav {
  view-transition-name: vt-nav;
}

```

Then, inside the existing `@media (prefers-reduced-motion: reduce) { ... }` block, add this rule before its closing brace (after the `html { scroll-behavior: auto; }` rule):
```css
  ::view-transition-group(*),
  ::view-transition-old(*),
  ::view-transition-new(*) {
    animation: none !important;
  }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python manage.py test recipes.tests.test_motion -v2`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add recipes/tests/test_motion.py recipes/templates/tonight/partials/hero_empty.html \
        recipes/templates/recipes/list.html recipes/templates/recipes/partials/search_results.html \
        recipes/static/recipes/css/app.css
git commit -m "feat: crossfade View Transitions on Tonight hero + recipe search"
```

---

## Task 2: Directional slide layer (week + cook) + direction hook

Add the directional slides for the two paginated flows, the JS direction hint, the slide keyframes/CSS, and bump the service-worker cache.

**Files:**
- Modify: `recipes/tests/test_motion.py`, `recipes/templates/week/week.html`, `recipes/templates/cook/partials/step.html`, `recipes/static/recipes/js/app.js`, `recipes/static/recipes/css/app.css`, `recipes/static/recipes/sw.js`

- [ ] **Step 1: Write the failing tests**

Append these two methods to `MotionAttributeTests` in `recipes/tests/test_motion.py`:

```python
    def test_week_nav_uses_directional_transition(self):
        response = self.client.get(reverse("week"))
        self.assertContains(response, "transition:true")
        self.assertContains(response, 'data-vt-dir="back"')
        self.assertContains(response, 'data-vt-dir="forward"')

    def test_cook_step_uses_directional_transition(self):
        response = self.client.get(reverse("cook", args=[self.recipe.pk]))
        self.assertContains(response, "transition:true")
        self.assertContains(response, "data-vt-dir")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test recipes.tests.test_motion -v2`
Expected: FAIL — the two new tests fail (week/cook templates lack `data-vt-dir`).

- [ ] **Step 3: Add directional attributes to week + cook nav**

In `recipes/templates/week/week.html`, the previous-week link (lines ~13–19) — set the swap and add the direction:
```django
    <a href="?offset={{ offset|add:"-1" }}"
       class="week-header__nav"
       aria-label="Previous week"
       hx-get="?offset={{ offset|add:"-1" }}"
       hx-target="#main-content"
       hx-swap="innerHTML transition:true"
       data-vt-dir="back"
       hx-push-url="true">&lsaquo;</a>
```
and the next-week link (lines ~30–36):
```django
    <a href="?offset={{ offset|add:"1" }}"
       class="week-header__nav"
       aria-label="Next week"
       hx-get="?offset={{ offset|add:"1" }}"
       hx-target="#main-content"
       hx-swap="innerHTML transition:true"
       data-vt-dir="forward"
       hx-push-url="true">&rsaquo;</a>
```

In `recipes/templates/cook/partials/step.html`, the three nav buttons (lines ~41–63): Prev is "back", Next and Done are "forward":
```django
    <button class="btn btn-outline"
            hx-get="{% url 'cook_step' recipe.pk step_num|add:"-1" %}"
            hx-target="#cook-step-content"
            hx-swap="innerHTML transition:true"
            data-vt-dir="back">
      &lsaquo; Prev
    </button>
```
```django
    <button class="btn btn-primary"
            hx-get="{% url 'cook_step' recipe.pk step_num|add:"1" %}"
            hx-target="#cook-step-content"
            hx-swap="innerHTML transition:true"
            data-vt-dir="forward">
      Next &rsaquo;
    </button>
```
```django
    <button class="btn btn-accent"
            hx-get="{% url 'cook_done' recipe.pk %}"
            hx-target="#cook-step-content"
            hx-swap="innerHTML transition:true"
            data-vt-dir="forward">
      Done <i class="bi bi-check-lg"></i>
```

- [ ] **Step 4: Add the direction-hint hook to `app.js`**

Append to `recipes/static/recipes/js/app.js`:
```javascript

// View Transitions: expose the triggering control's data-vt-dir on <html> for the
// duration of the swap, so scoped CSS can slide the page back/forward.
document.body.addEventListener('htmx:beforeRequest', (e) => {
    const dir = e.detail.elt && e.detail.elt.dataset ? e.detail.elt.dataset.vtDir : null;
    if (dir) {
        document.documentElement.dataset.vtDir = dir;
    } else {
        delete document.documentElement.dataset.vtDir;
    }
});
document.body.addEventListener('htmx:afterSettle', () => {
    delete document.documentElement.dataset.vtDir;
});
```

- [ ] **Step 5: Add the slide keyframes + directional rules to `app.css`**

In `recipes/static/recipes/css/app.css`, append to the `VIEW TRANSITIONS` section created in Task 1 (right after the `.bottom-nav { view-transition-name: vt-nav; }` rule):
```css
/* Directional slide for the paginated flows (week nav, cook steps). */
@keyframes vt-slide-out-left {
  from { transform: translateX(0); opacity: 1; }
  to   { transform: translateX(-30px); opacity: 0; }
}
@keyframes vt-slide-in-right {
  from { transform: translateX(30px); opacity: 0; }
  to   { transform: translateX(0); opacity: 1; }
}
@keyframes vt-slide-out-right {
  from { transform: translateX(0); opacity: 1; }
  to   { transform: translateX(30px); opacity: 0; }
}
@keyframes vt-slide-in-left {
  from { transform: translateX(-30px); opacity: 0; }
  to   { transform: translateX(0); opacity: 1; }
}

html[data-vt-dir="forward"]::view-transition-old(root) {
  animation: vt-slide-out-left 0.25s ease both;
}
html[data-vt-dir="forward"]::view-transition-new(root) {
  animation: vt-slide-in-right 0.25s ease both;
}
html[data-vt-dir="back"]::view-transition-old(root) {
  animation: vt-slide-out-right 0.25s ease both;
}
html[data-vt-dir="back"]::view-transition-new(root) {
  animation: vt-slide-in-left 0.25s ease both;
}
```

- [ ] **Step 6: Bump the service-worker cache**

In `recipes/static/recipes/sw.js`, line 1: change `const CACHE_NAME = 'meal-planner-v3';` to:
```javascript
const CACHE_NAME = 'meal-planner-v4';
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python manage.py test recipes.tests.test_motion -v2`
Expected: PASS (4 tests).

- [ ] **Step 8: Commit**

```bash
git add recipes/tests/test_motion.py recipes/templates/week/week.html \
        recipes/templates/cook/partials/step.html recipes/static/recipes/js/app.js \
        recipes/static/recipes/css/app.css recipes/static/recipes/sw.js
git commit -m "feat: directional slide View Transitions for week + cook navigation"
```

---

## Task 3: Full verification (suite + browser)

**Files:** none new — verification + any small fixes surfaced.

- [ ] **Step 1: Format, lint, full suite**

Run:
```bash
black . && isort . && flake8
python manage.py test recipes.tests.test_motion recipes.tests.test_household_scoring recipes.tests.test_suggestions recipes.tests.test_views_tonight recipes.tests.test_views_week recipes.tests.test_views_cook recipes.tests.test_services recipes.tests.test_services_new recipes.tests.test_meal_planner recipes.tests.test_models recipes.tests.test_models_new recipes.tests.test_views recipes.tests.test_views_recipes recipes.tests.test_views_shop recipes.tests.test_urls recipes.tests.test_forms recipes.tests.test_integration recipes.tests.test_templates recipes.tests.test_templatetags recipes.tests.test_utils recipes.tests.test_push recipes.tests.test_generate recipes.tests.test_import_url recipes.tests.test_household recipes.tests.test_ai_structured
```
Expected: black/isort/flake8 clean; all tests OK (0 failures). The non-motion swaps are byte-identical server-side, so nothing else should move.

- [ ] **Step 2: Browser verification (controller-driven, Playwright @ 390×844)**

> Motion is not unit-testable; the controller (not an implementer subagent) drives this with Playwright against a dev server, using an isolated smoke user (separate household + a recipe with steps). Tear the smoke user/data down afterwards.

Install a spy before navigating, then exercise each swap:
```javascript
// browser_evaluate, once after login:
() => { window.__vt = 0; const o = document.startViewTransition?.bind(document);
        if (o) document.startViewTransition = (cb) => { window.__vt++; return o(cb); };
        return !!o; }   // false => API unsupported (acceptable: instant swaps)
```
Verify, reading `window.__vt` and `document.documentElement.dataset.vtDir` after each:
1. Tonight **Swap** and **plan tonight** → `__vt` increments, no `data-vt-dir` (crossfade).
2. `/week/` **next** → `__vt` increments and `data-vt-dir` was `"forward"` during the swap; **prev** → `"back"`. Confirm the bottom nav does not move (it keeps `view-transition-name: vt-nav`).
3. Cook mode **Next**/**Prev** step → `__vt` increments, directional.
4. `/recipes/` search typing → `__vt` increments (crossfade).
5. Emulate reduced motion (`browser_resize` is not enough — set it via an init script or DevTools emulation) and confirm swaps still produce correct content with animations suppressed.

Confirm zero console errors throughout.

- [ ] **Step 3: Commit (checkpoint)**

```bash
git add -A
git commit -m "chore: Native Feel motion — verification checkpoint" --allow-empty
```

---

## Spec coverage check

| Spec requirement | Task |
|---|---|
| Crossfade on Tonight hero (accept/swap) | 1 |
| Crossfade on recipe search + pagination | 1 |
| Directional slide on week prev/next | 2 |
| Directional slide on cook step prev/next | 2 |
| Bottom nav held fixed (`view-transition-name`) | 1 |
| Direction hint via `data-vt-dir` + `app.js` hook | 2 |
| `prefers-reduced-motion` disables animations | 1 |
| Graceful degradation (no VT API) | inherent (htmx) — verified Task 3 |
| Overlays left untouched | inherent (not edited) |
| SW cache bump so CSS/JS propagate | 2 |
| Existing suite stays green | 3 |

## Notes for the implementer

- `transition:true` is an htmx `hx-swap` modifier (space-separated), e.g. `hx-swap="innerHTML transition:true"`. Do not put it in a separate attribute.
- Only `.bottom-nav` gets a `view-transition-name`. Do **not** name `#main-content` or `#cook-step-content` — `#main-content` lives in `base.html` and a duplicate name across pages makes the View Transitions API skip the transition.
- `cook.html` is a standalone page (not extending `base.html`) but it loads `app.js`, so the direction hook applies there too. It has no bottom nav — the whole cook screen sliding is the intended pager feel.
- Keep edits to the listed swaps only. Do **not** add `transition:true` to the body-append overlay swaps (`week_suggest`, `list_templates`, `cook_log`) — those are intentionally excluded.
