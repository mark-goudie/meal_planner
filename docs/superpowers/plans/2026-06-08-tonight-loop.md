# The Tonight Loop — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the meal planner compelling to use daily by shipping the "Tonight Loop": a Tonight-first home screen, a confirm-or-swap empty state with self-explaining suggestions, one-tap cook logging with a reusable rating sheet, household-wide scoring, and a recent-cook memory cue.

**Architecture:** Additive Django + HTMX + Alpine slice. A new `tonight_view` becomes the home route (`/`); the existing full week grid is untouched at `/week/`. Scoring in `meal_planning_assistant.py` becomes household-wide. A new `SuggestionService` composes ranked, reasoned single-slot suggestions. A shared rating-fields partial is reused by the Tonight bottom sheet and the existing Cook Mode finish screen. No new models or migrations.

**Tech Stack:** Django 5.2, HTMX 2, Alpine 3. Tests: Django `TestCase` + `Client`. Formatting: `black` + `isort`; lint: `flake8` (config in `setup.cfg`).

**Conventions to follow:**
- Run a single test: `python manage.py test recipes.tests.test_x.ClassName.test_method -v2`
- Run a module: `python manage.py test recipes.tests.test_x -v2`
- Reuse existing CSS classes/tokens: `.btn-accent` (gold CTA), `.btn-primary`, `.btn-outline`, `.btn-ghost`, `.chip`/`.chip--accent`/`.chip--muted`, `.day-card*`, `.day-list`, tokens `--primary #7cb9a8`, `--accent #ffd59a`, `--bg #1a1a2e`, `--text-main`, `--text-muted`, `--space-*`, `--radius-lg`, `--text-*`. Do **not** invent new colors.
- Mirror the existing bottom-sheet overlay pattern from `recipes/templates/week/partials/suggestions.html` (fixed inset 0, `align-items: flex-end`, HTMX `hx-target="body" hx-swap="beforeend"`).
- Each task ends green and committed.

---

## Task 1: Household-wide scoring

Make the four user-scoped queries in the scorer aggregate across household members, so both partners' ratings and recency count. Falls back to `[user.id]` when the user has no household (preserving current behaviour and the existing test suite).

**Files:**
- Modify: `recipes/services/meal_planning_assistant.py`
- Test: `recipes/tests/test_household_scoring.py` (create)

- [ ] **Step 1: Write the failing test**

Create `recipes/tests/test_household_scoring.py`:

```python
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from recipes.models import CookingNote, Recipe
from recipes.models.household import Household, HouseholdMembership
from recipes.services.meal_planning_assistant import MealPlanningAssistantService as S


class HouseholdScoringTests(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Home")
        self.alice = User.objects.create_user(username="alice", password="x")
        self.bob = User.objects.create_user(username="bob", password="x")
        HouseholdMembership.objects.create(user=self.alice, household=self.household)
        HouseholdMembership.objects.create(user=self.bob, household=self.household)
        self.recipe = Recipe.objects.create(user=self.alice, title="Curry", steps="Cook.")

    def test_partner_rating_counts_toward_happiness_score(self):
        # Bob rates 5 stars; Alice has no notes. Household-wide score = 100.
        CookingNote.objects.create(
            recipe=self.recipe, user=self.bob, cooked_date=date.today(), rating=5
        )
        score = S.calculate_recipe_happiness_score(self.recipe, self.alice)
        self.assertEqual(score, Decimal("100.0"))

    def test_partner_recent_cook_excludes_recipe_for_household(self):
        CookingNote.objects.create(
            recipe=self.recipe, user=self.bob, cooked_date=date.today()
        )
        recent = S.get_recently_cooked_recipes(self.alice, days=14)
        self.assertIn(self.recipe.id, recent)

    def test_solo_user_without_household_unaffected(self):
        solo = User.objects.create_user(username="solo", password="x")
        r = Recipe.objects.create(user=solo, title="Solo", steps="x")
        CookingNote.objects.create(
            recipe=r, user=solo, cooked_date=date.today(), rating=4
        )
        self.assertEqual(S.calculate_recipe_happiness_score(r, solo), Decimal("75.0"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test recipes.tests.test_household_scoring -v2`
Expected: FAIL — `test_partner_rating_counts_toward_happiness_score` gets `Decimal("50.0")` (partner note ignored) instead of `100.0`.

- [ ] **Step 3: Implement household aggregation**

In `recipes/services/meal_planning_assistant.py`, add this static method to the class (after `get_or_create_preferences`):

```python
    @staticmethod
    def _household_user_ids(user: User) -> List[int]:
        """User IDs of everyone in this user's household, or [user.id] if none."""
        household = get_household(user)
        if not household:
            return [user.id]
        return list(
            User.objects.filter(
                household_membership__household=household
            ).values_list("id", flat=True)
        )
```

Then replace the four `user=user` filters with `user__in=...`:

In `calculate_recipe_score` (the `notes = CookingNote.objects.filter(...)` block):
```python
        user_ids = MealPlanningAssistantService._household_user_ids(user)
        notes = CookingNote.objects.filter(
            recipe=recipe, user__in=user_ids, rating__isnull=False
        )
```

In `calculate_recipe_happiness_score` — the `notes` query **and** the `latest_note` query:
```python
        user_ids = MealPlanningAssistantService._household_user_ids(user)
        notes = CookingNote.objects.filter(
            recipe=recipe, user__in=user_ids, rating__isnull=False
        )
```
```python
        latest_note = (
            CookingNote.objects.filter(recipe=recipe, user__in=user_ids)
            .order_by("-cooked_date")
            .first()
        )
```

In `get_recently_cooked_recipes`:
```python
        user_ids = MealPlanningAssistantService._household_user_ids(user)
        return list(
            CookingNote.objects.filter(
                user__in=user_ids,
                cooked_date__gte=cutoff_date,
            )
            .order_by()
            .values_list("recipe_id", flat=True)
            .distinct()
        )
```

(`User` and `get_household` are already imported at the top of the file.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test recipes.tests.test_household_scoring recipes.tests.test_services_new recipes.tests.test_meal_planner recipes.tests.test_services -v2`
Expected: PASS (new tests pass; existing scoring/recency tests stay green because their users have no shared household → `[user.id]`).

- [ ] **Step 5: Commit**

```bash
git add recipes/services/meal_planning_assistant.py recipes/tests/test_household_scoring.py
git commit -m "feat: household-wide recipe scoring (both partners' ratings count)"
```

---

## Task 2: SuggestionService — ranked, reasoned single-slot suggestions

A new service that returns a deterministic, ranked list of suggestions for one date, each with human-readable reason chips, plus a household-aware "latest note" helper for the memory cue.

**Files:**
- Create: `recipes/services/suggestions.py`
- Test: `recipes/tests/test_suggestions.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `recipes/tests/test_suggestions.py`:

```python
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from recipes.models import CookingNote, Recipe
from recipes.models.household import Household, HouseholdMembership
from recipes.services.suggestions import SuggestionService


class RankForSlotTests(TestCase):
    def setUp(self):
        self.hh = Household.objects.create(name="Home")
        self.u = User.objects.create_user(username="u", password="x")
        HouseholdMembership.objects.create(user=self.u, household=self.hh)
        self.high = Recipe.objects.create(user=self.u, title="High", steps="x", cook_time=20)
        self.low = Recipe.objects.create(user=self.u, title="Low", steps="x", cook_time=20)
        # Cooked 30 days ago (outside the 14-day avoid window), so both are eligible.
        CookingNote.objects.create(
            recipe=self.high, user=self.u, cooked_date=date.today() - timedelta(days=30), rating=5
        )
        CookingNote.objects.create(
            recipe=self.low, user=self.u, cooked_date=date.today() - timedelta(days=30), rating=1
        )

    def test_top_pick_is_highest_scored(self):
        ranked = SuggestionService.rank_for_slot(self.hh, self.u, date.today())
        self.assertEqual(ranked[0]["recipe"], self.high)

    def test_exclude_ids_skips_recipe(self):
        ranked = SuggestionService.rank_for_slot(
            self.hh, self.u, date.today(), exclude_ids=[self.high.id]
        )
        self.assertNotIn(self.high, [r["recipe"] for r in ranked])

    def test_each_suggestion_has_reasons(self):
        ranked = SuggestionService.rank_for_slot(self.hh, self.u, date.today())
        self.assertTrue(ranked[0]["reasons"])
        self.assertIn("text", ranked[0]["reasons"][0])

    def test_empty_when_no_recipes(self):
        Recipe.objects.all().delete()
        self.assertEqual(SuggestionService.rank_for_slot(self.hh, self.u, date.today()), [])


class BuildReasonsTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="r", password="x")
        self.recipe = Recipe.objects.create(user=self.u, title="X", steps="x", cook_time=25)

    def test_never_tried_recipe_reason(self):
        from recipes.services.meal_planning_assistant import MealPlanningAssistantService
        prefs = MealPlanningAssistantService.get_or_create_preferences(self.u)
        reasons = SuggestionService.build_reasons(self.recipe, date.today(), prefs, self.u)
        texts = [r["text"] for r in reasons]
        self.assertIn("Never tried", texts)

    def test_time_reason_present(self):
        from recipes.services.meal_planning_assistant import MealPlanningAssistantService
        prefs = MealPlanningAssistantService.get_or_create_preferences(self.u)
        reasons = SuggestionService.build_reasons(self.recipe, date.today(), prefs, self.u)
        texts = [r["text"] for r in reasons]
        self.assertIn("25 min", texts)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test recipes.tests.test_suggestions -v2`
Expected: FAIL — `ModuleNotFoundError: No module named 'recipes.services.suggestions'`.

- [ ] **Step 3: Implement the service**

Create `recipes/services/suggestions.py`:

```python
"""Compose ranked, reasoned meal suggestions for a single date.

Depends on MealPlanningAssistantService for household-wide scoring/recency.
Deterministic: ranking is stable (score, then recipe id) so 'Swap' can walk
predictably to the next-best pick.
"""

from django.db.models import Avg, Q

from ..models import CookingNote, Recipe
from .meal_planning_assistant import MealPlanningAssistantService as MPA


class SuggestionService:
    @staticmethod
    def rank_for_slot(household, user, slot_date, exclude_ids=()):
        """Return [{recipe, score, reasons}] ranked best-first for slot_date."""
        prefs = MPA.get_or_create_preferences(user)

        if household:
            candidates = list(
                Recipe.objects.filter(
                    Q(user=user)
                    | Q(shared=True, user__household_membership__household=household)
                )
                .distinct()
                .prefetch_related("tags")
            )
        else:
            candidates = list(
                Recipe.objects.filter(user=user).prefetch_related("tags")
            )

        exclude = set(exclude_ids)
        pool = [r for r in candidates if r.id not in exclude]
        if not pool:
            return []

        recently = set(MPA.get_recently_cooked_recipes(user, prefs.avoid_repeat_days))
        fresh = [r for r in pool if r.id not in recently]
        pool = fresh or pool  # fall back if everything was recently cooked

        is_weekend = slot_date.weekday() in MPA.WEEKENDS
        max_time = prefs.max_weekend_time if is_weekend else prefs.max_weeknight_time
        time_ok = [r for r in pool if r.total_time is None or r.total_time <= max_time]
        pool = time_ok or pool

        scored = [
            (r, float(MPA.calculate_recipe_happiness_score(r, user))) for r in pool
        ]
        # Deterministic: highest score first, tie-break by id descending.
        scored.sort(key=lambda x: (x[1], x[0].id), reverse=True)

        return [
            {
                "recipe": r,
                "score": round(s),
                "reasons": SuggestionService.build_reasons(r, slot_date, prefs, user),
            }
            for r, s in scored
        ]

    @staticmethod
    def build_reasons(recipe, slot_date, prefs, user):
        """Human reason chips from data the scorer already uses."""
        user_ids = MPA._household_user_ids(user)
        reasons = []

        agg = CookingNote.objects.filter(
            recipe=recipe, user__in=user_ids, rating__isnull=False
        ).aggregate(avg=Avg("rating"))
        avg = agg["avg"]
        if avg is None:
            reasons.append({"icon": "bi-stars", "text": "Never tried"})
        elif avg >= 4.5:
            loved = "You both love it" if len(user_ids) > 1 else "You love it"
            reasons.append({"icon": "bi-heart-fill", "text": loved})
        else:
            reasons.append({"icon": "bi-star-fill", "text": f"{avg:.1f} avg"})

        latest = (
            CookingNote.objects.filter(recipe=recipe, user__in=user_ids)
            .order_by("-cooked_date")
            .first()
        )
        if latest:
            weeks = max((slot_date - latest.cooked_date).days // 7, 0)
            if weeks >= 1:
                unit = "wk" if weeks == 1 else "wks"
                reasons.append({"icon": "bi-clock-history", "text": f"{weeks} {unit} since"})

        if recipe.total_time:
            reasons.append({"icon": "bi-lightning-charge", "text": f"{recipe.total_time} min"})

        return reasons

    @staticmethod
    def latest_household_note(recipe, user):
        """Most recent CookingNote for this recipe across the household, or None."""
        user_ids = MPA._household_user_ids(user)
        return (
            CookingNote.objects.filter(recipe=recipe, user__in=user_ids)
            .order_by("-cooked_date")
            .first()
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test recipes.tests.test_suggestions -v2`
Expected: PASS (4 + 2 tests).

- [ ] **Step 5: Commit**

```bash
git add recipes/services/suggestions.py recipes/tests/test_suggestions.py
git commit -m "feat: SuggestionService — ranked single-slot picks with reason chips"
```

---

## Task 3: Tonight view, routing, nav, and templates

Add `tonight_view` as the home route, render the planned/empty hero + week strip, and switch the first nav tab to Tonight. The full grid stays at `/week/`.

**Files:**
- Create: `recipes/views/tonight.py`, `recipes/templates/tonight/tonight.html`, `recipes/templates/tonight/partials/{hero_planned,hero_empty,week_strip}.html`
- Modify: `recipes/views/__init__.py`, `recipes/urls.py`, `recipes/templates/base.html`, `recipes/tests/test_views_week.py`
- Test: `recipes/tests/test_views_tonight.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `recipes/tests/test_views_tonight.py`:

```python
from datetime import date

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from recipes.models import CookingNote, MealPlan, Recipe
from recipes.models.household import Household, HouseholdMembership


class TonightViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="t", password="pw")
        self.household = Household.objects.create(name="Home")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.recipe = Recipe.objects.create(
            user=self.user, title="Spaghetti Carbonara", steps="Cook.", cook_time=20
        )
        self.client.login(username="t", password="pw")

    def test_home_renders_tonight(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tonight/tonight.html")

    def test_planned_tonight_shows_meal_and_start_cooking(self):
        MealPlan.objects.create(
            household=self.household, added_by=self.user,
            date=date.today(), meal_type="dinner", recipe=self.recipe,
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Spaghetti Carbonara")
        self.assertContains(response, "Start Cooking")

    def test_empty_tonight_shows_suggestion_with_reason(self):
        # No meal planned today -> a confirm-or-swap suggestion should appear.
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Spaghetti Carbonara")
        self.assertContains(response, "plan tonight")  # accept button label

    def test_memory_cue_shows_last_note(self):
        MealPlan.objects.create(
            household=self.household, added_by=self.user,
            date=date.today(), meal_type="dinner", recipe=self.recipe,
        )
        CookingNote.objects.create(
            recipe=self.recipe, user=self.user, cooked_date=date.today(),
            rating=5, note="halve the chilli",
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, "halve the chilli")

    def test_no_recipes_shows_add_cta(self):
        Recipe.objects.all().delete()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add your first recipe")

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test recipes.tests.test_views_tonight -v2`
Expected: FAIL — `home` still serves `week/week.html` (template assertion fails / no suggestion markup).

- [ ] **Step 3: Implement the view**

Create `recipes/views/tonight.py`:

```python
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..models import MealPlan, Recipe
from ..models.household import get_household
from ..services.suggestions import SuggestionService
from .week import _build_week_context


def _today_day(ctx):
    return next((d for d in ctx["days"] if d["is_today"]), None)


@login_required
def tonight_view(request):
    """Home: tonight's dinner (planned or confirm-or-swap) + week strip."""
    household = get_household(request.user)
    today = timezone.localdate()
    if not household:
        return render(request, "tonight/tonight.html", {"days": [], "no_household": True})

    ctx = _build_week_context(request.user, household, offset=0)
    today_day = _today_day(ctx)
    suggestion = None
    memory = None
    if today_day and today_day["meal"]:
        memory = SuggestionService.latest_household_note(today_day["meal"].recipe, request.user)
    else:
        ranked = SuggestionService.rank_for_slot(household, request.user, today)
        suggestion = ranked[0] if ranked else None

    return render(
        request,
        "tonight/tonight.html",
        {**ctx, "today": today, "today_day": today_day,
         "suggestion": suggestion, "memory": memory,
         "exclude_for_swap": [suggestion["recipe"].pk] if suggestion else []},
    )


@login_required
def tonight_swap(request):
    """HTMX GET: return the empty hero with the next-best suggestion."""
    household = get_household(request.user)
    today = timezone.localdate()
    exclude_ids = [int(i) for i in request.GET.getlist("exclude") if i.isdigit()]
    ranked = (
        SuggestionService.rank_for_slot(household, request.user, today, exclude_ids=exclude_ids)
        if household else []
    )
    suggestion = ranked[0] if ranked else None
    exclude_for_swap = exclude_ids + ([suggestion["recipe"].pk] if suggestion else [])
    return render(
        request,
        "tonight/partials/hero_empty.html",
        {"suggestion": suggestion, "today": today, "exclude_for_swap": exclude_for_swap},
    )


@login_required
@require_POST
def tonight_accept(request):
    """HTMX POST: assign the suggested recipe to tonight, return planned hero."""
    household = get_household(request.user)
    today = timezone.localdate()
    access = Q(user=request.user) | Q(
        shared=True, user__household_membership__household=household
    )
    recipe = get_object_or_404(
        Recipe.objects.filter(access).distinct(), pk=request.POST.get("recipe_id")
    )
    MealPlan.objects.update_or_create(
        household=household, date=today, meal_type="dinner",
        defaults={"recipe": recipe, "added_by": request.user},
    )
    meal = (
        MealPlan.objects.with_related().for_household(household)
        .filter(date=today, meal_type="dinner").first()
    )
    today_day = {"date": today, "is_today": True, "meal": meal}
    memory = SuggestionService.latest_household_note(recipe, request.user)
    return render(
        request,
        "tonight/partials/hero_planned.html",
        {"today_day": today_day, "memory": memory},
    )
```

Add exports in `recipes/views/__init__.py` — add to the `from .tonight import (...)` (new import line, place it alphabetically near the others) and to `__all__`:

```python
from .tonight import tonight_accept, tonight_swap, tonight_view
```
and in `__all__` add (under a new `# Tonight` comment):
```python
    "tonight_view",
    "tonight_swap",
    "tonight_accept",
```

In `recipes/urls.py`: add the three names to the big `from .views import (...)` block, change the home route, and add the swap/accept routes. Replace:
```python
    path("", week_view, name="home"),
```
with:
```python
    path("", tonight_view, name="home"),
    path("tonight/swap/", tonight_swap, name="tonight_swap"),
    path("tonight/accept/", tonight_accept, name="tonight_accept"),
```

- [ ] **Step 4: Create the templates**

`recipes/templates/tonight/tonight.html`:
```django
{% extends "base.html" %}
{% block title %}Tonight - Meal Planner{% endblock %}
{% block nav_week %}active{% endblock %}

{% block content %}
<div class="screen">
  {% csrf_token %}

  <div class="tonight-label label" style="margin-bottom: var(--space-sm);">Tonight</div>

  <div id="tonight-hero">
    {% if no_household %}
      <p class="text-muted">No household found.</p>
    {% elif today_day and today_day.meal %}
      {% include "tonight/partials/hero_planned.html" %}
    {% else %}
      {% include "tonight/partials/hero_empty.html" %}
    {% endif %}
  </div>

  {% if days %}
  <div style="margin-top: var(--space-xl);">
    {% include "tonight/partials/week_strip.html" %}
  </div>
  {% endif %}
</div>
{% endblock %}
```

`recipes/templates/tonight/partials/hero_planned.html`:
```django
{% load recipe_extras %}
<div class="tonight-hero day-card day-card--has-meal"
     {% if today_day.meal.recipe.display_image_url %}
     style="--card-bg-image: url('{{ today_day.meal.recipe.display_image_url }}');"
     {% else %}
     style="--card-bg-gradient: {{ today_day.meal.recipe.title|recipe_gradient }};"
     {% endif %}>
  <div class="day-card__content">
    <a href="{% url 'recipe_detail' today_day.meal.recipe.pk %}"
       class="day-card__title" style="display:block; color: inherit; font-size: var(--text-xl);">
      {{ today_day.meal.recipe.title }}
    </a>

    {% if memory %}
    <div class="text-sm text-muted" style="margin-top: var(--space-xs);">
      {% if memory.rating %}<i class="bi bi-star-fill" style="color: var(--accent);"></i> {{ memory.rating }} · {% endif %}
      {% if memory.note %}Last time: &ldquo;{{ memory.note }}&rdquo;{% endif %}
    </div>
    {% endif %}

    <a href="{% url 'cook' today_day.meal.recipe.pk %}"
       class="btn btn-accent btn-full btn-lg" style="margin-top: var(--space-md);">
      <i class="bi bi-play-fill"></i> Start Cooking
    </a>

    <button class="btn btn-outline btn-full"
            style="margin-top: var(--space-sm);"
            hx-post="{% url 'cook_log' today_day.meal.recipe.pk %}"
            hx-target="body" hx-swap="beforeend">
      <i class="bi bi-check2-circle"></i> Cooked it &middot; rate
    </button>
  </div>
</div>
```

`recipes/templates/tonight/partials/hero_empty.html`:
```django
{% load recipe_extras %}
<div id="tonight-hero-inner">
{% if suggestion %}
  <div class="tonight-hero day-card day-card--has-meal"
       {% if suggestion.recipe.display_image_url %}
       style="--card-bg-image: url('{{ suggestion.recipe.display_image_url }}');"
       {% else %}
       style="--card-bg-gradient: {{ suggestion.recipe.title|recipe_gradient }};"
       {% endif %}>
    <div class="day-card__content">
      <span class="chip chip--accent" style="font-size: var(--text-xs);">Suggested for you</span>
      <div class="day-card__title" style="font-size: var(--text-xl); margin-top: var(--space-xs);">
        {{ suggestion.recipe.title }}
      </div>

      <div class="day-card__tags" style="margin-top: var(--space-sm);">
        {% for reason in suggestion.reasons %}
        <span class="chip chip--muted"><i class="bi {{ reason.icon }}"></i> {{ reason.text }}</span>
        {% endfor %}
      </div>

      <form hx-post="{% url 'tonight_accept' %}" hx-target="#tonight-hero" hx-swap="innerHTML"
            style="margin-top: var(--space-md);">
        {% csrf_token %}
        <input type="hidden" name="recipe_id" value="{{ suggestion.recipe.pk }}">
        <button type="submit" class="btn btn-accent btn-full btn-lg">
          <i class="bi bi-check-lg"></i> Looks good &mdash; plan tonight
        </button>
      </form>

      <div class="flex gap-sm" style="margin-top: var(--space-sm);">
        <button class="btn btn-outline btn-sm flex-1"
                hx-get="{% url 'tonight_swap' %}?{% for id in exclude_for_swap %}exclude={{ id }}&{% endfor %}"
                hx-target="#tonight-hero" hx-swap="innerHTML">
          <i class="bi bi-arrow-repeat"></i> Swap
        </button>
        <a href="{% url 'recipe_list' %}" class="btn btn-outline btn-sm flex-1">
          <i class="bi bi-search"></i> Browse
        </a>
      </div>
    </div>
  </div>
{% else %}
  <div class="day-card day-card--empty">
    <div class="day-card__content" style="text-align: center; padding: var(--space-lg);">
      <p class="text-muted" style="margin-bottom: var(--space-md);">Nothing planned and no suggestions yet.</p>
      <a href="{% url 'recipe_create' %}" class="btn btn-accent btn-full">
        <i class="bi bi-plus-lg"></i> Add your first recipe
      </a>
    </div>
  </div>
{% endif %}
</div>
```

`recipes/templates/tonight/partials/week_strip.html`:
```django
<div class="label" style="margin-bottom: var(--space-xs);">This week</div>
<div class="flex gap-xs">
  {% for day in days %}
  <a href="{% url 'week' %}"
     class="week-strip__day{% if day.is_today %} week-strip__day--today{% endif %}"
     style="flex:1; text-align:center; padding: var(--space-xs) 2px; border-radius: var(--radius-md);
            background: var(--bg-card); text-decoration: none; color: var(--text-muted);
            {% if day.is_today %}border: 1px solid var(--accent); color: var(--accent);{% endif %}">
    <div class="text-xs" style="font-weight:700;">{{ day.day_name|slice:":1" }}</div>
    {% if day.meal %}<i class="bi bi-circle-fill" style="font-size:5px; color: var(--primary);"></i>
    {% else %}<span class="text-xs text-dim">+</span>{% endif %}
  </a>
  {% endfor %}
</div>
```

(Tokens verified present in `app.css`: `--bg-card` #242440, `--radius-md`, `--text-dim`, `--space-xs`. Do not introduce new color literals.)

- [ ] **Step 5: Update the nav and the now-stale week home test**

In `recipes/templates/base.html`, change the first nav tab (the `{% url 'week' %}` anchor) to point at home and relabel:
```django
        <a href="{% url 'home' %}" class="nav-tab {% block nav_week %}{% endblock %}">
            <span class="nav-icon"><i class="bi bi-stars"></i></span>
            <span class="nav-label">Tonight</span>
        </a>
```

In `recipes/tests/test_views_week.py`, the `test_home_url_returns_week_view` test is now wrong (home serves Tonight). Replace its body:
```python
    def test_home_url_returns_tonight_view(self):
        """The root URL now serves the Tonight view."""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tonight/tonight.html")
```
(Rename the method too. The `/week/` tests are unaffected.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `python manage.py test recipes.tests.test_views_tonight recipes.tests.test_views_week -v2`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add recipes/views/tonight.py recipes/views/__init__.py recipes/urls.py \
        recipes/templates/tonight/ recipes/templates/base.html \
        recipes/tests/test_views_tonight.py recipes/tests/test_views_week.py
git commit -m "feat: Tonight home screen (planned + confirm-or-swap + week strip)"
```

---

## Task 4: Reusable rating fields + cook-log + rating-save

A shared rating-fields partial reused by the new Tonight bottom sheet and the existing Cook Mode finish screen. New endpoints log a cook and save a rating, both using the household access filter so a partner's shared recipe works (fixing the same 404 class on `cook_done`).

**Files:**
- Create: `recipes/templates/shared/partials/rating_fields.html`, `recipes/templates/shared/partials/rating_sheet.html`, `recipes/templates/shared/partials/rating_saved.html`
- Modify: `recipes/views/cook.py`, `recipes/views/__init__.py`, `recipes/urls.py`, `recipes/templates/cook/partials/done.html`
- Test: `recipes/tests/test_views_cook.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `recipes/tests/test_views_cook.py` (add the imports it needs at the top if absent: `from recipes.models import CookingNote`, `from recipes.models.household import Household, HouseholdMembership`):

```python
class CookLogRatingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.household = Household.objects.create(name="Home")
        self.alice = User.objects.create_user(username="alice", password="pw")
        self.bob = User.objects.create_user(username="bob", password="pw")
        HouseholdMembership.objects.create(user=self.alice, household=self.household)
        HouseholdMembership.objects.create(user=self.bob, household=self.household)
        # Bob owns a SHARED recipe; Alice cooks it.
        self.recipe = Recipe.objects.create(
            user=self.bob, title="Shared Stew", steps="Stew.", shared=True
        )
        self.client.login(username="alice", password="pw")

    def test_cook_log_creates_note_on_shared_recipe(self):
        response = self.client.post(reverse("cook_log", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        note = CookingNote.objects.get(recipe=self.recipe, user=self.alice)
        self.assertIsNone(note.rating)  # logged, not yet rated

    def test_rating_save_updates_note(self):
        note = CookingNote.objects.create(
            recipe=self.recipe, user=self.alice, cooked_date=date.today()
        )
        response = self.client.post(
            reverse("rating_save", args=[note.pk]),
            {"rating": "4", "note": "great", "would_make_again": "1"},
        )
        self.assertEqual(response.status_code, 200)
        note.refresh_from_db()
        self.assertEqual(note.rating, 4)
        self.assertEqual(note.note, "great")
        self.assertTrue(note.would_make_again)

    def test_rating_save_rejects_other_users_note(self):
        note = CookingNote.objects.create(
            recipe=self.recipe, user=self.bob, cooked_date=date.today()
        )
        response = self.client.post(reverse("rating_save", args=[note.pk]), {"rating": "5"})
        self.assertEqual(response.status_code, 404)
```

Ensure `from datetime import date` is imported in the test module.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test recipes.tests.test_views_cook.CookLogRatingTests -v2`
Expected: FAIL — `NoReverseMatch` for `cook_log` / `rating_save`.

- [ ] **Step 3: Implement the endpoints**

In `recipes/views/cook.py`, add imports at the top:
```python
from django.views.decorators.http import require_POST
```
Add a shared access helper and the two endpoints (append to the file):
```python
def _recipe_for_user(user, pk):
    """Recipe accessible to user: own, shared in household, or planned in household."""
    household = get_household(user)
    access = Q(user=user)
    if household:
        access |= Q(shared=True, user__household_membership__household=household)
        access |= Q(mealplan__household=household)
    return get_object_or_404(Recipe.objects.filter(access).distinct(), pk=pk)


@login_required
@require_POST
def cook_log(request, pk):
    """Log a cook (creates a CookingNote) and return the rating sheet."""
    recipe = _recipe_for_user(request.user, pk)
    note = CookingNote.objects.create(
        recipe=recipe,
        user=request.user,
        cooked_date=timezone.localdate(),
        rating=None,
        would_make_again=True,
    )
    return render(request, "shared/partials/rating_sheet.html", {"recipe": recipe, "note": note})


@login_required
@require_POST
def rating_save(request, note_pk):
    """Update the current user's CookingNote with rating/note/would-make-again."""
    note = get_object_or_404(CookingNote, pk=note_pk, user=request.user)
    rating = request.POST.get("rating")
    note.rating = int(rating) if rating else None
    note.note = request.POST.get("note", "").strip()
    note.would_make_again = "would_make_again" in request.POST
    note.save()
    return render(request, "shared/partials/rating_saved.html", {"recipe": note.recipe, "note": note})
```

Fix `cook_done`'s access filter (same 404 class). Replace its first line:
```python
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
```
with:
```python
    recipe = _recipe_for_user(request.user, pk)
```

Export in `recipes/views/__init__.py` — change the cook import and `__all__`:
```python
from .cook import cook_done, cook_log, cook_step, cook_view, rating_save
```
add to `__all__` under `# Cook`:
```python
    "cook_log",
    "rating_save",
```

In `recipes/urls.py` add the names to the `from .views import (...)` block and the routes (near the cook routes):
```python
    path("cook/<int:pk>/log/", cook_log, name="cook_log"),
    path("rating/<int:note_pk>/", rating_save, name="rating_save"),
```

- [ ] **Step 4: Create the shared partials**

`recipes/templates/shared/partials/rating_fields.html` (the reusable inner form fields — stars, note, make-again):
```django
<div style="margin-bottom: var(--space-lg);" x-data="{ rating: {{ note.rating|default:0 }} }">
  <label class="form-label">Rating</label>
  <div style="display: flex; gap: var(--space-sm); justify-content: center; font-size: 32px;">
    {% for i in "12345" %}
    <label style="cursor: pointer;">
      <input type="radio" name="rating" value="{{ forloop.counter }}" style="display:none;"
             x-on:click="rating = {{ forloop.counter }}">
      <span :style="rating >= {{ forloop.counter }} ? 'color: var(--accent)' : 'color: var(--text-dim)'"
            style="transition: color 0.2s;"><i class="bi" :class="rating >= {{ forloop.counter }} ? 'bi-star-fill' : 'bi-star'"></i></span>
    </label>
    {% endfor %}
  </div>
</div>

<div style="margin-bottom: var(--space-lg);">
  <label for="note" class="form-label">Notes</label>
  <textarea id="note" name="note" rows="2" class="form-input"
            placeholder="e.g. halve the chilli">{{ note.note }}</textarea>
</div>

<div style="margin-bottom: var(--space-lg);">
  <label style="display:flex; align-items:center; gap: var(--space-sm); cursor:pointer;">
    <input type="checkbox" name="would_make_again" value="1" {% if note.would_make_again or not note %}checked{% endif %}
           style="width:20px; height:20px; accent-color: var(--primary);">
    <span style="color: var(--text-main);">Would make again</span>
  </label>
</div>
```

`recipes/templates/shared/partials/rating_sheet.html` (bottom-sheet overlay mirroring the suggestions overlay):
```django
<div class="rating-overlay" x-data="{ show: true }" x-show="show"
     style="position: fixed; inset: 0; background: rgba(0,0,0,0.55); z-index: 250;
            display: flex; align-items: flex-end; justify-content: center;">
  <div style="background: var(--bg); border-radius: var(--radius-lg) var(--radius-lg) 0 0;
              width: 100%; max-width: 600px; padding: var(--space-lg) var(--space-lg) var(--space-2xl);">
    <div class="flex justify-between items-center mb-md">
      <div>
        <h2 style="margin:0; font-size: var(--text-lg); font-weight:800;">How was it?</h2>
        <p class="text-muted text-sm">{{ recipe.title }} &middot; logged <i class="bi bi-check2" style="color: var(--primary);"></i></p>
      </div>
      <button class="btn btn-ghost btn-sm" @click="show=false; $el.closest('.rating-overlay').remove()">
        <i class="bi bi-x-lg"></i>
      </button>
    </div>

    <form hx-post="{% url 'rating_save' note.pk %}"
          hx-target=".rating-overlay" hx-swap="outerHTML">
      {% csrf_token %}
      {% include "shared/partials/rating_fields.html" %}
      <button type="submit" class="btn btn-accent btn-full btn-lg">Save</button>
    </form>
  </div>
</div>
```

`recipes/templates/shared/partials/rating_saved.html` (confirmation that auto-dismisses):
```django
<div x-data="{ show: true }" x-show="show" x-init="setTimeout(() => show = false, 1500)"
     style="position: fixed; inset: 0; background: rgba(0,0,0,0.55); z-index: 250;
            display: flex; align-items: center; justify-content: center;">
  <div style="background: var(--bg); border-radius: var(--radius-lg); padding: var(--space-xl); text-align:center;">
    <div style="font-size: 40px; color: var(--accent);"><i class="bi bi-check-circle-fill"></i></div>
    <p style="margin-top: var(--space-sm); color: var(--text-main);">Saved &mdash; thanks!</p>
  </div>
</div>
```

- [ ] **Step 5: Reuse the fields in Cook Mode finish**

In `recipes/templates/cook/partials/done.html`, replace the three inline blocks (the star-rating `div`, the note `div`, and the would-make-again `div` — lines ~11-41) with a single include, keeping the surrounding `<form>` and submit button:
```django
  <form method="post" action="{% url 'cook_done' recipe.pk %}">
    {% csrf_token %}
    {% include "shared/partials/rating_fields.html" %}
    <button type="submit" class="btn btn-primary btn-full btn-lg">Save &amp; Finish</button>
  </form>
```
`note` is undefined in this Cook Mode context, so `{{ note.rating|default:0 }}` → 0 (no stars pre-selected) and the checkbox's `{% if note.would_make_again or not note %}` → `not note` is truthy → **checked by default**, preserving the current behaviour. No `with` argument needed.

- [ ] **Step 6: Wire "Cooked it" already done in Task 3**

The Tonight planned hero (Task 3) already posts to `cook_log` with `hx-target="body" hx-swap="beforeend"`, appending the rating sheet. No extra work — just confirm it renders by eye in Task 5's smoke test.

- [ ] **Step 7: Run tests to verify they pass**

Run: `python manage.py test recipes.tests.test_views_cook -v2`
Expected: PASS (new `CookLogRatingTests` + existing cook tests).

- [ ] **Step 8: Commit**

```bash
git add recipes/views/cook.py recipes/views/__init__.py recipes/urls.py \
        recipes/templates/shared/ recipes/templates/cook/partials/done.html \
        recipes/tests/test_views_cook.py
git commit -m "feat: one-tap cook log + reusable rating sheet (household-safe)"
```

---

## Task 5: Integration, polish, and full verification

Confirm the whole loop holds together, formatting/lint pass, and the full suite is green.

**Files:** none new (verification + any small fixes surfaced).

- [ ] **Step 1: Format and lint**

Run: `black . && isort . && flake8`
Expected: black/isort reformat as needed; flake8 reports no errors (config in `setup.cfg`). Fix any flagged issues (unused imports, line length).

- [ ] **Step 2: Run the full unit/integration suite**

Run: `python manage.py test recipes --exclude-tag e2e` (or enumerate non-e2e modules as the project does). If no tag is configured, run: `python manage.py test recipes.tests.test_household_scoring recipes.tests.test_suggestions recipes.tests.test_views_tonight recipes.tests.test_views_week recipes.tests.test_views_cook recipes.tests.test_services recipes.tests.test_services_new recipes.tests.test_meal_planner recipes.tests.test_models recipes.tests.test_models_new recipes.tests.test_views recipes.tests.test_views_recipes recipes.tests.test_views_shop recipes.tests.test_urls recipes.tests.test_forms recipes.tests.test_integration -v1`
Expected: OK, 0 failures.

- [ ] **Step 3: Manual smoke test**

```bash
python manage.py runserver 127.0.0.1:8011
```
Then, logged in as a user with a household and ≥1 recipe, verify by eye:
1. `/` shows Tonight. With no dinner planned → a "Suggested for you" card with reason chips, **Looks good — plan tonight**, **Swap**, **Browse**.
2. Click **Swap** → a different suggestion appears (or the same one if only one recipe).
3. Click **Looks good** → the hero swaps to the planned state with **Start Cooking** + **Cooked it · rate**.
4. Click **Cooked it · rate** → the bottom sheet slides up; set stars + note; **Save** → "Saved — thanks!" confirmation.
5. Reload `/` → the planned hero now shows the memory cue ("★N · Last time: …").
6. The week strip shows 7 days with today highlighted; tapping a day opens `/week/` (full grid intact).
7. Bottom nav first tab reads **Tonight** and is active.

Stop the server: `pkill -f "runserver 127.0.0.1:8011"`.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: Tonight Loop — formatting, lint, and integration polish"
```

---

## Spec coverage check

| Spec requirement | Task |
|---|---|
| Tonight screen as home (layout A: hero + week strip) | 3 |
| Confirm-or-Swap empty state | 3, 4 |
| Self-explaining reason chips | 2, 3 |
| One-tap "Cooked it" + bottom-sheet rating (reusable) | 4 |
| Household-wide scoring | 1 |
| Memory cue from latest CookingNote | 2, 3 |
| No new models/migrations | (all — none added) |
| Household access fix on rating/cook surfaces | 4 |
| Existing suite stays green | 1, 5 |

## Notes for the implementer

- **Per-candidate scoring is N+1** over the household's recipes. For a couple's cookbook (tens of recipes) this is fine and matches the existing `week_suggest`. Do not prematurely optimise.
- **CSS tokens** (all verified present in `app.css`): surfaces use `--bg-card`; radii `--radius-sm/md/lg`; text `--text-xs/sm/lg/xl`, `--text-main/muted/dim`; spacing `--space-xs…2xl`; colors `--primary`, `--accent`, `--danger`. Never introduce new color literals.
- **Determinism:** `rank_for_slot` sorts by `(score, id)` so Swap walks predictably; tests rely on this.
- **Deferred (do NOT build here):** haptics, View Transitions, offline caching, cook timer, push, planned-by/who's-cooking, share-to-import, onboarding, taste profile, favourite-404 fix.
