# The Tonight Loop — Design Spec

**Date:** 2026-06-08
**Status:** Approved (pending spec review)
**Topic:** Make the meal planner compelling to use daily by shipping one vertical slice — the "Tonight Loop".

---

## 1. Goal & North Star

The app is a competent weekly planner but doesn't yet answer the one question it exists to answer — *"what's for dinner tonight, and what do I do about it?"* — and it doesn't visibly learn from cooking. This slice fixes both in one self-reinforcing loop.

**North star:** It's 5pm. Mark or his wife opens the app and the first screen shows **tonight's dinner** with a giant **Start Cooking** button and a felt sense the cookbook knows them ("you both loved this — 4.5★", "your note: halve the chilli"). If nothing's planned, **one tap** confirms a top-scored suggestion that explains itself ("haven't had it in 3 weeks", "quick for a weeknight"). Cooking ends in a one-tap rating — and that rating **visibly** makes tomorrow's suggestion smarter, counting for *both* partners.

**Why this slice:** it's the only set of changes where the four highest-leverage gaps compound instead of shipping as disconnected features — it removes the daily decision, makes feeding the engine one tap, and makes that tap visibly pay off.

---

## 2. Scope

### In scope (v1)
1. **Tonight screen** as the new home/front door (layout: hero + week strip).
2. **Confirm-or-Swap** empty state — a single deterministic top-scored suggestion.
3. **Self-explaining suggestion reasons** — human chips replacing the bare `{{ s.score }}%`.
4. **One-tap "Cooked it" + bottom-sheet rating** — reusable across Tonight, Cook Mode finish, and (optionally) recipe detail.
5. **Household-wide scoring** — both partners' ratings/recency/would-make-again count.
6. **Memory cue** — the most recent `CookingNote` surfaced on the Tonight hero.

### Out of scope (explicitly deferred to later phases)
Native haptics; View Transitions; offline shop/cook caching; cook-mode timer; push re-activation; "planned by {name}"/who's-cooking; share-to-import; onboarding; taste-profile persistence; swipe gestures; accessibility/contrast pass; favourite-on-shared 404 fix. Each is its own future slice.

---

## 3. User-facing behaviour (the loop)

1. **Open app → Tonight.** Home route renders the Tonight screen.
2. **Planned tonight:** hero shows today's dinner, memory cue, **Start Cooking** (→ existing cook flow), and **Cooked it**. Below: a slim Mon–Sun week strip (glance + tap into the full grid).
3. **Empty tonight:** hero shows the single top-scored suggestion with reason chips and **Looks good → plan tonight** / **Swap** (next-best) / **Browse** (full picker).
4. **Cook:** Start Cooking → existing step flow → finish → the same rating sheet.
5. **Cooked it (from Tonight):** first tap logs the cook (creates a `CookingNote`); the bottom sheet reveals stars + 👍/👎 make-again + optional note; Save updates the note. Logging counts even with no stars.
6. **Payoff:** the rating immediately feeds household-wide scoring, so tomorrow's suggestion and its reason chips reflect it.

---

## 4. Architecture & components

### 4.1 Routing & navigation
- `recipes/urls.py`: add `path("", tonight_view, name="home")`; **`week_view` keeps `path("week/", … name="week")`** (full Mon–Sun grid unchanged — assign, swap, templates, comments, week-suggest overlay all preserved).
- `recipes/templates/base.html`: first bottom-nav tab becomes **Tonight** (`{% url 'home' %}`, label "Tonight", icon e.g. `bi-stars`). The full grid is reached from the Tonight week strip (a day tap → `/week/`), so the nav stays at 4 tabs.
- New `nav_tonight` block; `week.html` keeps its own active-state handling.

### 4.2 Scoring → household-wide (`recipes/services/meal_planning_assistant.py`)
Change the four user-scoped filters to aggregate across the household's members:
- `calculate_recipe_score` (filter at ~line 51)
- `calculate_recipe_happiness_score` (filter ~76 **and** latest-note filter ~91)
- `get_recently_cooked_recipes` (filter ~111)

Add a private helper:
```python
@staticmethod
def _household_user_ids(user):
    household = get_household(user)
    if not household:
        return [user.id]
    return list(
        User.objects.filter(household_membership__household=household)
        .values_list("id", flat=True)
    )
```
Replace `user=user` with `user__in=MealPlanningAssistantService._household_user_ids(user)` in those queries. Keep the `(recipe, user)` signatures (callers/tests unchanged at the call site). **Note:** this changes semantics — service unit tests that assert per-user scoring must be updated to household semantics. `week_suggest` benefits for free (it already calls `calculate_recipe_happiness_score`).

### 4.3 Suggestion + reason composition (new `recipes/services/suggestions.py`)
A thin `SuggestionService` that composes ranked, reasoned suggestions for the UI, depending on the scoring primitives above. Keeps the Tonight view thin and the scoring module focused.

```python
class SuggestionService:
    @staticmethod
    def rank_for_slot(household, user, slot_date, exclude_ids=()):
        """Return [(recipe, score, reasons)] ranked desc, deterministic top.
        Candidates = own + shared household recipes (same query as week_suggest),
        minus exclude_ids and recently-cooked. Time-fit by weeknight/weekend pref.
        """

    @staticmethod
    def build_reasons(recipe, slot_date, prefs, household_user_ids):
        """Pure-ish: returns a small list of {icon, text} chips from data the
        scorer already uses — days-since-last-cook, avg rating, would_make_again,
        total_time vs weeknight/weekend max. Examples:
        '🕒 3 weeks since', '⚡ 25 min', '★ you both love it', '🆕 never tried'."""
```
- The candidate query mirrors `week_suggest` (`Q(user=user) | Q(shared=True, user__household_membership__household=household)`), so it stays consistent.
- **Tonight** uses the deterministic top pick; **Swap** advances to the next-best (passing the shown recipe id in `exclude_ids`). No `random.choice` for the single-slot case.

### 4.4 Tonight view + templates
- `recipes/views/week.py` (or a new `recipes/views/tonight.py` — preferred, to keep week.py focused): `tonight_view`.
  - Resolves `household`; builds today's slot via `_build_week_context` (reuse) and picks out the `is_today` day for the hero.
  - Planned → hero context (meal, memory cue). Empty → `SuggestionService.rank_for_slot(...)[0]` for the hero suggestion + reasons.
  - Renders the week strip from the same `_build_week_context` days.
- Templates: `recipes/templates/tonight/tonight.html` + partials:
  - `partials/hero_planned.html`, `partials/hero_empty.html` (confirm-or-swap), `partials/week_strip.html`.
  - **Swap** is an HTMX GET returning a fresh `hero_empty.html` with the next suggestion.
  - **Plan tonight** reuses `week_accept_suggestion` semantics (assign recipe to today's dinner slot), then swaps the hero to `hero_planned.html`.
- Reuse existing visual language from `week/partials/meal_card.html` and `suggestions.html`.

### 4.5 Cook-log + rating bottom sheet (reusable)
- New shared partial `recipes/templates/shared/partials/rating_sheet.html` + an Alpine bottom-sheet controller (in `app.js` or inline). Dark theme, `.cook-timer`-style polish; respects existing reduced-motion block.
- New endpoints in `recipes/views/cook.py`:
  - `cook_log(request, pk)` — **POST**: create `CookingNote(recipe, user=request.user, cooked_date=today, rating=None, would_make_again=True)`; return the rating sheet partial bound to the new note id. **Access:** household `access_filter` (copy cook.py:55-58), **not** `user=request.user`, so a partner's shared recipe works.
  - `rating_save(request, note_pk)` — **POST**: update `rating`, `note`, `would_make_again` on the user's own `CookingNote`; return a small confirmation / refreshed memory-cue fragment.
- **Refactor:** extract the note-creation logic so `cook_done` POST (cook.py:132-146) and `cook_log` share one path; the Cook Mode "done" screen renders the same rating sheet partial. Fix `cook_done`'s recipe lookup to the household access filter while here (it currently 404s on shared recipes — in-scope because it's the same rating surface).
- URLs: `path("cook/log/<int:pk>/", cook_log, name="cook_log")`, `path("rating/<int:note_pk>/", rating_save, name="rating_save")`.

### 4.6 Memory cue
- Helper (on `SuggestionService` or a `Recipe` method): most recent household `CookingNote` for a recipe → `{rating, note, cooked_date}`. Surface on the Tonight hero (`hero_planned.html`). Recipe `latest_note` property exists but is user-unscoped via related manager; add a household-aware variant for display.

---

## 5. Data model

**No new models or migrations.** Everything reuses:
- `CookingNote` (recipe, user, cooked_date, rating 1-5 nullable, note, would_make_again default True). One-tap log = a `CookingNote` with `rating=None`.
- `MealPlan` (household, date, meal_type, recipe, added_by) — today's slot.
- `MealPlannerPreferences` (max_weeknight_time / max_weekend_time / avoid_repeat_days) for time-fit + recency.

Known trap to avoid (do **not** reintroduce): user-scoped `get_object_or_404(Recipe, … user=request.user)` on any shared-recipe surface — use the household `access_filter`.

---

## 6. Files to create / modify

**Create**
- `recipes/views/tonight.py` — `tonight_view` (+ swap/accept thin wrappers or reuse week's).
- `recipes/services/suggestions.py` — `SuggestionService` (rank_for_slot, build_reasons, latest household note).
- `recipes/templates/tonight/tonight.html` + `partials/{hero_planned,hero_empty,week_strip}.html`.
- `recipes/templates/shared/partials/rating_sheet.html`.
- Tests: `recipes/tests/test_views_tonight.py`, `recipes/tests/test_suggestions.py`.

**Modify**
- `recipes/urls.py` — `home` → `tonight_view`; `cook_log`, `rating_save` routes.
- `recipes/templates/base.html` — first nav tab → Tonight.
- `recipes/services/meal_planning_assistant.py` — household-wide filters + `_household_user_ids`.
- `recipes/views/cook.py` — `cook_log`, `rating_save`, shared note-create, `cook_done` access-filter fix + reuse rating sheet.
- `recipes/tests/test_services*.py`, `test_meal_planner.py` — update to household scoring semantics.

---

## 7. Testing

- **`test_suggestions.py`** — `rank_for_slot` returns deterministic top pick; excludes recently-cooked & planned; respects weeknight/weekend time-fit; `build_reasons` emits correct chips for: never-cooked, high-rating, recency, time-fit, would-make-again=False.
- **Household scoring** — a 2-member household where partner ratings change a recipe's score and recency; assert both members' notes count (this is the core regression to lock in).
- **`test_views_tonight.py`** — planned hero; empty hero (confirm-or-swap) with reasons; no-recipes empty; **Plan tonight** assigns today's dinner; **Swap** returns next-best.
- **Cook-log/rating** — `cook_log` POST creates a `CookingNote` and works on a partner's shared recipe (no 404); `rating_save` updates it.
- **Regression** — full existing suite stays green (`python manage.py test recipes`).

---

## 8. Edge cases & risks

- **No household** → `_household_user_ids` falls back to `[user.id]`; Tonight still works solo.
- **No recipes at all** → empty hero shows a friendly "add your first recipe" CTA (→ recipe create / AI generate).
- **Recipe with no time set** → treated as time-fit (matches current `total_time is None` handling).
- **Two members rate the same recipe differently** → averaged across the household (intended); document so it's not surprising.
- **Risk: household scoring breaks existing service tests.** Expected — update them as part of the slice; most `setUp` households are single-user so impact is contained.
- **Risk: `cook_done` refactor.** Keep its existing POST contract (creates note, redirect) intact while sharing the create helper; covered by `test_views_cook.py`.

---

## 9. Future phases (context, not scope)

Phase 2 "feels native" (haptics, View Transitions, offline shop/cook, cook timer); Phase 3 re-engagement (push re-activation, rate-last-night nudge); Phase 4 couple (planned-by/who's-cooking, partner-notified comments); Phase 5 growth (share-to-import, onboarding, taste profile). The Tonight Loop is the foundation they all build on.
