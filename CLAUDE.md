# CLAUDE.md

Household-based weekly meal planner. Django backend with HTMX partial updates and Alpine.js client-side interactivity. Mobile-first dark-themed PWA.

## Tech Stack

- Django 5.2 LTS, HTMX 2.x, Alpine.js 3.x
- Anthropic Claude Haiku (AI recipe generation, URL import)
- Unsplash API (recipe images)
- pywebpush (Web Push notifications)
- SQLite (dev), Playwright (E2E tests)

## Key Commands

```sh
# Run dev server
python manage.py runserver

# Run all unit/integration tests
python manage.py test recipes

# Run E2E tests (requires Playwright + chromium)
DJANGO_ALLOW_ASYNC_UNSAFE=true python manage.py test recipes.tests.test_e2e -v2

# Run a specific test file
python manage.py test recipes.tests.test_models -v2

# Migrations
python manage.py makemigrations && python manage.py migrate

# Formatting
black . && isort .

# Linting
flake8
```

## Project Structure

```
config/              Django settings, URLs, WSGI/ASGI
recipes/
  models/            Recipe, MealPlan, Ingredient, Household, Template, PushSubscription, CookingNote, ShoppingListItem
  views/             Modular views: week.py, recipes.py, cook.py, shop.py, settings.py, auth.py, push.py
  services/          ai_service.py (Claude API), recipe_service.py, meal_planning_assistant.py
  templates/         HTMX partials pattern: templates/{feature}/partials/
  tests/             Unit tests (test_models.py, test_views_*.py), E2E (test_e2e.py)
  forms.py           Django forms
  signals.py         Post-save signals
  urls.py            All URL routing
static/              CSS, JS, service worker, manifest
```

## Coding Conventions

- **Black** for formatting (line length default 88)
- **isort** with `profile = black`, `line_length = 120`
- **flake8** with `max-line-length = 120`, ignoring `E203, W503`, excluding `venv, migrations, __pycache__`
- Config lives in `setup.cfg`

## Important Patterns

### Household-Based Queries
All meal plans, shopping lists, and templates are scoped to a household. Always use `get_household(request.user)` to get the current user's household, then filter queries by it.

### HTMX Partials
Views return full pages for initial load and HTML partials for HTMX requests. Partial templates live in `templates/{feature}/partials/`. The pattern is `hx-get`/`hx-post` pointing to a URL that returns a partial, with `hx-target` and `hx-swap` controlling where the response goes.

### Alpine.js Components
Inline `x-data` components handle client-side state (e.g., the AI generator, URL importer, template save form, notification toggle). These are defined as functions in `{% block extra_js %}` or inline.

### Custom Managers
`Recipe.objects` and `MealPlan.objects` use custom querysets with chainable methods like `.search()`, `.for_household()`, `.in_date_range()`, `.with_related()`.

### Model Signals
`recipes/signals.py` handles post-save hooks (e.g., auto-creating preferences).

### Testing
- Unit tests use `TestCase` and create test data in `setUp`
- E2E tests extend `PlaywrightTestCase` (wraps `StaticLiveServerTestCase`)
- Use `self.login()` and `self.url("/path/")` helpers in E2E tests
- Set `DJANGO_ALLOW_ASYNC_UNSAFE=true` for E2E tests
