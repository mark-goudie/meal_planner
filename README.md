# Meal Planner

A Django-based weekly meal planner with HTMX and Alpine.js. Mobile-first, dark-themed interface for planning dinners, managing recipes with structured ingredients, step-by-step cooking mode, and auto-generated shopping lists. Includes AI-assisted recipe creation via OpenAI.

## Features

- **Weekly Meal Planning** -- calendar view with drag-and-drop recipe assignment
- **Recipe Collection** -- create, edit, search, filter, sort, and favourite recipes
- **Structured Ingredients** -- ingredients with quantities, units, and categories
- **Cooking Mode** -- step-by-step walkthrough with ingredient highlights and completion tracking
- **Shopping List** -- auto-generated from the week's meal plan, grouped by category
- **AI Recipe Creation** -- generate recipes from a prompt using the OpenAI API
- **User Authentication** -- registration, login, per-user data isolation

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

## Tech Stack

- **Django 4.2** -- web framework, ORM, auth
- **HTMX 2.x** -- partial page updates without full reloads
- **Alpine.js 3.x** -- lightweight client-side interactivity
- **SQLite** -- development database (no external DB required)
- **CSS custom properties** -- dark theme, mobile-first design system
- **OpenAI API** -- AI recipe generation (optional)

## Project Structure

```
meal_planner/
├── config/              # Django settings, root URL conf, WSGI/ASGI
├── recipes/             # Main application
│   ├── models/          # Recipe, MealPlan, Ingredient, ShoppingListItem, etc.
│   ├── services/        # AI service, recipe service, meal planning assistant
│   ├── templates/
│   │   ├── recipes/     # Recipe CRUD templates and partials
│   │   ├── week/        # Weekly planner templates
│   │   ├── cook/        # Cooking mode templates
│   │   ├── shop/        # Shopping list templates
│   │   ├── settings/    # User settings
│   │   └── auth/        # Login and registration
│   ├── tests/           # Unit and integration tests
│   ├── templatetags/    # Custom template filters
│   ├── views.py         # View functions
│   ├── urls.py          # URL routing
│   ├── forms.py         # Django forms
│   └── signals.py       # Model signals
├── static/              # Global static assets (CSS, JS)
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
| `OPENAI_API_KEY` | OpenAI API key for AI features | (optional) |

See `.env.example` for a template.

## Running Tests

```sh
python manage.py test recipes
```

## License

MIT
