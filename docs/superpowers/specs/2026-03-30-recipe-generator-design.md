# AI Recipe Generator — Design Spec

**Date:** 2026-03-30
**Status:** Approved

## Overview

Generate a batch of recipes tailored to user preferences using AI. Solves the "empty house" problem for new users and lets existing users quickly expand their cookbook.

## Entry Points

### 1. First-time modal (Recipes page)
When a user with zero recipes visits `/recipes/`, show a full-screen overlay:
- "Your cookbook is empty! Let's stock it with recipes tailored to your taste."
- "Get Started" button → opens the generator
- "I'll add my own" dismisses the modal

### 2. Settings page
Permanent "Generate Recipes" section with a "Generate More Recipes" button. Always available.

## Preference Selection

One scrollable page with tappable chips grouped by category. Selected chips highlighted in teal, deselected greyed out. Uses existing `.filter-chip` CSS pattern.

### Categories

**Cuisines:** Italian, Asian, Mexican, Mediterranean, Indian, Japanese, Middle Eastern, French, Korean, American, Thai, Greek

**Proteins:** Chicken, Beef, Pork, Seafood, Lamb, Tofu, Eggs

**Dietary:** Vegetarian, Vegan, Gluten-free, Dairy-free, Low-carb

**Cooking Style:** Quick weeknight, Slow cook, One-pot, BBQ/Grill, Meal prep, Comfort food, Healthy/Light

**Avoid:** Spicy, Mushrooms, Olives, Shellfish, Offal, Raw fish, Nuts (displayed in red/danger colour)

### Quantity Selector
Choose: 5 / 10 / 15 / 20 (max 20). Default 10.

No data model for preferences — selections are sent directly to the AI prompt each time.

## Generation Flow

### Poll-based approach

1. User selects preferences and taps "Generate X Recipes"
2. POST to `/recipes/generate-batch/` stores preferences and count in session, redirects to progress page
3. Progress page at `/recipes/generate-batch/progress/` renders UI with progress bar and empty recipe list
4. HTMX polls `/recipes/generate-batch/next/` every 3 seconds via `hx-trigger="load delay:1s"`
5. Each call to `/next/` generates ONE recipe via Claude Haiku, saves it to DB, returns:
   - The recipe card HTML (appended to the list)
   - Updated progress count
   - If more remain, includes `hx-get` trigger for next poll
   - If done, returns a "Complete!" message with "View Your Recipes" button
6. Recipes are saved immediately — if user navigates away mid-generation, completed recipes are kept

### AI Prompt

```
Generate a unique family-friendly dinner recipe.

Preferences:
- Cuisines: Italian, Asian
- Proteins: Chicken, Seafood
- Styles: Quick weeknight, One-pot
- Dietary: None specified
- Avoid: Spicy, Mushrooms

Return JSON with this exact structure:
{"title": "...", "description": "...", "prep_time": 10, "cook_time": 30,
 "servings": 4, "difficulty": "easy|medium|hard",
 "ingredients": [{"name": "...", "quantity": 500, "unit": "g",
  "category": "meat", "preparation_notes": "diced"}],
 "steps": ["Step 1", "Step 2"]}

Important: Make this recipe different from: [Chicken Stir Fry, Pasta Carbonara, ...]
Return ONLY valid JSON.
```

The "different from" list includes all titles generated in the current batch plus existing recipe titles in the user's collection.

### Recipe Creation

Each generated recipe is saved with:
- `user=request.user`
- `source="ai"`
- `is_ai_generated=True`
- `shared=False` (user can share later)
- Structured ingredients created via `Ingredient.objects.get_or_create()` and `RecipeIngredient.objects.create()`
- Tags auto-assigned from the preference categories selected (match cuisine/style to existing Tag objects)

## Endpoints

```
GET  /recipes/generate-batch/           — preference selection page
POST /recipes/generate-batch/           — store preferences in session, redirect to progress
GET  /recipes/generate-batch/progress/  — progress page (renders UI)
GET  /recipes/generate-batch/next/      — HTMX: generate one recipe, return card + progress
```

## Templates

### `recipes/templates/recipes/generate.html`
Full page with preference chips (extends base.html). Alpine.js manages chip selection state. Form POSTs selected values.

### `recipes/templates/recipes/generate_progress.html`
Progress page: header with count ("Generating 3 of 10..."), progress bar, recipe list that grows as items are polled. Each item shows title, cook time, difficulty.

### `recipes/templates/recipes/partials/generate_item.html`
Single generated recipe in the progress list: title, cook time, tags, with a link to the recipe detail.

### `recipes/templates/recipes/partials/generate_complete.html`
Final state: "All done! X recipes added to your cookbook." with "View Your Recipes" button.

### Update `recipes/templates/recipes/list.html`
Add first-time modal (Alpine.js `x-data` checks recipe count, shows overlay if zero).

### Update `recipes/templates/settings/settings.html`
Add "Generate Recipes" section with button linking to `/recipes/generate-batch/`.

## Files

### New:
- `recipes/views/generate.py` — batch generation views
- `recipes/templates/recipes/generate.html` — preference selection
- `recipes/templates/recipes/generate_progress.html` — progress UI
- `recipes/templates/recipes/partials/generate_item.html` — recipe card in progress list
- `recipes/templates/recipes/partials/generate_complete.html` — completion state
- `recipes/tests/test_generate.py` — tests

### Modified:
- `recipes/views/__init__.py` — export new views
- `recipes/urls.py` — add generate URLs
- `recipes/templates/recipes/list.html` — first-time modal
- `recipes/templates/settings/settings.html` — generate section
- `recipes/services/ai_service.py` — reuse `generate_structured_recipe` (already exists)
