# AI Recipe Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate batches of AI-powered recipes from user taste preferences, with a first-time onboarding modal and a permanent Settings entry point.

**Architecture:** A preference selection page posts chosen cuisines/proteins/styles to the session. A progress page polls an HTMX endpoint that generates one recipe per call via Claude Haiku, saving each immediately. Poll-based approach avoids streaming complexity while giving real-time feedback.

**Tech Stack:** Django 5.2, HTMX 2.x (polling), Alpine.js 3.x (chip selection), Anthropic Claude Haiku, existing AIService

**Spec:** `docs/superpowers/specs/2026-03-30-recipe-generator-design.md`

---

## File Structure

### New Files

```
recipes/views/generate.py                              — batch generation views (preferences, progress, next)
recipes/templates/recipes/generate.html                 — preference selection page
recipes/templates/recipes/generate_progress.html        — progress page with polling
recipes/templates/recipes/partials/generate_item.html   — single recipe card in progress list
recipes/templates/recipes/partials/generate_complete.html — completion state
recipes/tests/test_generate.py                          — tests
```

### Modified Files

```
recipes/views/__init__.py         — export new views
recipes/urls.py                   — add generate URLs
recipes/templates/recipes/list.html    — first-time onboarding modal
recipes/templates/settings/settings.html — "Generate Recipes" section
```

---

## Task 1: Generate Views — Preferences + Session Storage

**Files:**
- Create: `recipes/views/generate.py`
- Create: `recipes/templates/recipes/generate.html`
- Modify: `recipes/views/__init__.py`
- Modify: `recipes/urls.py`
- Create: `recipes/tests/test_generate.py`

- [ ] **Step 1: Create generate.py with preference selection view**

Create `recipes/views/generate.py`:

```python
import json
import logging
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render

from ..models import Ingredient, Recipe, RecipeIngredient, Tag
from ..services.ai_service import AIService, AIServiceException

logger = logging.getLogger(__name__)

CUISINE_OPTIONS = [
    "Italian", "Asian", "Mexican", "Mediterranean", "Indian", "Japanese",
    "Middle Eastern", "French", "Korean", "American", "Thai", "Greek",
]
PROTEIN_OPTIONS = ["Chicken", "Beef", "Pork", "Seafood", "Lamb", "Tofu", "Eggs"]
DIETARY_OPTIONS = ["Vegetarian", "Vegan", "Gluten-free", "Dairy-free", "Low-carb"]
STYLE_OPTIONS = [
    "Quick weeknight", "Slow cook", "One-pot", "BBQ / Grill",
    "Meal prep", "Comfort food", "Healthy / Light",
]
AVOID_OPTIONS = ["Spicy", "Mushrooms", "Olives", "Shellfish", "Offal", "Raw fish", "Nuts"]
COUNT_OPTIONS = [5, 10, 15, 20]


@login_required
def generate_preferences(request):
    """GET: show preference selection page. POST: store preferences, redirect to progress."""
    if request.method == "POST":
        request.session["gen_cuisines"] = request.POST.getlist("cuisines")
        request.session["gen_proteins"] = request.POST.getlist("proteins")
        request.session["gen_dietary"] = request.POST.getlist("dietary")
        request.session["gen_styles"] = request.POST.getlist("styles")
        request.session["gen_avoid"] = request.POST.getlist("avoid")
        count = int(request.POST.get("count", 10))
        request.session["gen_count"] = min(count, 20)
        request.session["gen_completed"] = 0
        request.session["gen_titles"] = []
        return redirect("generate_progress")

    return render(request, "recipes/generate.html", {
        "cuisines": CUISINE_OPTIONS,
        "proteins": PROTEIN_OPTIONS,
        "dietary": DIETARY_OPTIONS,
        "styles": STYLE_OPTIONS,
        "avoid": AVOID_OPTIONS,
        "counts": COUNT_OPTIONS,
    })


@login_required
def generate_progress(request):
    """Show the progress page that polls for recipe generation."""
    count = request.session.get("gen_count", 0)
    completed = request.session.get("gen_completed", 0)
    if not count:
        return redirect("generate_preferences")
    return render(request, "recipes/generate_progress.html", {
        "total": count,
        "completed": completed,
    })


@login_required
def generate_next(request):
    """HTMX endpoint: generate one recipe, return card + trigger next poll."""
    count = request.session.get("gen_count", 0)
    completed = request.session.get("gen_completed", 0)
    titles = request.session.get("gen_titles", [])

    if completed >= count:
        request.session.pop("gen_count", None)
        request.session.pop("gen_completed", None)
        request.session.pop("gen_titles", None)
        request.session.pop("gen_cuisines", None)
        request.session.pop("gen_proteins", None)
        request.session.pop("gen_dietary", None)
        request.session.pop("gen_styles", None)
        request.session.pop("gen_avoid", None)
        return render(request, "recipes/partials/generate_complete.html", {
            "total": count,
        })

    # Build prompt from preferences
    cuisines = request.session.get("gen_cuisines", [])
    proteins = request.session.get("gen_proteins", [])
    dietary = request.session.get("gen_dietary", [])
    styles = request.session.get("gen_styles", [])
    avoid = request.session.get("gen_avoid", [])

    # Also get existing recipe titles to avoid duplicates
    existing_titles = list(Recipe.objects.filter(user=request.user).values_list("title", flat=True))
    all_titles = existing_titles + titles

    prompt_parts = ["Generate a unique family-friendly dinner recipe."]
    if cuisines:
        prompt_parts.append(f"Cuisines: {', '.join(cuisines)}")
    if proteins:
        prompt_parts.append(f"Proteins: {', '.join(proteins)}")
    if dietary:
        prompt_parts.append(f"Dietary: {', '.join(dietary)}")
    if styles:
        prompt_parts.append(f"Cooking style: {', '.join(styles)}")
    if avoid:
        prompt_parts.append(f"Avoid these: {', '.join(avoid)}")
    if all_titles:
        prompt_parts.append(f"Must be different from: {', '.join(all_titles[-30:])}")

    prompt = "\n".join(prompt_parts)

    try:
        data = AIService.generate_structured_recipe(prompt)

        # Save recipe
        recipe = Recipe.objects.create(
            user=request.user,
            title=data.get("title", f"Recipe {completed + 1}"),
            description=data.get("description", ""),
            prep_time=data.get("prep_time"),
            cook_time=data.get("cook_time"),
            servings=data.get("servings", 4),
            difficulty=data.get("difficulty", "medium"),
            source="ai",
            is_ai_generated=True,
            steps="\n".join(data.get("steps", [])),
        )

        # Save structured ingredients
        for i, ing_data in enumerate(data.get("ingredients", [])):
            ingredient, _ = Ingredient.objects.get_or_create(
                name=ing_data.get("name", "").lower().strip(),
                defaults={"category": ing_data.get("category", "other")},
            )
            qty = ing_data.get("quantity")
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                quantity=Decimal(str(qty)) if qty else None,
                unit=ing_data.get("unit", ""),
                preparation_notes=ing_data.get("preparation_notes", ""),
                order=i,
            )

        # Auto-tag based on preferences
        for cuisine in cuisines:
            tag, _ = Tag.objects.get_or_create(name=cuisine, defaults={"tag_type": "cuisine"})
            # Only add tag if the recipe title/description suggests it matches
            recipe.tags.add(tag)

        # Update session progress
        titles.append(recipe.title)
        request.session["gen_completed"] = completed + 1
        request.session["gen_titles"] = titles

        return render(request, "recipes/partials/generate_item.html", {
            "recipe": recipe,
            "completed": completed + 1,
            "total": count,
            "done": (completed + 1) >= count,
        })

    except AIServiceException as e:
        logger.error(f"Recipe generation failed: {e}")
        # Skip this one, increment counter, try next
        request.session["gen_completed"] = completed + 1
        return render(request, "recipes/partials/generate_item.html", {
            "error": str(e),
            "completed": completed + 1,
            "total": count,
            "done": (completed + 1) >= count,
        })
```

- [ ] **Step 2: Create preference selection template**

Create `recipes/templates/recipes/generate.html`:

The page extends base.html with nav_recipes active. Uses Alpine.js `x-data` to manage selected chips. Each category rendered as a section with tappable `.filter-chip` elements. Form POSTs selected values. Includes the quantity selector (5/10/15/20) and a "Generate X Recipes" submit button.

Key Alpine.js pattern for chip selection:
```html
<div x-data="{ selected: [] }">
  {% for item in cuisines %}
  <button type="button" class="filter-chip"
          :class="{ 'active': selected.includes('{{ item }}') }"
          @click="selected.includes('{{ item }}') ? selected = selected.filter(x => x !== '{{ item }}') : selected.push('{{ item }}')">
    {{ item }}
  </button>
  <input type="hidden" name="cuisines" :value="'{{ item }}'" x-show="selected.includes('{{ item }}')">
  {% endfor %}
</div>
```

Actually, hidden inputs with `x-show` won't submit when hidden. Better approach — use a single hidden input with JSON, or use checkboxes:

```html
{% for item in cuisines %}
<label class="filter-chip" :class="{ 'active': cuisines.includes('{{ item }}') }"
       @click="cuisines.includes('{{ item }}') ? cuisines = cuisines.filter(x => x !== '{{ item }}') : cuisines.push('{{ item }}')"
       style="cursor: pointer;">
  <input type="checkbox" name="cuisines" value="{{ item }}" style="display: none;"
         :checked="cuisines.includes('{{ item }}')">
  {{ item }}
</label>
{% endfor %}
```

This uses hidden checkboxes that are checked/unchecked by Alpine — they submit normally in the form.

The "Avoid" section uses danger-coloured chips (red tint when selected).

The quantity selector uses radio buttons styled as chips.

- [ ] **Step 3: Create progress page template**

Create `recipes/templates/recipes/generate_progress.html`:

Extends base.html. Shows:
- Header: "Generating recipes..." with count
- Progress bar (reuse `.cook-progress` CSS)
- An empty `<div id="recipe-list">` that gets items appended via HTMX
- Initial HTMX trigger that starts polling: `<div hx-get="/recipes/generate-batch/next/" hx-trigger="load delay:500ms" hx-target="#recipe-list" hx-swap="beforeend"></div>`

- [ ] **Step 4: Create generate_item partial**

Create `recipes/templates/recipes/partials/generate_item.html`:

Shows one generated recipe as a card (title, cook time, difficulty). If `done` is False, includes an HTMX trigger for the next poll:
```html
<div class="day-card" style="border-left-color: var(--primary);">
  <div class="day-card__content">
    ...recipe info...
  </div>
</div>

<!-- Progress update -->
<div id="gen-progress" hx-swap-oob="innerHTML">
  {{ completed }} of {{ total }}
</div>
<div id="gen-bar" hx-swap-oob="innerHTML">
  <div class="cook-progress__fill" style="width: {% widthratio completed total 100 %}%;"></div>
</div>

{% if not done %}
<div hx-get="{% url 'generate_next' %}" hx-trigger="load delay:1s" hx-target="#recipe-list" hx-swap="beforeend"></div>
{% else %}
<div hx-get="{% url 'generate_next' %}" hx-trigger="load delay:500ms" hx-target="#recipe-list" hx-swap="beforeend"></div>
{% endif %}
```

When `done` is True, the next call returns `generate_complete.html` instead.

- [ ] **Step 5: Create generate_complete partial**

Create `recipes/templates/recipes/partials/generate_complete.html`:

```html
<div id="gen-progress" hx-swap-oob="innerHTML">Done!</div>
<div id="gen-bar" hx-swap-oob="innerHTML">
  <div class="cook-progress__fill" style="width: 100%;"></div>
</div>
<div style="text-align: center; padding: var(--space-xl) 0;">
  <div style="font-size: 36px; margin-bottom: var(--space-md);">🎉</div>
  <h3 style="color: var(--text-main);">{{ total }} recipes added!</h3>
  <p class="text-muted text-sm mb-lg">Your cookbook is stocked and ready to go.</p>
  <a href="{% url 'recipe_list' %}" class="btn btn-primary btn-lg">View Your Recipes</a>
</div>
```

- [ ] **Step 6: Add URLs and exports**

Add to `recipes/urls.py`:
```python
path("recipes/generate-batch/", generate_preferences, name="generate_preferences"),
path("recipes/generate-batch/progress/", generate_progress, name="generate_progress"),
path("recipes/generate-batch/next/", generate_next, name="generate_next"),
```

Update `recipes/views/__init__.py` to export `generate_preferences`, `generate_progress`, `generate_next`.

- [ ] **Step 7: Write tests**

Create `recipes/tests/test_generate.py`:

```python
class GeneratePreferencesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", password="testpass123")
        self.household = Household.objects.create(name="Test")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_preferences_page_returns_200(self):
        response = self.client.get(reverse("generate_preferences"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Italian")
        self.assertContains(response, "Chicken")

    def test_preferences_post_stores_session(self):
        response = self.client.post(reverse("generate_preferences"), {
            "cuisines": ["Italian", "Asian"],
            "proteins": ["Chicken"],
            "count": "5",
        })
        self.assertEqual(response.status_code, 302)
        session = self.client.session
        self.assertEqual(session["gen_cuisines"], ["Italian", "Asian"])
        self.assertEqual(session["gen_count"], 5)

    def test_preferences_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("generate_preferences"))
        self.assertEqual(response.status_code, 302)

    def test_count_capped_at_20(self):
        self.client.post(reverse("generate_preferences"), {"count": "50"})
        self.assertEqual(self.client.session["gen_count"], 20)

    def test_progress_redirects_without_session(self):
        response = self.client.get(reverse("generate_progress"))
        self.assertEqual(response.status_code, 302)

    @patch("recipes.views.generate.AIService.generate_structured_recipe")
    def test_generate_next_creates_recipe(self, mock_generate):
        mock_generate.return_value = {
            "title": "Test Recipe",
            "description": "A test",
            "prep_time": 10,
            "cook_time": 20,
            "servings": 4,
            "difficulty": "easy",
            "ingredients": [{"name": "chicken", "quantity": 500, "unit": "g", "category": "meat", "preparation_notes": ""}],
            "steps": ["Cook it"],
        }
        session = self.client.session
        session["gen_count"] = 2
        session["gen_completed"] = 0
        session["gen_titles"] = []
        session["gen_cuisines"] = ["Italian"]
        session["gen_proteins"] = []
        session["gen_dietary"] = []
        session["gen_styles"] = []
        session["gen_avoid"] = []
        session.save()

        response = self.client.get(reverse("generate_next"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Recipe.objects.filter(title="Test Recipe").exists())
        self.assertEqual(self.client.session["gen_completed"], 1)

    @patch("recipes.views.generate.AIService.generate_structured_recipe")
    def test_generate_next_returns_complete_when_done(self, mock_generate):
        session = self.client.session
        session["gen_count"] = 1
        session["gen_completed"] = 1
        session["gen_titles"] = ["Test"]
        session.save()

        response = self.client.get(reverse("generate_next"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "recipes added")
```

- [ ] **Step 8: Verify and commit**

```bash
python manage.py check
python manage.py test recipes.tests.test_generate -v2
```

Commit: `feat: AI recipe generator with preference chips and progress polling`

---

## Task 2: First-Time Onboarding Modal + Settings Entry Point

**Files:**
- Modify: `recipes/templates/recipes/list.html`
- Modify: `recipes/templates/settings/settings.html`

- [ ] **Step 1: Add onboarding modal to recipe list**

In `recipes/templates/recipes/list.html`, add an Alpine.js overlay that shows when there are zero recipes:

```html
{% if page_obj.paginator.count == 0 and not query and not selected_tag and not favourites_only %}
<div x-data="{ show: true }" x-show="show" x-transition
     style="position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 200; display: flex; align-items: center; justify-content: center; padding: var(--space-lg);">
  <div style="background: var(--bg-card); border-radius: var(--radius-lg); padding: var(--space-2xl); max-width: 340px; text-align: center;">
    <div style="font-size: 48px; margin-bottom: var(--space-lg);">📖</div>
    <h2 style="color: var(--text-main); margin-bottom: var(--space-sm);">Your cookbook is empty!</h2>
    <p class="text-muted mb-xl">Let's stock it with recipes tailored to your taste.</p>
    <a href="{% url 'generate_preferences' %}" class="btn btn-primary btn-full btn-lg mb-md">
      <i class="bi bi-stars"></i> Get Started
    </a>
    <button class="btn btn-ghost btn-full" @click="show = false">I'll add my own</button>
  </div>
</div>
{% endif %}
```

- [ ] **Step 2: Add generate section to Settings**

In `recipes/templates/settings/settings.html`, add before the Meal Templates section:

```html
<!-- Generate Recipes -->
<div style="padding: var(--space-lg); background: var(--bg-card); border-radius: var(--radius-md); margin-bottom: var(--space-xl);">
  <div class="section-header">
    <h2 class="section-title" style="margin-bottom: var(--space-md);">Generate Recipes</h2>
  </div>
  <p class="text-muted text-sm mb-md">Use AI to generate a batch of recipes based on your taste preferences.</p>
  <a href="{% url 'generate_preferences' %}" class="btn btn-primary btn-full">
    <i class="bi bi-stars"></i> Generate More Recipes
  </a>
</div>
```

- [ ] **Step 3: Run all tests and commit**

```bash
python manage.py test recipes -v0
```

Commit: `feat: first-time onboarding modal and Settings entry point for recipe generator`

---

## Task 3: Deploy and Verify

- [ ] **Step 1: Format code**

```bash
black recipes/ config/ --line-length 120
isort recipes/ config/ --profile black --line-length 120
flake8 recipes/ config/ --max-line-length=120
```

- [ ] **Step 2: Run full test suite**

```bash
python manage.py test recipes -v0
```

- [ ] **Step 3: Commit and deploy**

```bash
git push origin main
railway up --detach
```

---

## Summary

| Task | Component | Key Deliverable |
|------|-----------|-----------------|
| 1 | Generate views + templates | Preference selection, progress page, HTMX polling, recipe creation |
| 2 | Entry points | First-time modal on empty recipe list, Settings generate button |
| 3 | Deploy | Format, test, push, deploy to Railway |
