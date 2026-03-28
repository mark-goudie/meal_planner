# Household Sharing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add household sharing so two users can collaborate on a shared meal plan, shopping list, and selectively share recipes, joined via a 6-digit code.

**Architecture:** A new Household model with HouseholdMembership links users together. MealPlan and ShoppingListItem switch from user FK to household FK. Recipes get a `shared` boolean toggle. DayComment adds per-day notes. Registration accepts an optional household code to join an existing household.

**Tech Stack:** Django 4.2, existing HTMX + Alpine.js frontend, SQLite (dev)

**Spec:** `docs/superpowers/specs/2026-03-29-household-sharing-design.md`

---

## File Structure

### New Files

```
recipes/models/household.py          — Household, HouseholdMembership, DayComment models
recipes/tests/test_household.py      — tests for household models, sharing logic, views
recipes/templates/settings/household_section.html — HTMX partial for household settings
recipes/templates/week/partials/day_comment.html  — HTMX partial for day comment form
recipes/templates/week/partials/day_comment_display.html — inline comment display
```

### Modified Files

```
recipes/models/__init__.py           — export new models
recipes/models/recipe.py             — add `shared` field to Recipe
recipes/models/meal_plan.py          — MealPlan: user FK → household FK + added_by FK
recipes/models/shopping.py           — ShoppingListItem: user FK → household FK + added_by FK
recipes/models/managers.py           — update MealPlanQuerySet.for_user → for_household
recipes/views/auth.py                — handle household code on registration
recipes/views/week.py                — use household for meal plan queries, add day comment views
recipes/views/shop.py                — use household for shopping list queries
recipes/views/settings.py            — add household management (name, code, members, regenerate)
recipes/views/recipes.py             — recipe list shows household shared recipes
recipes/views/__init__.py            — export new views
recipes/urls.py                      — add day comment and household URLs
recipes/templates/auth/register.html — add household code field
recipes/templates/settings/settings.html — add household section
recipes/templates/week/partials/meal_card.html — show day comments, added-by
recipes/templates/shop/shop.html     — show added-by on manual items
recipes/templates/shop/partials/item.html — show added-by
recipes/templates/recipes/form.html  — add "Share with household" toggle
recipes/templates/recipes/partials/recipe_card.html — show "Shared by" label
recipes/templates/recipes/list.html  — include shared recipes in listing
```

---

## Task 1: Household and HouseholdMembership Models

**Files:**
- Create: `recipes/models/household.py`
- Modify: `recipes/models/__init__.py`
- Create: `recipes/tests/test_household.py`

- [ ] **Step 1: Write failing tests for Household and HouseholdMembership**

Create `recipes/tests/test_household.py`:

```python
from django.test import TestCase
from django.contrib.auth.models import User
from recipes.models.household import Household, HouseholdMembership, generate_household_code


class HouseholdModelTest(TestCase):
    def test_create_household(self):
        user = User.objects.create_user("mark", password="testpass123")
        household = Household.objects.create(name="The Goudies", created_by=user)
        self.assertEqual(str(household), "The Goudies")
        self.assertEqual(len(household.code), 6)
        self.assertTrue(household.code.isalnum())

    def test_household_code_auto_generated(self):
        user = User.objects.create_user("mark", password="testpass123")
        h1 = Household.objects.create(name="House 1", created_by=user)
        h2 = Household.objects.create(name="House 2", created_by=user)
        self.assertNotEqual(h1.code, h2.code)

    def test_household_code_excludes_ambiguous_chars(self):
        for _ in range(20):
            code = generate_household_code()
            for char in "0O1IL":
                self.assertNotIn(char, code)

    def test_create_membership(self):
        user = User.objects.create_user("mark", password="testpass123")
        household = Household.objects.create(name="Test", created_by=user)
        membership = HouseholdMembership.objects.create(user=user, household=household)
        self.assertEqual(user.household_membership.household, household)

    def test_household_members(self):
        user1 = User.objects.create_user("mark", password="testpass123")
        user2 = User.objects.create_user("lisa", password="testpass123")
        household = Household.objects.create(name="Test", created_by=user1)
        HouseholdMembership.objects.create(user=user1, household=household)
        HouseholdMembership.objects.create(user=user2, household=household)
        self.assertEqual(household.members.count(), 2)

    def test_membership_is_one_to_one(self):
        user = User.objects.create_user("mark", password="testpass123")
        h1 = Household.objects.create(name="House 1", created_by=user)
        HouseholdMembership.objects.create(user=user, household=h1)
        h2 = Household.objects.create(name="House 2", created_by=user)
        with self.assertRaises(Exception):
            HouseholdMembership.objects.create(user=user, household=h2)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source venv/bin/activate
python manage.py test recipes.tests.test_household -v2 2>&1 | tail -5
```

Expected: ImportError — `recipes.models.household` does not exist.

- [ ] **Step 3: Create household.py**

Create `recipes/models/household.py`:

```python
import secrets
import string

from django.contrib.auth.models import User
from django.db import models


def generate_household_code():
    """Generate a 6-character alphanumeric code excluding ambiguous characters."""
    chars = string.ascii_uppercase + string.digits
    for ch in "0O1IL":
        chars = chars.replace(ch, "")
    while True:
        code = "".join(secrets.choice(chars) for _ in range(6))
        if not Household.objects.filter(code=code).exists():
            return code


class Household(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=8, unique=True, editable=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_household_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class HouseholdMembership(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="household_membership")
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="members")
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} → {self.household.name}"


class DayComment(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="day_comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    text = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("household", "user", "date")
        ordering = ["date", "created_at"]

    def __str__(self):
        return f"{self.user.username} on {self.date}: {self.text}"
```

- [ ] **Step 4: Update models/__init__.py**

Add to `recipes/models/__init__.py`:

```python
from .household import DayComment, Household, HouseholdMembership, generate_household_code
```

- [ ] **Step 5: Generate and apply migrations**

```bash
python manage.py makemigrations recipes
python manage.py migrate
```

- [ ] **Step 6: Run tests**

```bash
python manage.py test recipes.tests.test_household -v2
```

Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add recipes/models/household.py recipes/models/__init__.py recipes/tests/test_household.py recipes/migrations/
git commit -m "feat: add Household, HouseholdMembership, DayComment models"
```

---

## Task 2: Add `shared` Field to Recipe, Migrate MealPlan and ShoppingListItem

**Files:**
- Modify: `recipes/models/recipe.py` — add `shared` BooleanField
- Modify: `recipes/models/meal_plan.py` — add `household` FK, `added_by` FK to MealPlan
- Modify: `recipes/models/shopping.py` — add `household` FK, `added_by` FK to ShoppingListItem
- Modify: `recipes/models/managers.py` — update MealPlanQuerySet
- Modify: `recipes/tests/test_household.py` — add tests

This task adds the new fields alongside the existing `user` FK fields. The data migration (Task 3) will populate them and remove the old FKs.

- [ ] **Step 1: Write failing tests**

Add to `recipes/tests/test_household.py`:

```python
from recipes.models import Recipe, MealPlan, ShoppingListItem
from recipes.models.household import Household, HouseholdMembership
from datetime import date


class SharedRecipeTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user("mark", password="testpass123")
        self.user2 = User.objects.create_user("lisa", password="testpass123")
        self.household = Household.objects.create(name="Test", created_by=self.user1)
        HouseholdMembership.objects.create(user=self.user1, household=self.household)
        HouseholdMembership.objects.create(user=self.user2, household=self.household)

    def test_recipe_shared_default_false(self):
        recipe = Recipe.objects.create(user=self.user1, title="Test", steps="cook")
        self.assertFalse(recipe.shared)

    def test_recipe_shared_toggle(self):
        recipe = Recipe.objects.create(user=self.user1, title="Test", steps="cook", shared=True)
        self.assertTrue(recipe.shared)


class SharedMealPlanTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user("mark", password="testpass123")
        self.user2 = User.objects.create_user("lisa", password="testpass123")
        self.household = Household.objects.create(name="Test", created_by=self.user1)
        HouseholdMembership.objects.create(user=self.user1, household=self.household)
        HouseholdMembership.objects.create(user=self.user2, household=self.household)
        self.recipe = Recipe.objects.create(user=self.user1, title="Dinner", steps="cook")

    def test_meal_plan_with_household(self):
        mp = MealPlan.objects.create(
            household=self.household, added_by=self.user1,
            date=date.today(), meal_type="dinner", recipe=self.recipe,
        )
        self.assertEqual(mp.household, self.household)
        self.assertEqual(mp.added_by, self.user1)

    def test_both_users_see_same_meal_plan(self):
        MealPlan.objects.create(
            household=self.household, added_by=self.user1,
            date=date.today(), meal_type="dinner", recipe=self.recipe,
        )
        plans = MealPlan.objects.filter(household=self.household)
        self.assertEqual(plans.count(), 1)


class SharedShoppingListTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user("mark", password="testpass123")
        self.user2 = User.objects.create_user("lisa", password="testpass123")
        self.household = Household.objects.create(name="Test", created_by=self.user1)
        HouseholdMembership.objects.create(user=self.user1, household=self.household)
        HouseholdMembership.objects.create(user=self.user2, household=self.household)

    def test_shopping_item_with_household(self):
        item = ShoppingListItem.objects.create(
            household=self.household, added_by=self.user1, name="Eggs",
        )
        self.assertEqual(item.household, self.household)

    def test_both_users_see_same_items(self):
        ShoppingListItem.objects.create(
            household=self.household, added_by=self.user1, name="Eggs",
        )
        ShoppingListItem.objects.create(
            household=self.household, added_by=self.user2, name="Milk",
        )
        items = ShoppingListItem.objects.filter(household=self.household)
        self.assertEqual(items.count(), 2)
```

- [ ] **Step 2: Add fields to models**

In `recipes/models/recipe.py`, add to `Recipe` class after `is_ai_generated`:

```python
shared = models.BooleanField(default=False, help_text="Share with household members")
```

In `recipes/models/meal_plan.py`, update `MealPlan`:
- Add `household` FK (nullable initially for migration): `household = models.ForeignKey("household.Household", on_delete=models.CASCADE, related_name="meal_plans", null=True, blank=True)`
- Add `added_by`: `added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="+")`
- Keep existing `user` FK for now (removed in Task 3 migration)
- Update `unique_together` to `("household", "date", "meal_type")`

Note: Use string reference `"Household"` for the FK since it's in the same app.

In `recipes/models/shopping.py`, update `ShoppingListItem`:
- Add `household` FK (nullable initially): `household = models.ForeignKey("Household", on_delete=models.CASCADE, related_name="shopping_items", null=True, blank=True)`
- Add `added_by`: `added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="+")`
- Keep existing `user` FK for now

In `recipes/models/managers.py`, add a `for_household` method to `MealPlanQuerySet`:

```python
def for_household(self, household):
    return self.filter(household=household)
```

And update `MealPlanManager` to proxy it.

- [ ] **Step 3: Generate migrations**

```bash
python manage.py makemigrations recipes
python manage.py migrate
```

- [ ] **Step 4: Run tests**

```bash
python manage.py test recipes.tests.test_household -v2
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add shared field to Recipe, household FK to MealPlan and ShoppingListItem"
```

---

## Task 3: Data Migration — Create Households for Existing Users

**Files:**
- Create: new migration via `makemigrations --empty`

This migration:
1. Creates a Household for each existing user who doesn't have one
2. Creates HouseholdMembership linking user to their household
3. Populates `MealPlan.household` and `MealPlan.added_by` from `MealPlan.user`
4. Populates `ShoppingListItem.household` and `ShoppingListItem.added_by` from `ShoppingListItem.user`

- [ ] **Step 1: Create data migration**

```bash
python manage.py makemigrations recipes --empty -n populate_households
```

Edit the generated migration:

```python
from django.db import migrations


def create_households(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Household = apps.get_model("recipes", "Household")
    HouseholdMembership = apps.get_model("recipes", "HouseholdMembership")
    MealPlan = apps.get_model("recipes", "MealPlan")
    ShoppingListItem = apps.get_model("recipes", "ShoppingListItem")

    import secrets
    import string

    chars = string.ascii_uppercase + string.digits
    for ch in "0O1IL":
        chars = chars.replace(ch, "")

    for user in User.objects.all():
        if not HouseholdMembership.objects.filter(user=user).exists():
            code = "".join(secrets.choice(chars) for _ in range(6))
            while Household.objects.filter(code=code).exists():
                code = "".join(secrets.choice(chars) for _ in range(6))

            household = Household.objects.create(
                name=f"{user.username}'s Kitchen",
                code=code,
                created_by=user,
            )
            HouseholdMembership.objects.create(user=user, household=household)

            # Migrate user's meal plans
            MealPlan.objects.filter(user=user).update(household=household, added_by=user)

            # Migrate user's shopping items
            ShoppingListItem.objects.filter(user=user).update(household=household, added_by=user)


def reverse_migration(apps, schema_editor):
    pass  # No reverse needed


class Migration(migrations.Migration):
    dependencies = [
        ("recipes", "PREVIOUS_MIGRATION"),  # Replace with actual name
    ]

    operations = [
        migrations.RunPython(create_households, reverse_migration),
    ]
```

Replace `"PREVIOUS_MIGRATION"` with the actual migration name from the previous task.

- [ ] **Step 2: Apply migration**

```bash
python manage.py migrate
```

- [ ] **Step 3: Verify data migrated**

```bash
python -c "
import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); django.setup()
from recipes.models.household import Household, HouseholdMembership
from recipes.models import MealPlan
print(f'Households: {Household.objects.count()}')
print(f'Memberships: {HouseholdMembership.objects.count()}')
print(f'MealPlans with household: {MealPlan.objects.filter(household__isnull=False).count()}')
print(f'MealPlans without household: {MealPlan.objects.filter(household__isnull=True).count()}')
"
```

Expected: All meal plans should have a household. No orphans.

- [ ] **Step 4: Commit**

```bash
git add recipes/migrations/
git commit -m "feat: data migration — create households for existing users"
```

---

## Task 4: Remove Old user FK from MealPlan and ShoppingListItem

**Files:**
- Modify: `recipes/models/meal_plan.py` — remove `user` FK, make `household` non-nullable
- Modify: `recipes/models/shopping.py` — remove `user` FK, make `household` non-nullable
- Modify: `recipes/models/managers.py` — remove `for_user` from MealPlanQuerySet

- [ ] **Step 1: Update models**

In `recipes/models/meal_plan.py`:
- Remove `user` FK entirely
- Change `household` from nullable to required: `household = models.ForeignKey("Household", on_delete=models.CASCADE, related_name="meal_plans")`
- Update `unique_together` to `("household", "date", "meal_type")`
- Update `__str__` to not reference user

In `recipes/models/shopping.py`:
- Remove `user` FK
- Change `household` from nullable to required

In `recipes/models/managers.py`:
- Remove `for_user` from MealPlanQuerySet and MealPlanManager
- Keep `for_household`

- [ ] **Step 2: Generate and apply migration**

```bash
python manage.py makemigrations recipes
python manage.py migrate
```

- [ ] **Step 3: Run all household tests**

```bash
python manage.py test recipes.tests.test_household -v2
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: remove user FK from MealPlan and ShoppingListItem, household is now required"
```

---

## Task 5: Update Registration to Support Household Code

**Files:**
- Modify: `recipes/views/auth.py`
- Modify: `recipes/templates/auth/register.html`
- Modify: `recipes/tests/test_household.py`

- [ ] **Step 1: Write failing tests**

Add to `recipes/tests/test_household.py`:

```python
from django.test import Client
from django.urls import reverse


class RegistrationHouseholdTest(TestCase):
    def test_register_creates_new_household(self):
        client = Client()
        client.post(reverse("register"), {
            "username": "newuser", "password1": "testpass123!", "password2": "testpass123!",
        })
        user = User.objects.get(username="newuser")
        self.assertTrue(hasattr(user, "household_membership"))
        self.assertIsNotNone(user.household_membership.household)

    def test_register_with_valid_code_joins_household(self):
        owner = User.objects.create_user("owner", password="testpass123")
        household = Household.objects.create(name="Family", created_by=owner)
        HouseholdMembership.objects.create(user=owner, household=household)

        client = Client()
        client.post(reverse("register"), {
            "username": "joiner", "password1": "testpass123!", "password2": "testpass123!",
            "household_code": household.code,
        })
        joiner = User.objects.get(username="joiner")
        self.assertEqual(joiner.household_membership.household, household)

    def test_register_with_invalid_code_shows_error(self):
        client = Client()
        response = client.post(reverse("register"), {
            "username": "badcode", "password1": "testpass123!", "password2": "testpass123!",
            "household_code": "XXXXXX",
        })
        self.assertFalse(User.objects.filter(username="badcode").exists())
        self.assertContains(response, "Invalid household code")
```

- [ ] **Step 2: Update register_view**

In `recipes/views/auth.py`:

```python
from django.shortcuts import render, redirect
from django.contrib.auth import login
from recipes.forms.auth import CustomUserCreationForm
from recipes.models.household import Household, HouseholdMembership


def register_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        household_code = request.POST.get("household_code", "").strip().upper()

        if form.is_valid():
            # If code provided, validate it before creating user
            if household_code:
                try:
                    household = Household.objects.get(code=household_code)
                except Household.DoesNotExist:
                    form.add_error(None, "Invalid household code.")
                    return render(request, "auth/register.html", {
                        "form": form, "household_code": household_code,
                    })
            else:
                household = None

            user = form.save()

            if household:
                HouseholdMembership.objects.create(user=user, household=household)
            else:
                new_household = Household.objects.create(
                    name=f"{user.username}'s Kitchen",
                    created_by=user,
                )
                HouseholdMembership.objects.create(user=user, household=new_household)

            login(request, user)
            return redirect("week")
    else:
        form = CustomUserCreationForm()
        household_code = ""

    return render(request, "auth/register.html", {
        "form": form, "household_code": household_code,
    })
```

- [ ] **Step 3: Update register.html**

Add a household code field to the registration form, after the standard fields and before the submit button:

```html
<!-- Household Code -->
<div class="form-group">
  <label class="form-label" for="household_code">Household Code (optional)</label>
  <input type="text" id="household_code" name="household_code" class="form-input"
         value="{{ household_code }}" placeholder="e.g. A7K3NP" maxlength="6"
         style="text-transform: uppercase; letter-spacing: 0.2em; text-align: center;">
  <span class="form-help">Have a code from a family member? Enter it to join their household.</span>
</div>
```

- [ ] **Step 4: Run tests**

```bash
python manage.py test recipes.tests.test_household -v2
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: registration supports household code to join existing household"
```

---

## Task 6: Helper Function + Update Views to Use Household

**Files:**
- Modify: `recipes/views/week.py` — use household for queries
- Modify: `recipes/views/shop.py` — use household for queries
- Modify: `recipes/views/recipes.py` — include shared recipes in list
- Modify: `recipes/views/settings.py` — add household section
- Modify: `recipes/tests/test_household.py`

This is the largest task — every view that queries MealPlan or ShoppingListItem needs to switch from `user=request.user` to `household=household`.

- [ ] **Step 1: Create get_household helper**

Add to `recipes/models/household.py`:

```python
def get_household(user):
    """Get the user's household. Returns None if no household."""
    try:
        return user.household_membership.household
    except (HouseholdMembership.DoesNotExist, AttributeError):
        return None
```

- [ ] **Step 2: Update week.py**

In `recipes/views/week.py`:
- Import `get_household` from `..models.household`
- Update `_build_week_context` to accept `household` instead of `user`:
  - `meals = MealPlan.objects.with_related().for_household(household).in_date_range(start, end)`
  - Also load DayComments for the week: `DayComment.objects.filter(household=household, date__range=[start, end])`
  - Add comments to each day's context
- Update `week_view`: get household via `get_household(request.user)`, pass to `_build_week_context`
- Update `week_assign`: create MealPlan with `household=household, added_by=request.user` instead of `user=request.user`
- Update `week_suggest`: query MealPlan and Recipe via household
- Update `week_accept_suggestion`: same pattern
- Update `week_slot`: query via household

- [ ] **Step 3: Update shop.py**

In `recipes/views/shop.py`:
- Import `get_household`
- `shop_view`: query MealPlan and ShoppingListItem via household
- `shop_generate`: clear and create ShoppingListItems via household
- `shop_toggle`: verify item belongs to user's household
- `shop_add`: create with `household=household, added_by=request.user`

- [ ] **Step 4: Update recipes.py**

In `recipes/views/recipes.py`:
- `recipe_list_view`: show user's own recipes + household shared recipes:
  ```python
  household = get_household(request.user)
  recipes = Recipe.objects.filter(
      Q(user=request.user) |
      Q(shared=True, user__household_membership__household=household)
  ).distinct()
  ```
- `recipe_search`: same filter pattern
- `week_assign` recipe picker: same — show own + household shared
- `recipe_create_view`: handle `shared` checkbox from POST

- [ ] **Step 5: Update settings.py**

In `recipes/views/settings.py`:
- Show household info: name, code, members
- Handle household name update
- Handle code regeneration (POST to a new endpoint)

- [ ] **Step 6: Write integration tests**

Add to `recipes/tests/test_household.py`:

```python
class HouseholdViewIntegrationTest(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Family", created_by=None)
        self.user1 = User.objects.create_user("mark", password="testpass123")
        self.user2 = User.objects.create_user("lisa", password="testpass123")
        HouseholdMembership.objects.create(user=self.user1, household=self.household)
        HouseholdMembership.objects.create(user=self.user2, household=self.household)
        self.recipe = Recipe.objects.create(user=self.user1, title="Shared Dinner", steps="cook", shared=True)
        self.client1 = Client()
        self.client1.login(username="mark", password="testpass123")
        self.client2 = Client()
        self.client2.login(username="lisa", password="testpass123")

    def test_user2_sees_shared_recipe(self):
        response = self.client2.get(reverse("recipe_list"))
        self.assertContains(response, "Shared Dinner")

    def test_user2_does_not_see_unshared_recipe(self):
        Recipe.objects.create(user=self.user1, title="Private Meal", steps="cook", shared=False)
        response = self.client2.get(reverse("recipe_list"))
        self.assertNotContains(response, "Private Meal")

    def test_both_users_see_same_meal_plan(self):
        MealPlan.objects.create(
            household=self.household, added_by=self.user1,
            date=date.today(), meal_type="dinner", recipe=self.recipe,
        )
        response1 = self.client1.get(reverse("week"))
        response2 = self.client2.get(reverse("week"))
        self.assertContains(response1, "Shared Dinner")
        self.assertContains(response2, "Shared Dinner")

    def test_both_users_see_same_shopping_list(self):
        ShoppingListItem.objects.create(
            household=self.household, added_by=self.user1, name="Eggs",
        )
        response1 = self.client1.get(reverse("shop"))
        response2 = self.client2.get(reverse("shop"))
        self.assertContains(response1, "Eggs")
        self.assertContains(response2, "Eggs")
```

- [ ] **Step 7: Run all tests**

```bash
python manage.py test recipes -v0
```

Fix any failures from views that still reference `MealPlan.user` or `ShoppingListItem.user`.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: views use household for meal plans, shopping lists, and shared recipes"
```

---

## Task 7: Day Comments — Views and Templates

**Files:**
- Modify: `recipes/views/week.py` — add day comment views
- Create: `recipes/templates/week/partials/day_comment.html`
- Modify: `recipes/templates/week/partials/meal_card.html` — show comments
- Modify: `recipes/urls.py`
- Modify: `recipes/tests/test_household.py`

- [ ] **Step 1: Write failing tests**

Add to `recipes/tests/test_household.py`:

```python
class DayCommentTest(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Family", created_by=None)
        self.user = User.objects.create_user("mark", password="testpass123")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.client = Client()
        self.client.login(username="mark", password="testpass123")

    def test_add_day_comment(self):
        today = date.today().strftime("%Y-%m-%d")
        response = self.client.post(
            reverse("day_comment", args=[today]),
            {"text": "Work dinner tonight"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(DayComment.objects.filter(household=self.household, date=date.today()).exists())

    def test_comment_shows_on_week_view(self):
        DayComment.objects.create(
            household=self.household, user=self.user, date=date.today(), text="Out for dinner",
        )
        response = self.client.get(reverse("week"))
        self.assertContains(response, "Out for dinner")
```

- [ ] **Step 2: Add day_comment view to week.py**

```python
@login_required
def day_comment(request, date_str):
    """HTMX: add or update a day comment."""
    household = get_household(request.user)
    comment_date = date.fromisoformat(date_str)

    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        if text:
            DayComment.objects.update_or_create(
                household=household, user=request.user, date=comment_date,
                defaults={"text": text},
            )
        else:
            DayComment.objects.filter(
                household=household, user=request.user, date=comment_date,
            ).delete()

    comments = DayComment.objects.filter(household=household, date=comment_date).select_related("user")
    return render(request, "week/partials/day_comment.html", {
        "comments": comments, "date_str": date_str,
    })
```

- [ ] **Step 3: Create day_comment.html partial**

```html
{% for comment in comments %}
<div class="day-comment">
  <span class="text-muted text-sm">{{ comment.user.username }}:</span>
  <span class="text-sm">{{ comment.text }}</span>
</div>
{% endfor %}
```

- [ ] **Step 4: Update meal_card.html**

Add after the day-card header, before the meal content:

```html
{% if day.comments %}
<div class="day-card__comments">
  {% for comment in day.comments %}
  <div class="day-comment">
    <i class="bi bi-chat-dots" style="color: var(--accent); font-size: var(--text-xs);"></i>
    <span class="text-sm text-muted">{{ comment.user.username }}:</span>
    <span class="text-sm">{{ comment.text }}</span>
  </div>
  {% endfor %}
</div>
{% endif %}
```

Add a comment button/input area (inline HTMX form) at the bottom of the card:

```html
<div class="day-card__add-comment" x-data="{ open: false }">
  <button class="btn btn-ghost btn-sm" @click="open = !open" style="font-size: var(--text-xs); color: var(--text-dim);">
    <i class="bi bi-chat-dots"></i> {% if day.comments %}{{ day.comments|length }}{% else %}Add note{% endif %}
  </button>
  <div x-show="open" style="display: none; margin-top: var(--space-xs);">
    <form hx-post="{% url 'day_comment' day.date|date:'Y-m-d' %}"
          hx-target="#day-{{ day.date|date:'Y-m-d' }}-comments"
          hx-swap="innerHTML"
          class="flex gap-xs">
      {% csrf_token %}
      <input type="text" name="text" class="form-input" style="flex: 1; min-height: 36px; padding: 4px 8px; font-size: var(--text-sm);"
             placeholder="e.g. Work dinner tonight" maxlength="200"
             value="{{ day.my_comment }}">
      <button type="submit" class="btn btn-primary btn-sm" style="min-height: 36px;">
        <i class="bi bi-check-lg"></i>
      </button>
    </form>
  </div>
</div>
```

Add a container for comment display with an id for HTMX targeting:

```html
<div id="day-{{ day.date|date:'Y-m-d' }}-comments">
  {% if day.comments %}
    {% for comment in day.comments %}
    <div class="day-comment">
      <i class="bi bi-chat-dots" style="color: var(--accent); font-size: var(--text-xs);"></i>
      <span class="text-sm text-muted">{{ comment.user.username }}:</span>
      <span class="text-sm">{{ comment.text }}</span>
    </div>
    {% endfor %}
  {% endif %}
</div>
```

- [ ] **Step 5: Add CSS for day comments**

Add to `recipes/static/recipes/css/app.css`:

```css
.day-comment {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs) 0;
}

.day-card__comments {
  margin-bottom: var(--space-sm);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--border);
}

.day-card__add-comment {
  margin-top: var(--space-sm);
  padding-top: var(--space-sm);
  border-top: 1px solid var(--border);
}
```

- [ ] **Step 6: Add URL pattern**

```python
path("week/comment/<str:date_str>/", day_comment, name="day_comment"),
```

Update imports in urls.py and views/__init__.py.

- [ ] **Step 7: Update _build_week_context to include comments**

In `_build_week_context`, load comments and attach to each day:

```python
comments = DayComment.objects.filter(
    household=household, date__range=[start, end]
).select_related("user")
comment_lookup = {}
for c in comments:
    comment_lookup.setdefault(c.date, []).append(c)

# In the days loop:
for d in dates:
    meal = meal_lookup.get((d, "dinner"))
    day_comments = comment_lookup.get(d, [])
    my_comment = next((c.text for c in day_comments if c.user == user), "")
    days.append({
        "date": d,
        "day_name": d.strftime("%a"),
        "day_num": d.day,
        "is_today": d == date.today(),
        "meal": meal,
        "comments": day_comments,
        "my_comment": my_comment,
    })
```

Note: `_build_week_context` needs to accept both `household` and `user` now (user for `my_comment`).

- [ ] **Step 8: Run tests**

```bash
python manage.py test recipes.tests.test_household -v2
```

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: day comments for household meal planning notes"
```

---

## Task 8: Settings Page — Household Management

**Files:**
- Modify: `recipes/views/settings.py`
- Modify: `recipes/templates/settings/settings.html`
- Modify: `recipes/urls.py`

- [ ] **Step 1: Update settings_view**

Add household context to the settings view:

```python
from recipes.models.household import get_household, generate_household_code, Household

@login_required
def settings_view(request):
    household = get_household(request.user)
    prefs, _ = MealPlannerPreferences.objects.get_or_create(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action", "save_prefs")

        if action == "save_prefs":
            # existing preferences handling
            ...
        elif action == "update_household":
            name = request.POST.get("household_name", "").strip()
            if name and household:
                household.name = name
                household.save()
                messages.success(request, "Household name updated.")
        elif action == "regenerate_code":
            if household:
                household.code = generate_household_code()
                household.save()
                messages.success(request, "Household code regenerated.")

    members = household.members.select_related("user").all() if household else []

    return render(request, "settings/settings.html", {
        "form": form,
        "household": household,
        "members": members,
    })
```

- [ ] **Step 2: Update settings.html**

Add a Household section before the preferences form:

```html
<!-- Household -->
{% if household %}
<div style="padding: var(--space-lg); background: var(--bg-card); border-radius: var(--radius-md); margin-bottom: var(--space-xl);">
  <div class="section-header">
    <h2 class="section-title" style="margin-bottom: var(--space-md);">Household</h2>
  </div>

  <form method="post" action="{% url 'settings' %}">
    {% csrf_token %}
    <input type="hidden" name="action" value="update_household">
    <div class="flex gap-sm items-center mb-lg">
      <input type="text" name="household_name" value="{{ household.name }}" class="form-input" style="flex: 1;">
      <button type="submit" class="btn btn-primary btn-sm">Save</button>
    </div>
  </form>

  <div class="flex justify-between items-center mb-md" style="padding: var(--space-sm) 0; border-bottom: 1px solid var(--border);">
    <div>
      <span class="text-muted text-sm">Invite Code</span>
      <div style="font-size: var(--text-xl); font-weight: 800; letter-spacing: 0.15em; color: var(--accent);">{{ household.code }}</div>
    </div>
    <form method="post" action="{% url 'settings' %}">
      {% csrf_token %}
      <input type="hidden" name="action" value="regenerate_code">
      <button type="submit" class="btn btn-outline btn-sm">
        <i class="bi bi-arrow-repeat"></i> New Code
      </button>
    </form>
  </div>

  <div>
    <span class="text-muted text-sm">Members</span>
    {% for member in members %}
    <div class="flex justify-between items-center" style="padding: var(--space-sm) 0;">
      <span>{{ member.user.username }}</span>
      <span class="text-dim text-sm">Joined {{ member.joined_at|date:"M d, Y" }}</span>
    </div>
    {% endfor %}
  </div>
</div>
{% endif %}
```

- [ ] **Step 3: Run tests**

```bash
python manage.py test recipes -v0
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: household management in settings (name, code, members)"
```

---

## Task 9: Template Updates — Shared Recipe Label, Added-by, Share Toggle

**Files:**
- Modify: `recipes/templates/recipes/form.html` — share toggle
- Modify: `recipes/templates/recipes/partials/recipe_card.html` — shared-by label
- Modify: `recipes/templates/shop/shop.html` — added-by on items
- Modify: `recipes/templates/shop/partials/item.html` — added-by

- [ ] **Step 1: Add share toggle to recipe form**

In `recipes/templates/recipes/form.html`, add after the Tags section:

```html
<!-- Share with Household -->
<div class="form-group">
  <label class="form-label flex items-center gap-sm" style="cursor: pointer;">
    <input type="checkbox" name="shared" value="1"
           {% if recipe.shared %}checked{% endif %}
           style="width: 20px; height: 20px; accent-color: var(--primary);">
    Share with household
  </label>
  <span class="form-help">When enabled, household members can see this recipe and add it to the meal plan.</span>
</div>
```

Update `recipe_create_view` and `recipe_update_view` in `recipes/views/recipes.py` to handle the `shared` field:

```python
shared=request.POST.get("shared") == "1",
```

- [ ] **Step 2: Add shared-by label to recipe card**

In `recipes/templates/recipes/partials/recipe_card.html`, add after tags/metadata:

```html
{% if recipe.shared and recipe.user != request.user %}
<div class="text-dim" style="font-size: var(--text-xs); margin-top: var(--space-xs);">
  <i class="bi bi-people"></i> Shared by {{ recipe.user.username }}
</div>
{% endif %}
```

- [ ] **Step 3: Add added-by to shopping list items**

In `recipes/templates/shop/partials/item.html`, add the added_by user:

```html
{% if item.added_by %}
<span class="text-dim" style="font-size: 9px;">({{ item.added_by.username }})</span>
{% endif %}
```

In `recipes/templates/shop/shop.html`, update the manual items section to show who added each item.

- [ ] **Step 4: Run tests**

```bash
python manage.py test recipes -v0
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: recipe sharing toggle, shared-by labels, added-by on shopping items"
```

---

## Task 10: Update Existing Tests and Final Verification

**Files:**
- Modify: various test files that reference `MealPlan(user=...)` or `ShoppingListItem(user=...)`

- [ ] **Step 1: Fix existing tests**

Any test that creates a `MealPlan` or `ShoppingListItem` with `user=` needs updating to use `household=` and `added_by=`. This includes:
- `test_views_week.py`
- `test_views_shop.py`
- `test_views_cook.py` (if it creates meal plans)
- `test_models_new.py` (if it tests MealPlan)
- `test_services_new.py`
- `test_integration.py`

Create a household and membership in each test's `setUp` and use `household=self.household, added_by=self.user` instead of `user=self.user`.

- [ ] **Step 2: Run full test suite**

```bash
python manage.py test recipes -v0
```

Fix all failures until ALL tests pass.

- [ ] **Step 3: Format with Black and isort**

```bash
source venv/bin/activate
black recipes/ config/ --line-length 120
isort recipes/ config/ --profile black --line-length 120
flake8 recipes/ config/ --max-line-length=120
```

- [ ] **Step 4: Final verification**

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py test recipes -v0
```

All must pass.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "fix: update all tests for household-based meal plans and shopping lists"
```

---

## Summary

| Task | Component | Key Deliverable |
|------|-----------|-----------------|
| 1 | Models | Household, HouseholdMembership, DayComment |
| 2 | Model changes | Recipe.shared, MealPlan.household, ShoppingListItem.household |
| 3 | Data migration | Create households for existing users, migrate data |
| 4 | Schema cleanup | Remove old user FKs, make household required |
| 5 | Registration | Household code field on signup |
| 6 | Views | All views query by household instead of user |
| 7 | Day comments | Add/view planning notes on day cards |
| 8 | Settings | Household name, code, members management |
| 9 | Templates | Share toggle, shared-by label, added-by attribution |
| 10 | Tests | Fix all existing tests for household model |
