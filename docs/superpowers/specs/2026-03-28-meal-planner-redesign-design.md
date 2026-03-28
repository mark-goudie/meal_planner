# Meal Planner Redesign — Design Spec

**Date:** 2026-03-28
**Status:** Approved
**Approach:** Option C — Enhanced Django with HTMX + Alpine.js

## Overview

Redesign the existing Django meal planner from a desktop-first template app into a mobile-first, app-like experience. The core value proposition is a "living cookbook" — an app that captures not just recipes but the accumulated experience of cooking them, becoming more valuable over time. AI assists with inspiration and gap-filling but does not drive the app.

**Primary users:** Mark and his wife, planning weekly family meals on their phones.
**Primary contexts:** Couch (planning), kitchen (cooking), supermarket (shopping).
**Build philosophy:** Design for two, architect for many.

## Information Architecture

Five core screens, navigated via a bottom tab bar (thumb-reachable, phone-native):

| Tab | Screen | Purpose |
|-----|--------|---------|
| **This Week** | Weekly meal plan | Home screen. Mon→Sun at a glance. Tap to assign, long-press to rearrange, swipe to remove. |
| **Recipes** | Recipe collection | The living cookbook. Search, filter, browse. Each recipe carries its history and notes. |
| **Cook** | Cooking mode | Opened from a recipe. Step-by-step with inline quantities. Screen stays on. |
| **Shop** | Shopping list | Generated from meal plan + manual items. Tick off at the store. |
| **More** | Settings/profile | Preferences, dietary restrictions, AI settings. |

### Key Flows

- **Weekly planning:** This Week → tap empty slot → browse/search Recipes → select → done (HTMX swap, no page reload)
- **Cooking:** This Week → tap tonight's meal → "Start Cooking" → Cooking Mode
- **Post-cook feedback:** Cooking Mode → "Done" → quick rating + optional note
- **Shopping:** This Week → "Generate Shopping List" → Shop tab with items grouped by category
- **Adding recipes:** Recipes → "+" → manual entry OR "Ask AI for ideas" → recipe saved with structured ingredients
- **Rearranging:** Long-press & drag meals between days. Swipe left to remove/swap.

## Data Model

### New Models

**`Ingredient`**
- `name` — CharField(100), unique. E.g. "cumin", "chicken breast"
- `category` — CharField with choices: Produce, Dairy, Meat & Protein, Pantry Staples, Spices & Seasonings, Frozen, Bakery, Other
- Grows organically as recipes are added. AI can suggest categories.

**`RecipeIngredient`**
- `recipe` — FK(Recipe, CASCADE)
- `ingredient` — FK(Ingredient, CASCADE)
- `quantity` — DecimalField (nullable for "to taste" items)
- `unit` — CharField with choices: g, kg, ml, L, tsp, tbsp, cup, piece, bunch, pinch, to taste
- `preparation_notes` — CharField (optional). E.g. "finely diced", "room temperature"
- `order` — PositiveIntegerField for display ordering

**`CookingNote`**
- `recipe` — FK(Recipe, CASCADE)
- `user` — FK(User, CASCADE)
- `cooked_date` — DateField
- `rating` — IntegerField (1–5 stars)
- `note` — TextField (optional free text)
- `would_make_again` — BooleanField (default True)
- `created_at` — DateTimeField (auto_now_add)

### Modified Models

**`Recipe`**
- Drop: `ingredients` TextField (replaced by RecipeIngredient M2M)
- Add: `source` — CharField with choices: manual, ai, url, family
- Add: `cooking_mode_steps` — JSONField storing steps with ingredient references for cooking mode. Structure: `[{"step": "Fry the guanciale until crispy", "ingredients": [{"ingredient_id": 5, "text": "guanciale (200g, cubed)"}], "timer_minutes": 10}]`
- Keep: title, description, steps (plain text fallback), author, prep_time, cook_time, servings, difficulty, image, is_ai_generated, tags M2M, favourited_by M2M, created_at, updated_at

**`MealPlan`**
- Add: `notes` — TextField (optional). Per-slot notes like "use leftover chicken from Monday"
- Keep: user FK, date, meal_type, recipe FK, unique constraint (user, date, meal_type)

**`Tag`** (merged with DietaryRestriction)
- Add: `tag_type` — CharField with choices: dietary, cuisine, method, time
- Keep: name (unique)

### Removed Models

- `FamilyPreference` — replaced by CookingNote (richer: free text + rating + would_make_again)
- `GeneratedMealPlan` / `GeneratedMealPlanEntry` — AI suggestions go directly into MealPlan slots rather than a parallel data structure
- `DietaryRestriction` — merged into Tag with tag_type="dietary"
- `MealPlannerPreferences` — kept but slimmed down. Retains: `max_weeknight_time`, `max_weekend_time`, `avoid_repeat_days`. Drops: `variety_score`, `vegetarian_meals_per_week`, `use_leftovers`, `batch_cooking_friendly`, `dietary_restrictions` M2M (moved to Tag). Accessed via Settings/More screen.
- `RecipeCookingHistory` — replaced by CookingNote
- Orphaned ShoppingList/ShoppingListItem tables — dropped via migration

### Shopping List

Not a persistent model. Generated on-the-fly from the week's MealPlan → Recipe → RecipeIngredient chain with quantities summed by ingredient. Manual "Other Items" stored in a simple `ShoppingListItem` model:
- `user` — FK(User, CASCADE)
- `name` — CharField
- `checked` — BooleanField (default False)
- `created_at` — DateTimeField (auto_now_add)

Cleared when a new shopping list is generated.

## Screen Designs

### This Week (Home Screen)

- Dark background (#1a1a2e), card-based layout
- Each day is a card showing: day/date label, recipe title, cook time, tags, rating
- Today's card highlighted with gold accent border and "Start Cooking →" button
- Empty slots show dashed border with "Tap to add a meal..." prompt
- Week navigation via ‹ › arrows or horizontal swipe
- Bottom action buttons: "Shopping List" and "Suggest Meals"
- Interactions: tap filled card → recipe detail, tap empty → recipe picker, long-press & drag → rearrange, swipe left → remove/swap

### Recipe Detail (Browse View)

- Recipe header: title, cook time, servings, difficulty, tags
- Rating summary: average stars, cook count, last cooked date
- Structured ingredients list: ingredient name left-aligned, quantity/unit right-aligned
- Steps: numbered, full text
- Cooking Notes section: chronological list of past cooking experiences with date, rating, and free-text note
- "Start Cooking →" CTA at bottom

### Cooking Mode

- Distraction-free dark UI (#0d0d1a)
- Exit button (top left), recipe name (center), step counter (top right)
- Progress bar across top
- Large step number watermark, step text in 20px with ingredient quantities highlighted inline in gold (#ffd59a)
- "Ingredients for this step" card below the step text
- Optional timer suggestion when step mentions a duration
- Previous cooking notes for this recipe surfaced contextually
- Prev/Next navigation at bottom. Last step shows "Done — Rate this cook"
- Wake Lock API keeps screen on

### Shopping List

- Header: "Shopping List" with week range and meal count
- Progress bar: "5 of 18 items"
- Items grouped by category (Meat & Protein, Dairy & Eggs, Produce, etc.) with emoji headers
- Each item: checkbox, ingredient name, quantity, source recipe(s)
- Ticked items fade + strike-through, stay visible until list is cleared
- "Other Items" section at bottom for manual additions (household items)
- Inline "Add item..." prompt at bottom of Other Items
- Share button for exporting the list

### Recipe Collection

- Search bar: search by recipe name or ingredient
- Horizontally scrollable filter chips: All, Favourites, Quick, Italian, Asian, etc.
- Sort options: Recently cooked, Rating, Times cooked, Newest
- Recipe cards: title, metadata (time, servings, difficulty), tags, rating, cook count
- Cards show latest cooking note preview ("Perfect result! Kids loved it.")
- Border accent: gold = favourited, teal = has been cooked, grey = never cooked
- AI-generated recipes tagged with "AI" badge
- "+ Add" button top right

## AI Integration

Three touch points, all supporting rather than driving:

### 1. Suggest Meals (from This Week)
- Triggered by "Suggest Meals" button when empty slots exist
- Algorithm: check recipe collection → ratings → cooking history → recency → propose one recipe per empty slot
- Uses existing recipes first. Only suggests new AI-generated recipes if collection is thin or user explicitly asks
- Each suggestion appears inline via HTMX with Accept / Skip / Another idea buttons

### 2. Ask AI (from Recipe → Add)
- Ingredient-based prompts: "I have chicken thighs, coconut milk, and lime"
- AI returns a structured recipe with proper ingredients, quantities, units, steps
- User reviews, tweaks, and saves to their collection
- Tagged as AI-generated (source="ai")

### 3. Post-cook intelligence (passive)
- After cooking notes accumulate, the smart planner weights suggestions better
- Recipes marked "would not make again" drop from suggestions
- High-rated recipes get boosted in suggestions
- No explicit UI — this happens in the scoring algorithm

### AI boundaries
- AI is not required to use the app. All AI features gracefully degrade if no OpenAI key is configured.
- AI does not generate meal plans from scratch — it fills gaps using the user's own recipe collection.
- The app's value comes from accumulated experience, not AI generation.

## Technical Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend | Django 4.2 | Models, views, services, auth (existing) |
| Dynamic UI | HTMX 2.x | Partial page swaps — meal slot updates, shopping ticks, recipe search |
| Client interactivity | Alpine.js 3.x | Cooking mode, drag-and-drop (SortableJS), swipe gestures, dark mode, filter chips |
| CSS | New mobile-first system | CSS custom properties, phone-first breakpoints, dark mode default |
| PWA | Service worker + manifest | Installable on home screen, offline recipe viewing, no browser chrome |

### What stays from the current codebase
- Models (refactored as described above)
- Services: RecipeService, MealPlanService, MealPlanningAssistantService, AIService (updated)
- Django auth (login, register, session-based)
- Test suite (adapted to new models)

### What gets replaced
- All templates — rebuilt mobile-first with HTMX attributes
- All CSS — new design system, dark-first, phone-first
- views.py — consolidated (remove CBV duplication), add HTMX partial response views
- Frontend JS/React directory — removed entirely, replaced by Alpine.js

### What gets added
- HTMX partial templates for each swappable region
- Cooking mode view + template with Wake Lock API
- PWA manifest + service worker
- Structured ingredient entry form UI

### URL Structure

Full-page views (initial load) and HTMX partial views (interactions):

```
# Weekly planner
/week/                              → full weekly view (home)
/week/slot/<date>/<meal_type>/      → HTMX partial: single meal card
/week/assign/<date>/<meal_type>/    → HTMX partial: recipe picker for slot
/week/suggest/                      → HTMX partial: AI suggestions for empty slots

# Recipes
/recipes/                           → full recipe list
/recipes/search/                    → HTMX partial: filtered recipe cards
/recipes/new/                       → full recipe form (manual + AI)
/recipes/<id>/                      → full recipe detail
/recipes/<id>/edit/                 → full recipe edit
/recipes/<id>/delete/               → POST: delete recipe
/recipes/<id>/favourite/            → HTMX partial: toggle favourite

# Cooking mode
/cook/<id>/                         → full cooking mode
/cook/<id>/step/<n>/                → HTMX partial: single step
/cook/<id>/done/                    → HTMX partial: rating form

# Shopping
/shop/                              → full shopping list
/shop/generate/                     → POST: generate from meal plan
/shop/toggle/<id>/                  → HTMX partial: tick/untick item
/shop/add/                          → HTMX partial: add manual item

# Auth
/accounts/login/                    → login
/accounts/register/                 → register
/accounts/logout/                   → logout

# Settings
/settings/                          → preferences, profile
```

## Design Principles

1. **Phone-first** — every screen designed for a phone viewport. Desktop is the afterthought that "looks fine too."
2. **Living cookbook** — the app becomes more valuable as recipes accumulate notes, ratings, and context.
3. **AI assists, doesn't drive** — structure and memory are the product; AI fills gaps.
4. **No page reloads** — HTMX makes every interaction feel instant.
5. **Cooking mode is sacred** — distraction-free, screen stays on, quantities inline, past notes surfaced.
6. **Plans adapt** — drag to rearrange, swipe to remove. Life happens; the plan should bend.
