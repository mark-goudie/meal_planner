# Recipe Import from URL — Design Spec

**Date:** 2026-03-29
**Status:** Approved

## Overview

Add URL import to the recipe creation form. User pastes a recipe URL, Claude extracts the structured recipe from the page content, and pre-fills the form for review before saving.

## Flow

1. User opens "New Recipe" form
2. Below the AI Generate section, a new "Import from URL" section
3. User pastes a URL and clicks "Import"
4. Backend fetches the page HTML, strips to text, sends to Claude Haiku
5. Claude returns structured recipe JSON (same format as `generate_structured_recipe`)
6. JavaScript pre-fills the form (same pattern as AI Generate)
7. User reviews, tweaks, and saves

## Backend

### New service method: `AIService.import_recipe_from_url(url)`

1. Validate URL format (basic URL validation)
2. Fetch page content using `requests.get(url, timeout=15)` with a browser-like User-Agent
3. Parse HTML with Python's `html.parser` or `re` — strip `<script>`, `<style>`, `<nav>`, `<footer>` tags
4. Extract text content, truncate to 5000 characters
5. Send to Claude Haiku with system prompt:
   ```
   Extract the recipe from this webpage content. Return JSON with this exact structure:
   {"title": "...", "description": "...", "prep_time": 10, "cook_time": 30,
    "servings": 4, "difficulty": "easy|medium|hard",
    "ingredients": [{"name": "...", "quantity": 500, "unit": "g", "category": "meat", "preparation_notes": "diced"}],
    "steps": ["Step 1", "Step 2"]}
   Return ONLY valid JSON, no markdown or extra text.
   If no recipe is found, return {"error": "No recipe found on this page."}
   ```
6. Parse JSON response, return dict

### New view: `import_recipe_url(request)`

- `POST /recipes/import-url/`
- Accepts `url` from POST data
- Calls `AIService.import_recipe_from_url(url)`
- Returns `JsonResponse` with structured recipe or error
- `@login_required`

### Error handling

- Missing/empty URL → 400 `{"error": "Please provide a URL."}`
- Invalid URL format → 400 `{"error": "Please provide a valid URL."}`
- Fetch fails (timeout, 404, etc.) → 400 `{"error": "Couldn't access that URL. Please check it's correct."}`
- No recipe found → 400 `{"error": "Couldn't find a recipe on that page. Try a direct recipe URL."}`
- Claude API error → 400 `{"error": "AI service unavailable. Please try again."}`

## Frontend

### Template changes: `recipes/templates/recipes/form.html`

Add a new section between the AI Generate section and the form, matching the same card style:

```html
<!-- Import from URL -->
<div x-data="urlImporter()" class="mb-xl" style="...card styles...">
  <div class="flex items-center gap-sm mb-md">
    <i class="bi bi-link-45deg" style="color: var(--primary); font-size: var(--text-xl);"></i>
    <h3>Import from URL</h3>
  </div>
  <p class="text-muted text-sm mb-md">Paste a recipe URL and we'll extract the details.</p>
  <div class="flex gap-sm">
    <input type="url" x-model="url" class="form-input" style="flex: 1;"
           placeholder="https://www.bbcgoodfood.com/recipes/..."
           @keydown.enter.prevent="importRecipe()">
    <button type="button" @click="importRecipe()" class="btn btn-primary btn-sm"
            :disabled="loading || !url.trim()">
      <span x-show="loading">Importing...</span>
      <span x-show="!loading">Import</span>
    </button>
  </div>
  <div x-show="error" class="form-error mt-sm"></div>
  <div x-show="success" class="mt-sm text-sm" style="color: var(--primary);">
    Recipe imported! Review and edit below, then save.
  </div>
</div>
```

### JavaScript: `urlImporter()` function

Same pattern as `aiGenerator()`:
- POST to `/recipes/import-url/` with the URL
- On success, pre-fill all form fields (title, description, prep_time, cook_time, servings, difficulty, source, steps)
- Populate Alpine.js ingredient rows
- Set source to "url"
- Show success message

## URL Pattern

```python
path("recipes/import-url/", import_recipe_url, name="import_recipe_url"),
```

## Files to modify

- `recipes/services/ai_service.py` — add `import_recipe_from_url` method
- `recipes/views/recipes.py` — add `import_recipe_url` view
- `recipes/views/__init__.py` — export new view
- `recipes/urls.py` — add URL pattern
- `recipes/templates/recipes/form.html` — add URL import section + JS function
