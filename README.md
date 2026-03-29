# Meal Planner

A full-featured weekly meal planning app built with Django, HTMX, and Alpine.js. Designed as a mobile-first PWA with a dark theme, it helps households plan dinners, manage recipes, generate shopping lists, and cook step-by-step. Includes AI-powered recipe generation and URL import.

## Features

- **Weekly Meal Planning** -- calendar view with tap-to-assign recipe picker, week navigation, and AI-powered meal suggestions
- **Recipe Collection** -- create, edit, search, filter, sort, and favourite recipes with structured ingredients
- **AI Recipe Generation** -- generate complete recipes from a text prompt using Anthropic Claude
- **Recipe Import from URL** -- paste a recipe URL and AI extracts title, ingredients, and steps
- **Cooking Mode** -- step-by-step walkthrough with wake lock to keep the screen on
- **Shopping List** -- auto-generated from the week's meal plan, grouped by category, with editable quantities and manual items
- **Household Sharing** -- invite family members by code; shared meal plan, shopping list, and recipes
- **Day Comments** -- add notes to any day for planning context
- **Cooking Notes** -- rate recipes, add review notes, and mark "would make again"
- **Unsplash Images** -- search and attach photos to recipes via the Unsplash API
- **Meal Plan Templates** -- save a week's meals as a reusable template and apply it to future weeks
- **Push Notifications** -- daily dinner reminder notifications via Web Push
- **PWA** -- installable on home screen with service worker and offline support
- **Dark Theme Mobile-First Design** -- CSS custom properties design system optimised for phone screens

## Tech Stack

- **Django 5.2 LTS** -- web framework, ORM, auth
- **HTMX 2.x** -- partial page updates without full reloads
- **Alpine.js 3.x** -- lightweight client-side interactivity
- **Anthropic Claude Haiku** -- AI recipe generation and URL import
- **Unsplash API** -- recipe photo search
- **Web Push (pywebpush)** -- push notification delivery
- **Playwright** -- end-to-end browser testing
- **SQLite** -- development database (no external DB required)

## Quick Start

```sh
git clone https://github.com/mgoudie/meal_planner.git
cd meal_planner
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then edit .env with your secrets
python manage.py migrate
python manage.py runserver
```

Visit http://localhost:8000/

## Project Structure

```
meal_planner/
├── config/                # Django settings, root URL conf, WSGI/ASGI
├── recipes/               # Main application
│   ├── models/            # Recipe, MealPlan, Ingredient, Household, Template, PushSubscription, etc.
│   ├── views/             # View modules: week, recipes, cook, shop, settings, auth, push
│   ├── services/          # AI service, recipe service, meal planning assistant
│   ├── templates/
│   │   ├── recipes/       # Recipe CRUD templates and partials
│   │   ├── week/          # Weekly planner templates and partials
│   │   ├── cook/          # Cooking mode templates
│   │   ├── shop/          # Shopping list templates
│   │   ├── settings/      # User settings
│   │   └── auth/          # Login and registration
│   ├── tests/             # Unit, integration, and E2E tests
│   ├── templatetags/      # Custom template filters
│   ├── forms.py           # Django forms
│   ├── signals.py         # Model signals
│   └── urls.py            # URL routing
├── static/                # Global static assets (CSS, JS, service worker)
├── requirements.txt
└── manage.py
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DJANGO_ENVIRONMENT` | `development` or `production` | `development` |
| `SECRET_KEY` | Django secret key | (required) |
| `DEBUG` | Enable debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated hostnames | `localhost,127.0.0.1` |
| `ANTHROPIC_API_KEY` | Anthropic API key for AI recipe generation and URL import | (optional) |
| `UNSPLASH_ACCESS_KEY` | Unsplash API key for recipe images | (optional) |
| `VAPID_PRIVATE_KEY` | VAPID private key for Web Push notifications | (optional) |
| `VAPID_PUBLIC_KEY` | VAPID public key for Web Push notifications | (optional) |
| `VAPID_ADMIN_EMAIL` | Admin email for VAPID (mailto: format) | (optional) |

See `.env.example` for a template.

## Testing

Run all unit and integration tests:

```sh
python manage.py test recipes
```

Run E2E tests (requires Playwright browsers installed):

```sh
pip install playwright
playwright install chromium
DJANGO_ALLOW_ASYNC_UNSAFE=true python manage.py test recipes.tests.test_e2e -v2
```

## Mobile Testing

To test on your phone over the local network:

```sh
# Find your local IP
ipconfig getifaddr en0

# Add it to ALLOWED_HOSTS in .env
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.xxx

# Run the server on all interfaces
python manage.py runserver 0.0.0.0:8000
```

Then open `http://192.168.1.xxx:8000` on your phone. Use "Add to Home Screen" in your browser to install the PWA.

## License

MIT
