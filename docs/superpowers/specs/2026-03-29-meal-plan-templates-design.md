# Meal Plan Templates — Design Spec

**Date:** 2026-03-29
**Status:** Approved

## Overview

Save a good week's meal plan as a reusable template. Apply templates to future weeks to quickly fill empty slots.

## Data Model

### `MealPlanTemplate`
- `household` — FK(Household, CASCADE, related_name="meal_templates")
- `name` — CharField(100). E.g. "Quick Weeknight Rotation"
- `created_by` — FK(User, SET_NULL, nullable)
- `created_at` — DateTimeField(auto_now_add)

### `MealPlanTemplateEntry`
- `template` — FK(MealPlanTemplate, CASCADE, related_name="entries")
- `day_of_week` — IntegerField (0=Monday, 6=Sunday)
- `meal_type` — CharField(10), default "dinner"
- `recipe` — FK(Recipe, CASCADE)
- Unique constraint: (template, day_of_week, meal_type)

## Endpoints

### `POST /week/save-template/`
- Accepts: `name` (string), `offset` (int, which week to save)
- Creates MealPlanTemplate + entries from the specified week's meals
- Returns success message or error if no meals planned

### `GET /week/templates/`
- Returns HTMX partial: picker overlay listing household's saved templates
- Each template shows: name, recipe count, recipe names preview, created date
- Clicking a template triggers the apply

### `POST /week/apply-template/<id>/`
- Accepts: `offset` (int, which week to apply to)
- For each template entry, checks if that day already has a meal
- Only fills empty slots (doesn't overwrite)
- Returns updated week view

### `POST /week/delete-template/<id>/`
- Deletes the template (household ownership check)
- Returns success

## UI

### This Week Page

Add two buttons to the `week-bottom-actions` area (alongside Shopping List and Suggest Meals):

```
[Shopping List] [Suggest Meals]
[Save as Template] [Use Template]
```

**Save as Template:** Opens an inline Alpine.js form (name input + save button). On save, POSTs to save-template endpoint.

**Use Template:** Opens a picker overlay (same style as recipe picker) showing saved templates. Clicking one applies it and closes the picker.

### Settings Page

Add a "Meal Templates" section showing:
- List of saved templates with name, recipe count, delete button
- Empty state if no templates saved

## Apply Logic

When applying template to a week with offset:
1. Calculate the Monday of the target week
2. For each TemplateEntry:
   - Calculate target_date = monday + timedelta(days=entry.day_of_week)
   - Check if MealPlan exists for (household, target_date, entry.meal_type)
   - If empty, create MealPlan with the template's recipe
   - If filled, skip
3. Return the count of meals added

## Files

### New:
- `recipes/models/template.py` — MealPlanTemplate, MealPlanTemplateEntry
- `recipes/templates/week/partials/template_picker.html` — HTMX picker overlay
- `recipes/tests/test_templates.py` — tests

### Modified:
- `recipes/models/__init__.py` — export new models
- `recipes/views/week.py` — add save/apply/delete/list template views
- `recipes/views/__init__.py` — export new views
- `recipes/urls.py` — add template URL patterns
- `recipes/templates/week/week.html` — add Save/Use Template buttons
- `recipes/templates/settings/settings.html` — add templates section
