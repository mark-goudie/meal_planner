# Meal Planner Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the meal planner into a mobile-first, HTMX-powered app with structured ingredients, cooking mode, and a living cookbook experience.

**Architecture:** Keep Django 4.2 backend with existing service layer. Replace all templates with mobile-first HTMX + Alpine.js templates. Refactor data models for structured ingredients and cooking notes. Add PWA support for home screen installation.

**Tech Stack:** Django 4.2, HTMX 2.x, Alpine.js 3.x, SortableJS, CSS custom properties (no framework), SQLite (dev)

**Spec:** `docs/superpowers/specs/2026-03-28-meal-planner-redesign-design.md`

---

## File Structure

### New Files

```
# Models (split from monolithic models.py)
recipes/models/                          — models package
recipes/models/__init__.py               — re-exports all models
recipes/models/recipe.py                 — Recipe, Tag, Ingredient, RecipeIngredient
recipes/models/meal_plan.py              — MealPlan, MealPlannerPreferences
recipes/models/cooking.py                — CookingNote
recipes/models/shopping.py               — ShoppingListItem
recipes/models/managers.py               — RecipeQuerySet, RecipeManager, MealPlanQuerySet, MealPlanManager

# Views (split by screen)
recipes/views/                           — views package
recipes/views/__init__.py                — re-exports all views
recipes/views/week.py                    — This Week views (full + HTMX partials)
recipes/views/recipes.py                 — Recipe CRUD views (full + HTMX partials)
recipes/views/cook.py                    — Cooking mode views
recipes/views/shop.py                    — Shopping list views
recipes/views/auth.py                    — Register, login redirects
recipes/views/settings.py                — User preferences/settings

# Templates (mobile-first, HTMX-enabled)
recipes/templates/base.html              — new mobile-first base with bottom nav, HTMX, Alpine
recipes/templates/week/week.html         — full weekly view
recipes/templates/week/partials/         — HTMX partials: meal_card.html, recipe_picker.html, suggestion.html
recipes/templates/recipes/list.html      — recipe collection
recipes/templates/recipes/detail.html    — recipe detail with cooking notes
recipes/templates/recipes/form.html      — add/edit recipe with structured ingredients
recipes/templates/recipes/partials/      — HTMX partials: recipe_card.html, search_results.html
recipes/templates/cook/cook.html         — cooking mode full page
recipes/templates/cook/partials/         — HTMX partials: step.html, done.html
recipes/templates/shop/shop.html         — shopping list full page
recipes/templates/shop/partials/         — HTMX partials: item.html, add_item.html
recipes/templates/auth/login.html        — login
recipes/templates/auth/register.html     — register
recipes/templates/settings/settings.html — user preferences

# Static assets
recipes/static/recipes/css/app.css       — new mobile-first design system
recipes/static/recipes/js/app.js         — Alpine.js components (cooking mode, drag-drop)
recipes/static/recipes/manifest.json     — PWA manifest
recipes/static/recipes/sw.js             — service worker

# Forms
recipes/forms/                           — forms package
recipes/forms/__init__.py                — re-exports
recipes/forms/recipe.py                  — RecipeForm with structured ingredients
recipes/forms/meal_plan.py               — MealPlanForm
recipes/forms/cooking.py                 — CookingNoteForm (quick post-cook rating)
recipes/forms/auth.py                    — CustomUserCreationForm

# Tests (updated for new models)
recipes/tests/test_models_new.py         — tests for new/modified models
recipes/tests/test_views_week.py         — tests for week views
recipes/tests/test_views_cook.py         — tests for cooking mode views
recipes/tests/test_views_shop.py         — tests for shopping views
recipes/tests/test_views_recipes.py      — tests for recipe CRUD views
```

### Modified Files

```
config/settings.py                       — add django_htmx to INSTALLED_APPS, STATIC_ROOT
config/urls.py                           — updated URL includes
recipes/urls.py                          — complete rewrite with new URL patterns
recipes/services/recipe_service.py       — update for structured ingredients
recipes/services/meal_plan_service.py    — update for new models
recipes/services/meal_planning_assistant.py — update scoring for CookingNote
recipes/services/ai_service.py           — return structured recipe data
recipes/signals.py                       — update demo recipes for new model structure
recipes/admin.py                         — register new models
requirements.txt                         — add django-htmx
```

### Removed Files

```
recipes/models.py                        — replaced by recipes/models/ package
recipes/views.py                         — replaced by recipes/views/ package
recipes/views_cbv.py                     — removed (consolidated into views package)
recipes/forms.py                         — replaced by recipes/forms/ package
recipes/static/recipes/css/main.css      — replaced by app.css
frontend/                               — removed entirely (React demo)
```

---

## Task 1: Install Dependencies and Configure HTMX

**Files:**
- Modify: `requirements.txt`
- Modify: `config/settings.py`
- Modify: `.gitignore`

- [ ] **Step 1: Install HTMX and Alpine.js dependencies**

```bash
source venv/bin/activate
pip install django-htmx>=1.17.0
pip freeze | grep django-htmx
```

Expected: `django-htmx==1.19.0` (or similar)

- [ ] **Step 2: Update requirements.txt**

Add `django-htmx` to `requirements.txt`:

```
Django>=4.2.3,<5.0
django-htmx>=1.17.0
django-ratelimit>=4.0
django-widget-tweaks>=1.5.0
openai>=1.0.0
pillow>=10.0.0
python-dotenv>=1.0.0
```

- [ ] **Step 3: Update settings.py**

In `config/settings.py`, add `django_htmx` to `INSTALLED_APPS` after `widget_tweaks`, add `HtmxMiddleware` to `MIDDLEWARE`, and add `STATIC_ROOT`:

```python
INSTALLED_APPS = [
    'recipes.apps.RecipesConfig',
    'widget_tweaks',
    'django_htmx',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]
```

Add at the bottom of settings.py:

```python
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

- [ ] **Step 4: Update .gitignore**

Add these entries to `.gitignore`:

```
.superpowers/
frontend/node_modules/
frontend/dist/
staticfiles/
```

- [ ] **Step 5: Verify configuration**

```bash
source venv/bin/activate
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 6: Commit**

```bash
git add requirements.txt config/settings.py .gitignore
git commit -m "feat: add HTMX dependency and configure middleware"
```

---

## Task 2: Refactor Models into Package — Managers

**Files:**
- Create: `recipes/models/__init__.py`
- Create: `recipes/models/managers.py`

- [ ] **Step 1: Create models package directory**

```bash
mkdir -p recipes/models
```

- [ ] **Step 2: Create managers.py with existing managers**

Create `recipes/models/managers.py` with the existing `RecipeQuerySet`, `RecipeManager`, `MealPlanQuerySet`, and `MealPlanManager` from `recipes/models.py:10-108`. Update the `search` method to also search structured ingredients:

```python
from django.db import models
from django.db.models import Q, Count


class RecipeQuerySet(models.QuerySet):
    def with_related(self):
        return self.select_related('user').prefetch_related(
            'tags', 'favourited_by', 'recipe_ingredients__ingredient'
        )

    def for_user(self, user):
        return self.filter(user=user)

    def favourited_by_user(self, user):
        return self.filter(favourited_by=user)

    def with_tag(self, tag_id):
        return self.filter(tags__id=tag_id)

    def search(self, query):
        return self.filter(
            Q(title__icontains=query)
            | Q(ingredients_text__icontains=query)
            | Q(recipe_ingredients__ingredient__name__icontains=query)
        ).distinct()


class RecipeManager(models.Manager):
    def get_queryset(self):
        return RecipeQuerySet(self.model, using=self._db)

    def with_related(self):
        return self.get_queryset().with_related()

    def for_user(self, user):
        return self.get_queryset().for_user(user)

    def favourited_by_user(self, user):
        return self.get_queryset().favourited_by_user(user)

    def with_tag(self, tag_id):
        return self.get_queryset().with_tag(tag_id)

    def search(self, query):
        return self.get_queryset().search(query)


class MealPlanQuerySet(models.QuerySet):
    def with_related(self):
        return self.select_related(
            'recipe', 'recipe__user'
        ).prefetch_related('recipe__tags')

    def for_user(self, user):
        return self.filter(user=user)

    def upcoming(self):
        from datetime import date
        return self.filter(date__gte=date.today())

    def in_date_range(self, start_date, end_date):
        return self.filter(date__range=[start_date, end_date])


class MealPlanManager(models.Manager):
    def get_queryset(self):
        return MealPlanQuerySet(self.model, using=self._db)

    def with_related(self):
        return self.get_queryset().with_related()

    def for_user(self, user):
        return self.get_queryset().for_user(user)

    def upcoming(self):
        return self.get_queryset().upcoming()

    def in_date_range(self, start_date, end_date):
        return self.get_queryset().in_date_range(start_date, end_date)
```

- [ ] **Step 3: Create models/__init__.py**

Create `recipes/models/__init__.py` as an empty file for now (we'll add imports as we create model files):

```python
# Models will be imported here as they are created in subsequent tasks
```

- [ ] **Step 4: Commit**

```bash
git add recipes/models/
git commit -m "refactor: extract model managers into models package"
```

---

## Task 3: New and Modified Models — Recipe, Tag, Ingredient, RecipeIngredient

**Files:**
- Create: `recipes/models/recipe.py`
- Test: `recipes/tests/test_models_new.py`

- [ ] **Step 1: Write failing tests for Ingredient and RecipeIngredient**

Create `recipes/tests/test_models_new.py`:

```python
from django.test import TestCase
from django.contrib.auth.models import User
from recipes.models.recipe import Ingredient, RecipeIngredient, Recipe, Tag


class IngredientModelTest(TestCase):
    def test_create_ingredient(self):
        ingredient = Ingredient.objects.create(name="cumin", category="spices")
        self.assertEqual(str(ingredient), "cumin")
        self.assertEqual(ingredient.category, "spices")

    def test_ingredient_name_unique(self):
        Ingredient.objects.create(name="salt", category="spices")
        with self.assertRaises(Exception):
            Ingredient.objects.create(name="salt", category="spices")

    def test_ingredient_categories(self):
        for code, _ in Ingredient.CATEGORY_CHOICES:
            i = Ingredient.objects.create(name=f"test_{code}", category=code)
            self.assertEqual(i.category, code)


class RecipeIngredientModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", password="testpass123")
        self.recipe = Recipe.objects.create(
            user=self.user, title="Test Recipe", steps="Step 1"
        )
        self.ingredient = Ingredient.objects.create(name="chicken", category="meat")

    def test_create_recipe_ingredient(self):
        ri = RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient,
            quantity=500,
            unit="g",
            order=1,
        )
        self.assertEqual(str(ri), "500 g chicken")
        self.assertEqual(ri.recipe, self.recipe)

    def test_recipe_ingredient_nullable_quantity(self):
        ri = RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient,
            unit="to_taste",
            order=1,
        )
        self.assertIsNone(ri.quantity)
        self.assertEqual(str(ri), "to taste chicken")

    def test_recipe_ingredient_with_prep_notes(self):
        ri = RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient,
            quantity=200,
            unit="g",
            preparation_notes="finely diced",
            order=1,
        )
        self.assertEqual(ri.preparation_notes, "finely diced")


class TagModelTest(TestCase):
    def test_create_tag_with_type(self):
        tag = Tag.objects.create(name="Italian", tag_type="cuisine")
        self.assertEqual(tag.tag_type, "cuisine")
        self.assertEqual(str(tag), "Italian")

    def test_tag_type_choices(self):
        for code, _ in Tag.TAG_TYPE_CHOICES:
            t = Tag.objects.create(name=f"test_{code}", tag_type=code)
            self.assertEqual(t.tag_type, code)


class RecipeModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", password="testpass123")

    def test_recipe_source_field(self):
        recipe = Recipe.objects.create(
            user=self.user, title="Test", steps="Step 1", source="ai"
        )
        self.assertEqual(recipe.source, "ai")

    def test_recipe_ingredients_text_kept(self):
        recipe = Recipe.objects.create(
            user=self.user,
            title="Test",
            steps="Step 1",
            ingredients_text="500g chicken",
        )
        self.assertEqual(recipe.ingredients_text, "500g chicken")

    def test_recipe_structured_ingredients(self):
        recipe = Recipe.objects.create(
            user=self.user, title="Test", steps="Step 1"
        )
        ingredient = Ingredient.objects.create(name="garlic", category="produce")
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=ingredient, quantity=3, unit="piece", order=1
        )
        self.assertEqual(recipe.recipe_ingredients.count(), 1)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source venv/bin/activate
python manage.py test recipes.tests.test_models_new -v2 2>&1 | head -20
```

Expected: ImportError — `recipes.models.recipe` does not exist yet.

- [ ] **Step 3: Create recipe.py with all recipe-related models**

Create `recipes/models/recipe.py`:

```python
from django.db import models
from django.contrib.auth.models import User
from .managers import RecipeManager


class Tag(models.Model):
    TAG_TYPE_CHOICES = [
        ('dietary', 'Dietary'),
        ('cuisine', 'Cuisine'),
        ('method', 'Method'),
        ('time', 'Time'),
    ]

    name = models.CharField(max_length=50, unique=True)
    tag_type = models.CharField(
        max_length=20, choices=TAG_TYPE_CHOICES, default='cuisine'
    )

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    CATEGORY_CHOICES = [
        ('produce', 'Produce'),
        ('dairy', 'Dairy & Eggs'),
        ('meat', 'Meat & Protein'),
        ('pantry', 'Pantry Staples'),
        ('spices', 'Spices & Seasonings'),
        ('frozen', 'Frozen'),
        ('bakery', 'Bakery'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default='other'
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Recipe(models.Model):
    SOURCE_CHOICES = [
        ('manual', 'Manual'),
        ('ai', 'AI Generated'),
        ('url', 'From URL'),
        ('family', 'Family Recipe'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipes')
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    ingredients_text = models.TextField(blank=True, help_text="Legacy plain-text ingredients")
    steps = models.TextField()
    notes = models.TextField(blank=True)
    source = models.CharField(
        max_length=10, choices=SOURCE_CHOICES, default='manual'
    )
    is_ai_generated = models.BooleanField(default=False)
    cooking_mode_steps = models.JSONField(
        null=True, blank=True,
        help_text="Structured steps with ingredient refs for cooking mode"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    prep_time = models.PositiveIntegerField(
        null=True, blank=True, help_text="Preparation time in minutes"
    )
    cook_time = models.PositiveIntegerField(
        null=True, blank=True, help_text="Cooking time in minutes"
    )
    servings = models.PositiveIntegerField(default=4, help_text="Number of servings")
    difficulty = models.CharField(
        max_length=10,
        choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')],
        default='medium',
        blank=True,
    )
    image = models.ImageField(upload_to='recipes/', null=True, blank=True)

    tags = models.ManyToManyField(Tag, blank=True)
    favourited_by = models.ManyToManyField(
        User, related_name='favourites', blank=True
    )

    objects = RecipeManager()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return self.title

    @property
    def total_time(self):
        prep = self.prep_time or 0
        cook = self.cook_time or 0
        return prep + cook if (prep or cook) else None

    @property
    def average_rating(self):
        from .cooking import CookingNote
        avg = self.cooking_notes.aggregate(avg=models.Avg('rating'))['avg']
        return round(avg, 1) if avg else None

    @property
    def cook_count(self):
        return self.cooking_notes.count()

    @property
    def latest_note(self):
        return self.cooking_notes.order_by('-cooked_date').first()


class RecipeIngredient(models.Model):
    UNIT_CHOICES = [
        ('g', 'g'),
        ('kg', 'kg'),
        ('ml', 'ml'),
        ('L', 'L'),
        ('tsp', 'tsp'),
        ('tbsp', 'tbsp'),
        ('cup', 'cup'),
        ('piece', 'piece'),
        ('bunch', 'bunch'),
        ('pinch', 'pinch'),
        ('to_taste', 'to taste'),
    ]

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='recipe_ingredients'
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, related_name='recipe_ingredients'
    )
    quantity = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='g')
    preparation_notes = models.CharField(max_length=100, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        if self.quantity:
            qty = self.quantity.normalize()
            return f"{qty} {self.get_unit_display()} {self.ingredient.name}"
        return f"{self.get_unit_display()} {self.ingredient.name}"
```

- [ ] **Step 4: Update models/__init__.py**

```python
from .recipe import Recipe, Tag, Ingredient, RecipeIngredient
from .managers import RecipeQuerySet, RecipeManager, MealPlanQuerySet, MealPlanManager
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
source venv/bin/activate
python manage.py test recipes.tests.test_models_new -v2
```

Expected: All tests pass.

Note: These tests import from `recipes.models.recipe` directly. The old `recipes/models.py` still exists at this point. We'll remove it after all model files are created and migrations are generated.

- [ ] **Step 6: Commit**

```bash
git add recipes/models/recipe.py recipes/models/__init__.py recipes/tests/test_models_new.py
git commit -m "feat: add Ingredient, RecipeIngredient models and Tag.tag_type"
```

---

## Task 4: New Models — MealPlan, CookingNote, ShoppingListItem

**Files:**
- Create: `recipes/models/meal_plan.py`
- Create: `recipes/models/cooking.py`
- Create: `recipes/models/shopping.py`
- Modify: `recipes/models/__init__.py`
- Modify: `recipes/tests/test_models_new.py`

- [ ] **Step 1: Write failing tests for CookingNote and ShoppingListItem**

Append to `recipes/tests/test_models_new.py`:

```python
from recipes.models.cooking import CookingNote
from recipes.models.shopping import ShoppingListItem
from recipes.models.meal_plan import MealPlan, MealPlannerPreferences


class CookingNoteModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("cooknotes", password="testpass123")
        self.recipe = Recipe.objects.create(
            user=self.user, title="Test Recipe", steps="Step 1"
        )

    def test_create_cooking_note(self):
        note = CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date="2026-03-28",
            rating=5,
            note="Delicious! Family loved it.",
            would_make_again=True,
        )
        self.assertEqual(note.rating, 5)
        self.assertTrue(note.would_make_again)
        self.assertEqual(str(note), "Test Recipe — 2026-03-28 (5★)")

    def test_cooking_note_optional_note_text(self):
        note = CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date="2026-03-28",
            rating=3,
        )
        self.assertEqual(note.note, "")

    def test_recipe_average_rating(self):
        CookingNote.objects.create(
            recipe=self.recipe, user=self.user,
            cooked_date="2026-03-20", rating=4,
        )
        CookingNote.objects.create(
            recipe=self.recipe, user=self.user,
            cooked_date="2026-03-25", rating=5,
        )
        self.assertEqual(self.recipe.average_rating, 4.5)


class ShoppingListItemModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("shopper", password="testpass123")

    def test_create_manual_item(self):
        item = ShoppingListItem.objects.create(
            user=self.user, name="Dishwasher tablets"
        )
        self.assertFalse(item.checked)
        self.assertEqual(str(item), "Dishwasher tablets")

    def test_toggle_checked(self):
        item = ShoppingListItem.objects.create(
            user=self.user, name="Paper towels"
        )
        item.checked = True
        item.save()
        item.refresh_from_db()
        self.assertTrue(item.checked)


class MealPlanModelNewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("planner", password="testpass123")
        self.recipe = Recipe.objects.create(
            user=self.user, title="Test Recipe", steps="Step 1"
        )

    def test_meal_plan_notes_field(self):
        mp = MealPlan.objects.create(
            user=self.user,
            date="2026-03-28",
            meal_type="dinner",
            recipe=self.recipe,
            notes="Use leftover chicken",
        )
        self.assertEqual(mp.notes, "Use leftover chicken")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source venv/bin/activate
python manage.py test recipes.tests.test_models_new -v2 2>&1 | tail -5
```

Expected: ImportError for `recipes.models.cooking`.

- [ ] **Step 3: Create cooking.py**

Create `recipes/models/cooking.py`:

```python
from django.db import models
from django.contrib.auth.models import User


class CookingNote(models.Model):
    recipe = models.ForeignKey(
        'recipe.Recipe', on_delete=models.CASCADE, related_name='cooking_notes'
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='cooking_notes'
    )
    cooked_date = models.DateField()
    rating = models.IntegerField(
        choices=[(i, f"{i}★") for i in range(1, 6)]
    )
    note = models.TextField(blank=True)
    would_make_again = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-cooked_date']
        indexes = [
            models.Index(fields=['user', '-cooked_date']),
        ]

    def __str__(self):
        return f"{self.recipe.title} — {self.cooked_date} ({self.rating}★)"
```

- [ ] **Step 4: Create shopping.py**

Create `recipes/models/shopping.py`:

```python
from django.db import models
from django.contrib.auth.models import User


class ShoppingListItem(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='shopping_items'
    )
    name = models.CharField(max_length=200)
    checked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['checked', 'created_at']

    def __str__(self):
        return self.name
```

- [ ] **Step 5: Create meal_plan.py**

Create `recipes/models/meal_plan.py`:

```python
from datetime import date
from django.db import models
from django.contrib.auth.models import User
from .managers import MealPlanManager

MEAL_CHOICES = [
    ('breakfast', 'Breakfast'),
    ('lunch', 'Lunch'),
    ('dinner', 'Dinner'),
]


class MealPlan(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='meal_plans'
    )
    date = models.DateField(default=date.today)
    meal_type = models.CharField(max_length=10, choices=MEAL_CHOICES)
    recipe = models.ForeignKey(
        'recipe.Recipe', on_delete=models.CASCADE
    )
    notes = models.TextField(blank=True)

    objects = MealPlanManager()

    class Meta:
        ordering = ['date', 'meal_type']
        unique_together = ('user', 'date', 'meal_type')
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'date', 'meal_type']),
        ]

    def __str__(self):
        meal_type_display = dict(MEAL_CHOICES).get(self.meal_type, self.meal_type)
        return f"{meal_type_display} on {self.date}: {self.recipe.title}"


class MealPlannerPreferences(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='planner_preferences'
    )
    max_weeknight_time = models.IntegerField(
        default=45, help_text="Maximum cooking time for weeknights (minutes)"
    )
    max_weekend_time = models.IntegerField(
        default=90, help_text="Maximum cooking time for weekends (minutes)"
    )
    avoid_repeat_days = models.IntegerField(
        default=14, help_text="Don't repeat recipes within this many days"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Meal planner preferences'

    def __str__(self):
        return f"Preferences for {self.user.username}"
```

- [ ] **Step 6: Update models/__init__.py with all imports**

```python
from .recipe import Recipe, Tag, Ingredient, RecipeIngredient
from .cooking import CookingNote
from .meal_plan import MealPlan, MealPlannerPreferences, MEAL_CHOICES
from .shopping import ShoppingListItem
from .managers import RecipeQuerySet, RecipeManager, MealPlanQuerySet, MealPlanManager
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
source venv/bin/activate
python manage.py test recipes.tests.test_models_new -v2
```

Expected: All tests pass. Note: migrations haven't been created yet — Django's test runner creates tables from model definitions. We'll create migrations in the next task.

- [ ] **Step 8: Commit**

```bash
git add recipes/models/ recipes/tests/test_models_new.py
git commit -m "feat: add CookingNote, ShoppingListItem, MealPlan.notes models"
```

---

## Task 5: Migration — Swap Old models.py for New Package

This is the critical task that replaces the old monolithic `recipes/models.py` with the new package, generates migrations, and ensures database continuity.

**Files:**
- Remove: `recipes/models.py`
- Modify: `recipes/models/__init__.py`
- Create: new migration file (auto-generated)
- Modify: `recipes/signals.py`
- Modify: `recipes/admin.py`

- [ ] **Step 1: Remove old models.py**

```bash
rm recipes/models.py
```

The `recipes/models/` package now takes over. Django resolves models from `recipes.models` via the `__init__.py` imports.

- [ ] **Step 2: Update import in CookingNote to use string reference**

In `recipes/models/cooking.py`, the FK to Recipe should use a string reference to avoid circular imports. Verify it says `'recipe.Recipe'` — if Django can't resolve this (since the app label is `recipes`, not `recipe`), update to:

```python
recipe = models.ForeignKey(
    'Recipe', on_delete=models.CASCADE, related_name='cooking_notes'
)
```

Similarly in `recipes/models/meal_plan.py`:

```python
recipe = models.ForeignKey(
    'Recipe', on_delete=models.CASCADE
)
```

When using string references without an app label, Django resolves them within the same app.

- [ ] **Step 3: Update signals.py for new model structure**

Update `recipes/signals.py` to use `ingredients_text` instead of `ingredients` and add `source` field:

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Recipe


@receiver(post_save, sender=User)
def create_demo_recipes(sender, instance, created, **kwargs):
    if created:
        Recipe.objects.create(
            user=instance,
            title="Classic Omelette",
            ingredients_text="3 eggs\n1 tbsp butter\nSalt and pepper to taste\nOptional fillings: cheese, herbs, vegetables",
            steps="1. Crack eggs into a bowl and whisk until well combined.\n2. Heat butter in a non-stick pan over medium heat.\n3. Pour in the eggs and let them set for about 30 seconds.\n4. Gently push cooked edges toward center, tilting pan to let uncooked egg flow to edges.\n5. When mostly set but still slightly moist on top, add fillings to one half.\n6. Fold the other half over the fillings and slide onto a plate.\n7. Season with salt and pepper.",
            prep_time=5,
            cook_time=10,
            servings=1,
            difficulty='easy',
            source='manual',
        )
        Recipe.objects.create(
            user=instance,
            title="Fresh Garden Salad",
            ingredients_text="Mixed salad greens\n1 cucumber, sliced\n2 tomatoes, chopped\n1/4 red onion, thinly sliced\nOlive oil and lemon dressing",
            steps="1. Wash and dry all vegetables thoroughly.\n2. Tear salad greens into bite-sized pieces and place in a large bowl.\n3. Add sliced cucumber, chopped tomatoes, and red onion.\n4. Drizzle with olive oil and squeeze fresh lemon juice over the top.\n5. Toss gently to combine.\n6. Season with salt and pepper to taste.",
            prep_time=10,
            cook_time=0,
            servings=2,
            difficulty='easy',
            source='manual',
        )
```

- [ ] **Step 4: Update admin.py**

Replace `recipes/admin.py`:

```python
from django.contrib import admin
from .models import (
    Recipe, Tag, Ingredient, RecipeIngredient,
    MealPlan, MealPlannerPreferences,
    CookingNote, ShoppingListItem,
)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'source', 'difficulty', 'created_at']
    list_filter = ['source', 'difficulty', 'tags']
    search_fields = ['title']
    inlines = [RecipeIngredientInline]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'tag_type']
    list_filter = ['tag_type']


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['name', 'category']
    list_filter = ['category']
    search_fields = ['name']


@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'meal_type', 'recipe']
    list_filter = ['meal_type', 'date']


@admin.register(CookingNote)
class CookingNoteAdmin(admin.ModelAdmin):
    list_display = ['recipe', 'user', 'cooked_date', 'rating', 'would_make_again']
    list_filter = ['rating', 'would_make_again']


@admin.register(MealPlannerPreferences)
class MealPlannerPreferencesAdmin(admin.ModelAdmin):
    list_display = ['user', 'max_weeknight_time', 'max_weekend_time']


@admin.register(ShoppingListItem)
class ShoppingListItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'checked']
    list_filter = ['checked']
```

- [ ] **Step 5: Generate migrations**

```bash
source venv/bin/activate
python manage.py makemigrations recipes
```

This will generate migration(s) that:
- Rename `ingredients` → `ingredients_text` on Recipe
- Add `source`, `cooking_mode_steps` fields to Recipe
- Add `tag_type` to Tag
- Add `notes` to MealPlan
- Create `Ingredient`, `RecipeIngredient`, `CookingNote`, `ShoppingListItem` tables
- Remove `FamilyPreference`, `RecipeCookingHistory`, `DietaryRestriction`, `GeneratedMealPlan`, `GeneratedMealPlanEntry` tables

Django may need help understanding the rename. If it asks "Did you rename Recipe.ingredients to Recipe.ingredients_text?", answer **yes**.

- [ ] **Step 6: Review the generated migration**

```bash
cat recipes/migrations/0011_*.py | head -60
```

Verify the migration includes `RenameField` for `ingredients` → `ingredients_text` (not a drop+add).

- [ ] **Step 7: Apply migrations**

```bash
source venv/bin/activate
python manage.py migrate
```

Expected: Migration applied successfully.

- [ ] **Step 8: Verify Django checks pass**

```bash
source venv/bin/activate
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 9: Run all new model tests**

```bash
source venv/bin/activate
python manage.py test recipes.tests.test_models_new -v2
```

Expected: All tests pass.

- [ ] **Step 10: Remove old view/form files that reference deleted models**

```bash
rm recipes/views_cbv.py
```

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "feat: migrate to models package with structured ingredients and cooking notes"
```

---

## Task 6: Update Services for New Models

**Files:**
- Modify: `recipes/services/recipe_service.py`
- Modify: `recipes/services/meal_plan_service.py`
- Modify: `recipes/services/meal_planning_assistant.py`
- Modify: `recipes/services/__init__.py`

- [ ] **Step 1: Write test for shopping list generation with structured ingredients**

Create `recipes/tests/test_services_new.py`:

```python
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from recipes.models import Recipe, Ingredient, RecipeIngredient, MealPlan, CookingNote
from recipes.services.recipe_service import RecipeService


class ShoppingListGenerationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("shoptest", password="testpass123")
        self.recipe1 = Recipe.objects.create(
            user=self.user, title="Carbonara", steps="Cook it"
        )
        self.recipe2 = Recipe.objects.create(
            user=self.user, title="Stir Fry", steps="Fry it"
        )
        self.eggs = Ingredient.objects.create(name="eggs", category="dairy")
        self.chicken = Ingredient.objects.create(name="chicken breast", category="meat")

        # Carbonara needs 4 eggs
        RecipeIngredient.objects.create(
            recipe=self.recipe1, ingredient=self.eggs,
            quantity=4, unit="piece", order=1,
        )
        # Stir fry needs 2 eggs and 500g chicken
        RecipeIngredient.objects.create(
            recipe=self.recipe2, ingredient=self.eggs,
            quantity=2, unit="piece", order=1,
        )
        RecipeIngredient.objects.create(
            recipe=self.recipe2, ingredient=self.chicken,
            quantity=500, unit="g", order=2,
        )

    def test_generate_shopping_list_sums_quantities(self):
        recipes = [self.recipe1, self.recipe2]
        shopping_list = RecipeService.generate_structured_shopping_list(recipes)
        # eggs should be summed: 4 + 2 = 6
        eggs_entry = next(e for e in shopping_list if e['ingredient'].name == 'eggs')
        self.assertEqual(eggs_entry['total_quantity'], Decimal('6'))
        self.assertEqual(eggs_entry['unit'], 'piece')
        self.assertEqual(set(eggs_entry['recipes']), {'Carbonara', 'Stir Fry'})

    def test_generate_shopping_list_groups_by_category(self):
        recipes = [self.recipe1, self.recipe2]
        shopping_list = RecipeService.generate_structured_shopping_list(recipes)
        categories = {e['category'] for e in shopping_list}
        self.assertIn('dairy', categories)
        self.assertIn('meat', categories)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
source venv/bin/activate
python manage.py test recipes.tests.test_services_new -v2 2>&1 | tail -5
```

Expected: AttributeError — `RecipeService` has no `generate_structured_shopping_list`.

- [ ] **Step 3: Add generate_structured_shopping_list to RecipeService**

Add to `recipes/services/recipe_service.py`:

```python
@staticmethod
def generate_structured_shopping_list(recipes):
    """Generate a shopping list with summed quantities from structured ingredients."""
    from collections import defaultdict
    from recipes.models import RecipeIngredient

    aggregated = defaultdict(lambda: {
        'ingredient': None,
        'category': '',
        'total_quantity': Decimal('0'),
        'unit': '',
        'recipes': set(),
    })

    for recipe in recipes:
        for ri in recipe.recipe_ingredients.select_related('ingredient').all():
            key = (ri.ingredient_id, ri.unit)
            entry = aggregated[key]
            entry['ingredient'] = ri.ingredient
            entry['category'] = ri.ingredient.category
            if ri.quantity:
                entry['total_quantity'] += ri.quantity
            entry['unit'] = ri.get_unit_display()
            entry['recipes'].add(recipe.title)

    return sorted(aggregated.values(), key=lambda x: (x['category'], x['ingredient'].name))
```

Add `from decimal import Decimal` to the top of the file.

- [ ] **Step 4: Run test to verify it passes**

```bash
source venv/bin/activate
python manage.py test recipes.tests.test_services_new -v2
```

Expected: All tests pass.

- [ ] **Step 5: Update MealPlanningAssistantService to use CookingNote**

In `recipes/services/meal_planning_assistant.py`, update the imports and `calculate_recipe_happiness_score` method to read from `CookingNote` instead of `FamilyPreference` and `RecipeCookingHistory`:

Update imports at top:

```python
from ..models import (
    Recipe,
    CookingNote,
    MealPlan,
    MealPlannerPreferences,
    MEAL_CHOICES,
)
```

Replace `calculate_recipe_happiness_score`:

```python
@staticmethod
def calculate_recipe_happiness_score(recipe, user):
    """Calculate a happiness score (0-100) based on cooking notes."""
    notes = CookingNote.objects.filter(recipe=recipe, user=user)
    if not notes.exists():
        return 50.0  # neutral score for uncooked recipes

    avg_rating = notes.aggregate(avg=models.Avg('rating'))['avg']
    # Convert 1-5 scale to 0-100
    score = ((avg_rating - 1) / 4) * 100

    # Boost if user would make again (most recent note)
    latest = notes.order_by('-cooked_date').first()
    if latest and not latest.would_make_again:
        score = max(score - 30, 0)

    return round(score, 1)
```

Replace `get_recently_cooked_recipes`:

```python
@staticmethod
def get_recently_cooked_recipes(user, days=14):
    """Get recipe IDs cooked in the last N days."""
    from datetime import date, timedelta
    cutoff = date.today() - timedelta(days=days)
    return set(
        CookingNote.objects.filter(
            user=user, cooked_date__gte=cutoff
        ).values_list('recipe_id', flat=True)
    )
```

Update `approve_plan` to create `CookingNote` entries instead of `RecipeCookingHistory`, and create `MealPlan` entries directly (no more `GeneratedMealPlan`). This method will be simplified in a later task when we rework the suggest-meals flow.

- [ ] **Step 6: Update services/__init__.py**

```python
from .ai_service import AIService, AIServiceException, AIConfigurationError, AIValidationError, AIAPIError
from .recipe_service import RecipeService
from .meal_plan_service import MealPlanService
from .meal_planning_assistant import MealPlanningAssistantService
```

- [ ] **Step 7: Run all tests**

```bash
source venv/bin/activate
python manage.py test recipes.tests.test_services_new -v2
```

Expected: All tests pass.

- [ ] **Step 8: Commit**

```bash
git add recipes/services/ recipes/tests/test_services_new.py
git commit -m "feat: update services for structured ingredients and CookingNote"
```

---

## Task 7: Mobile-First CSS Design System

**Files:**
- Create: `recipes/static/recipes/css/app.css`

- [ ] **Step 1: Create the mobile-first design system**

Create `recipes/static/recipes/css/app.css` with CSS custom properties, dark-first theme, phone-first breakpoints. This is a large file — key sections:

1. **CSS Reset & Variables** — custom properties for colours (`--primary: #7cb9a8`, `--accent: #ffd59a`, `--bg: #1a1a2e`, etc.), spacing scale, typography scale, shadows, radii
2. **Base Typography** — Inter/Roboto fonts, fluid sizing with `clamp()`
3. **Bottom Tab Bar** — fixed bottom nav, thumb-reachable, 48px touch targets
4. **Card Components** — meal cards, recipe cards with accent borders
5. **Form Components** — large touch-friendly inputs (min-height 48px), styled selects
6. **Button Components** — primary gradient, secondary outline, full-width on mobile
7. **Shopping List** — checkbox styling, strike-through, category headers
8. **Cooking Mode** — dark immersive UI, large step text, progress bar, inline ingredient highlights
9. **Filter Chips** — horizontally scrollable tag filters
10. **Responsive Breakpoints** — phone default, tablet (768px+), desktop (1024px+)
11. **Utilities** — fade-in animations, visually-hidden, safe-area-inset padding
12. **Light Mode Override** — `body.light-mode` variant

This file replaces `main.css` entirely. The exact CSS implementation will be ~600-800 lines following the design spec's colour palette and component patterns shown in the mockups.

The engineer should reference the visual mockups saved in `.superpowers/brainstorm/` for exact styling and refer to the spec at `docs/superpowers/specs/2026-03-28-meal-planner-redesign-design.md` for colours and component descriptions.

- [ ] **Step 2: Verify static file is served**

```bash
source venv/bin/activate
python manage.py collectstatic --noinput 2>&1 | tail -3
```

Expected: Static files collected successfully.

- [ ] **Step 3: Commit**

```bash
git add recipes/static/recipes/css/app.css
git commit -m "feat: add mobile-first CSS design system"
```

---

## Task 8: Base Template with HTMX, Alpine.js, Bottom Nav

**Files:**
- Create: `recipes/templates/base.html` (overwrite existing)
- Create: `recipes/templates/auth/login.html`
- Create: `recipes/templates/auth/register.html`

- [ ] **Step 1: Create new base.html**

Replace `recipes/templates/base.html` with mobile-first layout:

```html
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <meta name="theme-color" content="#1a1a2e">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>{% block title %}Meal Planner{% endblock %}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{% static 'recipes/css/app.css' %}">
    {% block extra_css %}{% endblock %}
</head>
<body class="dark-mode">
    {% csrf_token %}

    <main id="main-content" class="main-content">
        {% if messages %}
        <div class="toast-container">
            {% for message in messages %}
            <div class="toast toast-{{ message.tags }}" role="alert"
                 x-data="{ show: true }" x-show="show" x-init="setTimeout(() => show = false, 4000)">
                {{ message }}
            </div>
            {% endfor %}
        </div>
        {% endif %}

        {% block content %}{% endblock %}
    </main>

    {% if user.is_authenticated %}
    <nav class="bottom-nav" aria-label="Main navigation">
        <a href="{% url 'week' %}" class="nav-tab {% block nav_week %}{% endblock %}">
            <span class="nav-icon">📅</span>
            <span class="nav-label">This Week</span>
        </a>
        <a href="{% url 'recipe_list' %}" class="nav-tab {% block nav_recipes %}{% endblock %}">
            <span class="nav-icon">📖</span>
            <span class="nav-label">Recipes</span>
        </a>
        <a href="{% url 'shop' %}" class="nav-tab {% block nav_shop %}{% endblock %}">
            <span class="nav-icon">🛒</span>
            <span class="nav-label">Shop</span>
        </a>
        <a href="{% url 'settings' %}" class="nav-tab {% block nav_more %}{% endblock %}">
            <span class="nav-icon">⚙️</span>
            <span class="nav-label">More</span>
        </a>
    </nav>
    {% endif %}

    <script src="https://unpkg.com/htmx.org@2.0.4"></script>
    <script src="https://unpkg.com/alpinejs@3.14.8/dist/cdn.min.js" defer></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

- [ ] **Step 2: Create login.html**

Create `recipes/templates/auth/login.html`:

```html
{% extends "base.html" %}
{% block title %}Login — Meal Planner{% endblock %}

{% block content %}
<div class="auth-container">
    <h1 class="auth-title">Meal Planner</h1>
    <p class="auth-subtitle">Your living cookbook</p>

    <form method="post" class="auth-form">
        {% csrf_token %}
        <div class="form-group">
            <label for="id_username">Username</label>
            <input type="text" name="username" id="id_username" class="form-input" required autofocus>
        </div>
        <div class="form-group">
            <label for="id_password">Password</label>
            <input type="password" name="password" id="id_password" class="form-input" required>
        </div>
        {% if form.errors %}
        <div class="form-error">Invalid username or password.</div>
        {% endif %}
        <button type="submit" class="btn btn-primary btn-full">Log In</button>
    </form>

    <p class="auth-link">Don't have an account? <a href="{% url 'register' %}">Sign up</a></p>
</div>
{% endblock %}
```

- [ ] **Step 3: Create register.html**

Create `recipes/templates/auth/register.html`:

```html
{% extends "base.html" %}
{% block title %}Sign Up — Meal Planner{% endblock %}

{% block content %}
<div class="auth-container">
    <h1 class="auth-title">Create Account</h1>

    <form method="post" class="auth-form">
        {% csrf_token %}
        {% for field in form %}
        <div class="form-group">
            <label for="{{ field.id_for_label }}">{{ field.label }}</label>
            {{ field }}
            {% if field.errors %}
            <div class="form-error">{{ field.errors.0 }}</div>
            {% endif %}
            {% if field.help_text %}
            <small class="form-help">{{ field.help_text }}</small>
            {% endif %}
        </div>
        {% endfor %}
        <button type="submit" class="btn btn-primary btn-full">Sign Up</button>
    </form>

    <p class="auth-link">Already have an account? <a href="{% url 'login' %}">Log in</a></p>
</div>
{% endblock %}
```

- [ ] **Step 4: Update settings.py TEMPLATES to include auth template dir**

In `config/settings.py`, update TEMPLATES DIRS so Django finds `auth/login.html` for the built-in `LoginView`:

```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        ...
    },
]
```

Since `APP_DIRS` is True and the templates live in `recipes/templates/`, Django will find them. But the built-in `LoginView` looks for `registration/login.html` by default. Override in `config/urls.py`:

```python
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('recipes.urls')),
]
```

- [ ] **Step 5: Commit**

```bash
git add recipes/templates/base.html recipes/templates/auth/ config/urls.py
git commit -m "feat: mobile-first base template with HTMX, Alpine.js, bottom nav"
```

---

## Task 9: This Week View — Full Page + HTMX Partials

**Files:**
- Create: `recipes/views/week.py`
- Create: `recipes/templates/week/week.html`
- Create: `recipes/templates/week/partials/meal_card.html`
- Create: `recipes/templates/week/partials/recipe_picker.html`
- Create: `recipes/tests/test_views_week.py`
- Modify: `recipes/urls.py`

- [ ] **Step 1: Write failing test for week view**

Create `recipes/tests/test_views_week.py`:

```python
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from recipes.models import Recipe, MealPlan


class WeekViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("weektest", password="testpass123")
        self.client.login(username="weektest", password="testpass123")
        self.recipe = Recipe.objects.create(
            user=self.user, title="Test Dinner", steps="Cook it",
            prep_time=10, cook_time=20,
        )
        # Create a meal plan for today
        self.today = date.today()
        MealPlan.objects.create(
            user=self.user, date=self.today,
            meal_type="dinner", recipe=self.recipe,
        )

    def test_week_view_returns_200(self):
        response = self.client.get("/week/")
        self.assertEqual(response.status_code, 200)

    def test_week_view_shows_planned_meal(self):
        response = self.client.get("/week/")
        self.assertContains(response, "Test Dinner")

    def test_week_view_shows_empty_slots(self):
        response = self.client.get("/week/")
        self.assertContains(response, "Tap to add a meal")

    def test_week_view_requires_login(self):
        self.client.logout()
        response = self.client.get("/week/")
        self.assertEqual(response.status_code, 302)

    def test_week_navigation_offset(self):
        response = self.client.get("/week/?offset=1")
        self.assertEqual(response.status_code, 200)

    def test_slot_update_htmx(self):
        tomorrow = self.today + timedelta(days=1)
        response = self.client.post(
            f"/week/assign/{tomorrow}/dinner/",
            {"recipe_id": self.recipe.id},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            MealPlan.objects.filter(
                user=self.user, date=tomorrow, meal_type="dinner"
            ).exists()
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
source venv/bin/activate
python manage.py test recipes.tests.test_views_week -v2 2>&1 | tail -5
```

Expected: 404 — URL `/week/` not defined yet.

- [ ] **Step 3: Create week views**

Create `recipes/views/__init__.py`:

```python
from .week import week_view, week_slot, week_assign, week_suggest
from .auth import register_view
```

Create `recipes/views/auth.py`:

```python
from django.shortcuts import render, redirect
from django.contrib.auth import login
from recipes.forms.auth import CustomUserCreationForm


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('week')
    else:
        form = CustomUserCreationForm()
    return render(request, 'auth/register.html', {'form': form})
```

Create `recipes/forms/__init__.py`:

```python
from .auth import CustomUserCreationForm
```

Create `recipes/forms/auth.py`:

```python
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
```

Create `recipes/views/week.py`:

```python
from datetime import date, timedelta
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from recipes.models import Recipe, MealPlan


def _get_week_dates(offset=0):
    """Get Monday-Sunday dates for a given week offset from current week."""
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return [monday + timedelta(days=i) for i in range(7)]


def _build_week_context(user, offset=0):
    """Build the weekly meal plan context."""
    dates = _get_week_dates(offset)
    start, end = dates[0], dates[-1]

    meals = MealPlan.objects.with_related().for_user(user).in_date_range(start, end)
    meal_lookup = {(m.date, m.meal_type): m for m in meals}

    days = []
    for d in dates:
        meal = meal_lookup.get((d, 'dinner'))
        days.append({
            'date': d,
            'day_name': d.strftime('%a'),
            'day_num': d.day,
            'is_today': d == date.today(),
            'meal': meal,
        })

    return {
        'days': days,
        'week_start': start,
        'week_end': end,
        'offset': offset,
        'today': date.today(),
    }


@login_required
def week_view(request):
    offset = int(request.GET.get('offset', 0))
    context = _build_week_context(request.user, offset)
    return render(request, 'week/week.html', context)


@login_required
def week_slot(request, date_str, meal_type):
    """HTMX partial: render a single meal card."""
    slot_date = date.fromisoformat(date_str)
    meal = MealPlan.objects.filter(
        user=request.user, date=slot_date, meal_type=meal_type
    ).select_related('recipe').first()
    return render(request, 'week/partials/meal_card.html', {
        'day': {
            'date': slot_date,
            'day_name': slot_date.strftime('%a'),
            'day_num': slot_date.day,
            'is_today': slot_date == date.today(),
            'meal': meal,
        }
    })


@login_required
def week_assign(request, date_str, meal_type):
    """HTMX: assign a recipe to a meal slot."""
    if request.method == 'GET':
        recipes = Recipe.objects.for_user(request.user).with_related()
        query = request.GET.get('q', '')
        if query:
            recipes = recipes.search(query)
        return render(request, 'week/partials/recipe_picker.html', {
            'recipes': recipes[:20],
            'date_str': date_str,
            'meal_type': meal_type,
        })

    # POST: assign recipe to slot
    recipe_id = request.POST.get('recipe_id')
    recipe = get_object_or_404(Recipe, id=recipe_id, user=request.user)
    slot_date = date.fromisoformat(date_str)
    MealPlan.objects.update_or_create(
        user=request.user, date=slot_date, meal_type=meal_type,
        defaults={'recipe': recipe},
    )
    meal = MealPlan.objects.select_related('recipe').get(
        user=request.user, date=slot_date, meal_type=meal_type,
    )
    return render(request, 'week/partials/meal_card.html', {
        'day': {
            'date': slot_date,
            'day_name': slot_date.strftime('%a'),
            'day_num': slot_date.day,
            'is_today': slot_date == date.today(),
            'meal': meal,
        }
    })


@login_required
def week_suggest(request):
    """HTMX: AI-powered meal suggestions for empty slots."""
    # Placeholder — will be implemented in AI integration task
    return HttpResponse('<div class="suggestion-placeholder">Coming soon</div>')
```

- [ ] **Step 4: Create URL configuration**

Replace `recipes/urls.py`:

```python
from django.urls import path
from .views import week, auth

urlpatterns = [
    # Home redirects to week
    path('', week.week_view, name='home'),

    # Week views
    path('week/', week.week_view, name='week'),
    path('week/slot/<str:date_str>/<str:meal_type>/', week.week_slot, name='week_slot'),
    path('week/assign/<str:date_str>/<str:meal_type>/', week.week_assign, name='week_assign'),
    path('week/suggest/', week.week_suggest, name='week_suggest'),

    # Auth
    path('register/', auth.register_view, name='register'),
]
```

Update `config/urls.py` to set `LOGIN_URL`:

Add to `config/settings.py`:

```python
LOGIN_URL = '/accounts/login/'
```

- [ ] **Step 5: Create week.html template**

Create `recipes/templates/week/week.html`:

```html
{% extends "base.html" %}
{% block title %}This Week — Meal Planner{% endblock %}
{% block nav_week %}active{% endblock %}

{% block content %}
<div class="screen">
    <div class="week-header">
        <a href="?offset={{ offset|add:'-1' }}" class="week-nav">‹</a>
        <div class="week-title">
            <h1>This Week</h1>
            <span class="week-dates">{{ week_start|date:"j M" }} – {{ week_end|date:"j M" }}</span>
        </div>
        <a href="?offset={{ offset|add:'1' }}" class="week-nav">›</a>
    </div>

    <div class="day-list" id="day-list">
        {% for day in days %}
            {% include "week/partials/meal_card.html" %}
        {% endfor %}
    </div>

    <div class="week-actions">
        <a href="{% url 'shop' %}" class="btn btn-outline">🛒 Shopping List</a>
        <button class="btn btn-outline"
                hx-post="{% url 'week_suggest' %}"
                hx-target="#day-list"
                hx-swap="innerHTML">
            ✨ Suggest Meals
        </button>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 6: Create meal_card.html partial**

Create `recipes/templates/week/partials/meal_card.html`:

```html
<div class="day-card {% if day.is_today %}day-card--today{% endif %} {% if not day.meal %}day-card--empty{% endif %}"
     id="day-{{ day.date|date:'Y-m-d' }}">
    <div class="day-card__header">
        <span class="day-card__label {% if day.is_today %}day-card__label--today{% endif %}">
            {{ day.day_name }} {{ day.day_num }}
        </span>
        {% if day.is_today %}
        <span class="badge badge--today">TODAY</span>
        {% endif %}
        {% if day.meal %}
        <span class="day-card__time">⏱ {{ day.meal.recipe.total_time }} min</span>
        {% endif %}
    </div>

    {% if day.meal %}
    <a href="{% url 'recipe_detail' day.meal.recipe.id %}" class="day-card__title">
        {{ day.meal.recipe.title }}
    </a>
    <div class="day-card__tags">
        {% for tag in day.meal.recipe.tags.all %}
        <span class="chip">{{ tag.name }}</span>
        {% endfor %}
        {% if day.meal.recipe.average_rating %}
        <span class="chip chip--accent">⭐ {{ day.meal.recipe.average_rating }}</span>
        {% endif %}
    </div>
    {% if day.is_today %}
    <a href="{% url 'cook' day.meal.recipe.id %}" class="btn btn-primary btn-full mt-sm">
        Start Cooking →
    </a>
    {% endif %}
    {% else %}
    <div class="day-card__empty"
         hx-get="{% url 'week_assign' day.date|date:'Y-m-d' 'dinner' %}"
         hx-target="#day-{{ day.date|date:'Y-m-d' }}"
         hx-swap="outerHTML">
        Tap to add a meal...
    </div>
    {% endif %}
</div>
```

- [ ] **Step 7: Create recipe_picker.html partial**

Create `recipes/templates/week/partials/recipe_picker.html`:

```html
<div class="picker-overlay" x-data="{ search: '' }">
    <div class="picker">
        <div class="picker__header">
            <h3>Pick a recipe</h3>
            <button class="picker__close" onclick="this.closest('.picker-overlay').remove()">✕</button>
        </div>
        <input type="search" class="form-input" placeholder="Search recipes..."
               hx-get="{% url 'week_assign' date_str meal_type %}"
               hx-trigger="keyup changed delay:300ms"
               hx-target="closest .picker-overlay"
               hx-swap="outerHTML"
               name="q">
        <div class="picker__list">
            {% for recipe in recipes %}
            <button class="picker__item"
                    hx-post="{% url 'week_assign' date_str meal_type %}"
                    hx-vals='{"recipe_id": "{{ recipe.id }}"}'
                    hx-target="#day-{{ date_str }}"
                    hx-swap="outerHTML">
                <span class="picker__item-title">{{ recipe.title }}</span>
                <span class="picker__item-meta">
                    {% if recipe.total_time %}⏱ {{ recipe.total_time }}min{% endif %}
                </span>
            </button>
            {% empty %}
            <p class="picker__empty">No recipes found. <a href="{% url 'recipe_create' %}">Add one?</a></p>
            {% endfor %}
        </div>
    </div>
</div>
```

- [ ] **Step 8: Run tests**

```bash
source venv/bin/activate
python manage.py test recipes.tests.test_views_week -v2
```

Expected: All tests pass.

- [ ] **Step 9: Commit**

```bash
git add recipes/views/ recipes/templates/week/ recipes/urls.py recipes/forms/ recipes/tests/test_views_week.py config/urls.py config/settings.py
git commit -m "feat: This Week screen with HTMX meal assignment"
```

---

## Task 10: Recipe Collection & Detail Views

**Files:**
- Create: `recipes/views/recipes.py`
- Create: `recipes/templates/recipes/list.html`
- Create: `recipes/templates/recipes/detail.html`
- Create: `recipes/templates/recipes/form.html`
- Create: `recipes/templates/recipes/partials/recipe_card.html`
- Create: `recipes/templates/recipes/partials/search_results.html`
- Create: `recipes/forms/recipe.py`
- Create: `recipes/tests/test_views_recipes.py`
- Modify: `recipes/urls.py`
- Modify: `recipes/views/__init__.py`

This task creates the recipe CRUD views, recipe list with search/filter, recipe detail with cooking notes, and the add/edit form with structured ingredient entry. Follow the same TDD pattern as Task 9: write failing tests first, implement views, create templates, verify tests pass.

The recipe list template uses HTMX for search (`hx-get` on the search input triggers a partial swap of the recipe cards). The recipe detail template shows the full recipe with structured ingredients and the cooking notes timeline. The form template includes a dynamic ingredient entry section using Alpine.js (`x-data` with an array of ingredient rows that can be added/removed).

URL patterns to add:

```python
path('recipes/', recipes.recipe_list, name='recipe_list'),
path('recipes/search/', recipes.recipe_search, name='recipe_search'),
path('recipes/new/', recipes.recipe_create, name='recipe_create'),
path('recipes/<int:pk>/', recipes.recipe_detail, name='recipe_detail'),
path('recipes/<int:pk>/edit/', recipes.recipe_update, name='recipe_update'),
path('recipes/<int:pk>/delete/', recipes.recipe_delete, name='recipe_delete'),
path('recipes/<int:pk>/favourite/', recipes.toggle_favourite, name='toggle_favourite'),
```

- [ ] **Step 1: Write failing tests**
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Create recipe views** (recipe_list, recipe_detail, recipe_create, recipe_update, recipe_delete, recipe_search, toggle_favourite)
- [ ] **Step 4: Create RecipeForm with structured ingredient handling**
- [ ] **Step 5: Create templates** (list.html, detail.html, form.html, partials/)
- [ ] **Step 6: Update urls.py with recipe URL patterns**
- [ ] **Step 7: Run tests to verify they pass**
- [ ] **Step 8: Commit**

```bash
git add recipes/views/recipes.py recipes/templates/recipes/ recipes/forms/recipe.py recipes/urls.py recipes/tests/test_views_recipes.py
git commit -m "feat: recipe collection and detail views with HTMX search"
```

---

## Task 11: Cooking Mode

**Files:**
- Create: `recipes/views/cook.py`
- Create: `recipes/templates/cook/cook.html`
- Create: `recipes/templates/cook/partials/step.html`
- Create: `recipes/templates/cook/partials/done.html`
- Create: `recipes/forms/cooking.py`
- Create: `recipes/tests/test_views_cook.py`
- Create: `recipes/static/recipes/js/app.js`
- Modify: `recipes/urls.py`
- Modify: `recipes/views/__init__.py`

Cooking mode is a distraction-free step-by-step view. The view parses the recipe's `cooking_mode_steps` JSON (or falls back to splitting `steps` by newlines). Each step is served as an HTMX partial. Alpine.js handles the Wake Lock API to keep the screen on, and Prev/Next navigation.

The `done.html` partial shows a quick rating form (`CookingNoteForm`) with 1-5 star rating, optional text note, and "would make again" toggle.

URL patterns:

```python
path('cook/<int:pk>/', cook.cook_view, name='cook'),
path('cook/<int:pk>/step/<int:step>/', cook.cook_step, name='cook_step'),
path('cook/<int:pk>/done/', cook.cook_done, name='cook_done'),
```

`app.js` contains the Alpine.js component for Wake Lock:

```javascript
document.addEventListener('alpine:init', () => {
    Alpine.data('cookingMode', () => ({
        wakeLock: null,
        async init() {
            if ('wakeLock' in navigator) {
                try {
                    this.wakeLock = await navigator.wakeLock.request('screen');
                } catch (e) { /* permission denied or not supported */ }
            }
        },
        destroy() {
            if (this.wakeLock) this.wakeLock.release();
        }
    }));
});
```

- [ ] **Step 1: Write failing tests** for cook_view, cook_step, cook_done
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Create CookingNoteForm**
- [ ] **Step 4: Create cook views**
- [ ] **Step 5: Create templates** (cook.html, step.html, done.html)
- [ ] **Step 6: Create app.js** with Wake Lock Alpine component
- [ ] **Step 7: Update urls.py**
- [ ] **Step 8: Run tests to verify they pass**
- [ ] **Step 9: Commit**

```bash
git add recipes/views/cook.py recipes/templates/cook/ recipes/forms/cooking.py recipes/static/recipes/js/app.js recipes/urls.py recipes/tests/test_views_cook.py
git commit -m "feat: cooking mode with step-by-step HTMX and wake lock"
```

---

## Task 12: Shopping List

**Files:**
- Create: `recipes/views/shop.py`
- Create: `recipes/templates/shop/shop.html`
- Create: `recipes/templates/shop/partials/item.html`
- Create: `recipes/templates/shop/partials/add_item.html`
- Create: `recipes/tests/test_views_shop.py`
- Modify: `recipes/urls.py`
- Modify: `recipes/views/__init__.py`

The shopping list view generates items from the current week's meal plan using `RecipeService.generate_structured_shopping_list()`. Items are grouped by ingredient category. Manual items come from `ShoppingListItem`. Ticking an item is an HTMX POST that toggles the `checked` state.

URL patterns:

```python
path('shop/', shop.shop_view, name='shop'),
path('shop/generate/', shop.shop_generate, name='shop_generate'),
path('shop/toggle/<int:pk>/', shop.shop_toggle, name='shop_toggle'),
path('shop/add/', shop.shop_add, name='shop_add'),
```

- [ ] **Step 1: Write failing tests** for shop_view, shop_generate, shop_toggle, shop_add
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Create shop views**
- [ ] **Step 4: Create templates** (shop.html, partials/)
- [ ] **Step 5: Update urls.py**
- [ ] **Step 6: Run tests to verify they pass**
- [ ] **Step 7: Commit**

```bash
git add recipes/views/shop.py recipes/templates/shop/ recipes/urls.py recipes/tests/test_views_shop.py
git commit -m "feat: shopping list with structured ingredients and HTMX tick-off"
```

---

## Task 13: Settings View

**Files:**
- Create: `recipes/views/settings.py`
- Create: `recipes/templates/settings/settings.html`
- Modify: `recipes/urls.py`
- Modify: `recipes/views/__init__.py`

Simple settings page for meal planner preferences (max cook times, avoid repeat days) and account info.

URL pattern:

```python
path('settings/', settings_views.settings_view, name='settings'),
```

- [ ] **Step 1: Create settings view and template**
- [ ] **Step 2: Update urls.py**
- [ ] **Step 3: Verify it loads**
- [ ] **Step 4: Commit**

```bash
git add recipes/views/settings.py recipes/templates/settings/ recipes/urls.py
git commit -m "feat: settings screen for meal planner preferences"
```

---

## Task 14: AI Service Update for Structured Recipes

**Files:**
- Modify: `recipes/services/ai_service.py`
- Create: `recipes/tests/test_ai_structured.py`

Update `AIService.generate_recipe_from_prompt()` to return structured data that can directly populate `Recipe` + `RecipeIngredient` records. The prompt instructs GPT to return JSON with separated ingredients (name, quantity, unit).

- [ ] **Step 1: Write failing test**

```python
from django.test import TestCase
from unittest.mock import patch, MagicMock
from recipes.services.ai_service import AIService


class AIStructuredRecipeTest(TestCase):
    @patch('recipes.services.ai_service.openai')
    def test_parse_structured_recipe(self, mock_openai):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''{
            "title": "Lemon Chicken",
            "description": "A simple lemon chicken dish",
            "prep_time": 10,
            "cook_time": 30,
            "servings": 4,
            "difficulty": "easy",
            "ingredients": [
                {"name": "chicken breast", "quantity": 500, "unit": "g", "category": "meat"},
                {"name": "lemon", "quantity": 2, "unit": "piece", "category": "produce"}
            ],
            "steps": [
                "Season the chicken with salt and pepper",
                "Squeeze lemon juice over the chicken",
                "Bake at 200°C for 30 minutes"
            ]
        }'''
        mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response

        result = AIService.generate_structured_recipe("chicken and lemon")
        self.assertEqual(result['title'], "Lemon Chicken")
        self.assertEqual(len(result['ingredients']), 2)
        self.assertEqual(result['ingredients'][0]['name'], "chicken breast")
        self.assertEqual(result['steps'][0], "Season the chicken with salt and pepper")
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement generate_structured_recipe in AIService**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

```bash
git add recipes/services/ai_service.py recipes/tests/test_ai_structured.py
git commit -m "feat: AI service returns structured recipe data with ingredients"
```

---

## Task 15: PWA Setup

**Files:**
- Create: `recipes/static/recipes/manifest.json`
- Create: `recipes/static/recipes/sw.js`
- Modify: `recipes/templates/base.html`

- [ ] **Step 1: Create manifest.json**

```json
{
    "name": "Meal Planner",
    "short_name": "Meals",
    "description": "Your living cookbook — plan meals, cook, shop",
    "start_url": "/week/",
    "display": "standalone",
    "background_color": "#1a1a2e",
    "theme_color": "#1a1a2e",
    "icons": [
        {
            "src": "/static/recipes/icons/icon-192.png",
            "sizes": "192x192",
            "type": "image/png"
        },
        {
            "src": "/static/recipes/icons/icon-512.png",
            "sizes": "512x512",
            "type": "image/png"
        }
    ]
}
```

- [ ] **Step 2: Create minimal service worker**

```javascript
const CACHE_NAME = 'meal-planner-v1';
const PRECACHE_URLS = [
    '/static/recipes/css/app.css',
    '/static/recipes/js/app.js',
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS))
    );
});

self.addEventListener('fetch', event => {
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).catch(() => caches.match('/week/'))
        );
    }
});
```

- [ ] **Step 3: Add manifest and SW registration to base.html**

Add to `<head>` in base.html:

```html
<link rel="manifest" href="{% static 'recipes/manifest.json' %}">
```

Add before `</body>`:

```html
<script>
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register("{% static 'recipes/sw.js' %}");
}
</script>
```

- [ ] **Step 4: Commit**

```bash
git add recipes/static/recipes/manifest.json recipes/static/recipes/sw.js recipes/templates/base.html
git commit -m "feat: PWA manifest and service worker for home screen install"
```

---

## Task 16: Cleanup and Final Integration

**Files:**
- Remove: `recipes/static/recipes/css/main.css`
- Remove: `frontend/` directory
- Remove: old template files no longer used
- Modify: `recipes/tests/` — update existing tests for new model imports

- [ ] **Step 1: Remove old files**

```bash
rm recipes/static/recipes/css/main.css
rm -rf frontend/
rm recipes/templates/recipes/react_demo.html
rm recipes/templates/recipes/comparison_banner.html
```

- [ ] **Step 2: Update existing test imports**

Update all files in `recipes/tests/` to import from `recipes.models` (which now points to the package). Most imports should work unchanged since `__init__.py` re-exports everything. Fix any import errors for removed models (`FamilyPreference`, `GeneratedMealPlan`, etc.) by removing or updating the affected tests.

- [ ] **Step 3: Run full test suite**

```bash
source venv/bin/activate
python manage.py test recipes -v2
```

Fix any failures.

- [ ] **Step 4: Run Django system checks**

```bash
source venv/bin/activate
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 5: Start server and verify**

```bash
source venv/bin/activate
python manage.py runserver 8000
```

Visit `http://localhost:8000/` — should redirect to login. After login, should see the This Week view with bottom nav.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: remove old templates, CSS, and frontend; update test imports"
```

---

## Summary

| Task | Component | Key Deliverable |
|------|-----------|-----------------|
| 1 | Dependencies | HTMX + django-htmx installed and configured |
| 2 | Models — Managers | Extracted into models package |
| 3 | Models — Recipe/Ingredient | Ingredient, RecipeIngredient, Tag.tag_type, Recipe.source |
| 4 | Models — Cooking/Shopping | CookingNote, ShoppingListItem, MealPlan.notes |
| 5 | Migration | Swap models.py → models package, generate + apply migrations |
| 6 | Services | Updated for structured ingredients and CookingNote |
| 7 | CSS | New mobile-first design system |
| 8 | Base Template | HTMX, Alpine.js, bottom nav, auth pages |
| 9 | This Week | Weekly view with HTMX meal assignment |
| 10 | Recipes | Collection, detail, CRUD with structured ingredients |
| 11 | Cooking Mode | Step-by-step with inline quantities and wake lock |
| 12 | Shopping List | Generated + manual items with tick-off |
| 13 | Settings | Meal planner preferences |
| 14 | AI Service | Structured recipe output from OpenAI |
| 15 | PWA | Manifest, service worker, installable |
| 16 | Cleanup | Remove old files, fix tests, verify |
