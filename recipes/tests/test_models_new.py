"""
Tests for the new and updated models introduced in the redesign.

Covers:
- Ingredient creation and uniqueness
- RecipeIngredient creation with/without quantity
- CookingNote creation and Recipe.average_rating property
- ShoppingListItem creation and toggle
- Tag with tag_type
- Recipe with source field
- MealPlan with notes field
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase

from recipes.models import (
    CookingNote,
    Ingredient,
    MealPlan,
    Recipe,
    RecipeIngredient,
    ShoppingListItem,
    Tag,
    MEAL_CHOICES,
)


class IngredientModelTests(TestCase):
    """Tests for the Ingredient model."""

    def test_create_ingredient(self):
        ingredient = Ingredient.objects.create(name="Garlic", category="produce")
        self.assertEqual(ingredient.name, "Garlic")
        self.assertEqual(ingredient.category, "produce")

    def test_ingredient_default_category(self):
        ingredient = Ingredient.objects.create(name="Mystery Item")
        self.assertEqual(ingredient.category, "other")

    def test_ingredient_uniqueness(self):
        Ingredient.objects.create(name="Salt")
        with self.assertRaises(IntegrityError):
            Ingredient.objects.create(name="Salt")

    def test_ingredient_ordering(self):
        Ingredient.objects.create(name="Zucchini")
        Ingredient.objects.create(name="Apple")
        Ingredient.objects.create(name="Milk")
        names = list(Ingredient.objects.values_list("name", flat=True))
        self.assertEqual(names, ["Apple", "Milk", "Zucchini"])

    def test_ingredient_str(self):
        ingredient = Ingredient.objects.create(name="Basil", category="produce")
        self.assertEqual(str(ingredient), "Basil")


class RecipeIngredientModelTests(TestCase):
    """Tests for the RecipeIngredient model."""

    def setUp(self):
        self.user = User.objects.create_user("chef", password="pass1234")
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Test Recipe",
            steps="Step 1",
        )
        self.ingredient = Ingredient.objects.create(name="Flour", category="pantry")

    def test_create_with_quantity(self):
        ri = RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient,
            quantity=Decimal("2.50"),
            unit="cup",
            preparation_notes="sifted",
            order=1,
        )
        self.assertEqual(ri.quantity, Decimal("2.50"))
        self.assertEqual(ri.unit, "cup")
        self.assertEqual(ri.preparation_notes, "sifted")
        self.assertIn("Flour", str(ri))
        self.assertIn("2.50", str(ri))
        self.assertIn("cup", str(ri))
        self.assertIn("sifted", str(ri))

    def test_create_without_quantity(self):
        ri = RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient,
            order=1,
        )
        self.assertIsNone(ri.quantity)
        self.assertEqual(ri.unit, "")
        self.assertEqual(str(ri), "Flour")

    def test_ordering(self):
        salt = Ingredient.objects.create(name="Salt", category="spices")
        RecipeIngredient.objects.create(
            recipe=self.recipe, ingredient=salt, order=2
        )
        RecipeIngredient.objects.create(
            recipe=self.recipe, ingredient=self.ingredient, order=1
        )
        ris = list(self.recipe.recipe_ingredients.all())
        self.assertEqual(ris[0].ingredient.name, "Flour")
        self.assertEqual(ris[1].ingredient.name, "Salt")


class CookingNoteModelTests(TestCase):
    """Tests for the CookingNote model and Recipe.average_rating."""

    def setUp(self):
        self.user = User.objects.create_user("cook", password="pass1234")
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Pasta",
            steps="Boil and serve",
        )

    def test_create_cooking_note(self):
        note = CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date(2026, 3, 15),
            rating=4,
            note="Used extra cheese",
            would_make_again=True,
        )
        self.assertEqual(note.rating, 4)
        self.assertEqual(note.note, "Used extra cheese")
        self.assertTrue(note.would_make_again)

    def test_average_rating_single(self):
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date(2026, 3, 1),
            rating=5,
        )
        self.assertEqual(self.recipe.average_rating, 5.0)

    def test_average_rating_multiple(self):
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date(2026, 3, 1),
            rating=4,
        )
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date(2026, 3, 2),
            rating=2,
        )
        self.assertAlmostEqual(self.recipe.average_rating, 3.0)

    def test_average_rating_none_when_no_notes(self):
        self.assertIsNone(self.recipe.average_rating)

    def test_average_rating_excludes_unrated(self):
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date(2026, 3, 1),
            rating=None,
            note="No rating this time",
        )
        self.assertIsNone(self.recipe.average_rating)

    def test_cook_count(self):
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date(2026, 3, 1),
            rating=4,
        )
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date(2026, 3, 10),
        )
        self.assertEqual(self.recipe.cook_count, 2)

    def test_latest_note(self):
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date(2026, 3, 1),
            note="First time",
        )
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date(2026, 3, 20),
            note="Second time",
        )
        latest = self.recipe.latest_note
        self.assertEqual(latest.note, "Second time")

    def test_ordering_by_cooked_date_desc(self):
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date(2026, 1, 1),
        )
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date(2026, 3, 1),
        )
        notes = list(CookingNote.objects.all())
        self.assertGreater(notes[0].cooked_date, notes[1].cooked_date)


class ShoppingListItemModelTests(TestCase):
    """Tests for the ShoppingListItem model."""

    def setUp(self):
        self.user = User.objects.create_user("shopper", password="pass1234")

    def test_create_item(self):
        item = ShoppingListItem.objects.create(
            user=self.user, name="Milk"
        )
        self.assertEqual(item.name, "Milk")
        self.assertFalse(item.checked)

    def test_toggle_checked(self):
        item = ShoppingListItem.objects.create(
            user=self.user, name="Eggs"
        )
        self.assertFalse(item.checked)

        item.checked = True
        item.save()
        item.refresh_from_db()
        self.assertTrue(item.checked)

    def test_ordering_checked_last(self):
        ShoppingListItem.objects.create(user=self.user, name="Bread")
        checked_item = ShoppingListItem.objects.create(
            user=self.user, name="Butter", checked=True
        )
        ShoppingListItem.objects.create(user=self.user, name="Cheese")

        items = list(ShoppingListItem.objects.filter(user=self.user))
        # Checked items should come last (ordering by checked, created_at)
        self.assertEqual(items[-1].name, "Butter")
        self.assertTrue(items[-1].checked)

    def test_str(self):
        item = ShoppingListItem.objects.create(user=self.user, name="Apple")
        self.assertIn("Apple", str(item))

        item.checked = True
        item.save()
        self.assertIn("x", str(item))


class TagModelTests(TestCase):
    """Tests for the Tag model with tag_type."""

    def test_create_tag_with_default_type(self):
        tag = Tag.objects.create(name="Italian")
        self.assertEqual(tag.tag_type, "cuisine")

    def test_create_tag_with_dietary_type(self):
        tag = Tag.objects.create(name="Keto", tag_type="dietary")
        self.assertEqual(tag.tag_type, "dietary")

    def test_create_tag_with_method_type(self):
        tag = Tag.objects.create(name="Grilled", tag_type="method")
        self.assertEqual(tag.tag_type, "method")

    def test_create_tag_with_time_type(self):
        tag = Tag.objects.create(name="30-min", tag_type="time")
        self.assertEqual(tag.tag_type, "time")

    def test_tag_str(self):
        tag = Tag.objects.create(name="Mexican")
        self.assertEqual(str(tag), "Mexican")


class RecipeSourceFieldTests(TestCase):
    """Tests for the Recipe source field."""

    def setUp(self):
        self.user = User.objects.create_user("author", password="pass1234")

    def test_default_source(self):
        recipe = Recipe.objects.create(
            user=self.user,
            title="Manual Recipe",
            steps="Do the thing",
        )
        self.assertEqual(recipe.source, "manual")

    def test_ai_source(self):
        recipe = Recipe.objects.create(
            user=self.user,
            title="AI Recipe",
            steps="AI step",
            source="ai",
        )
        self.assertEqual(recipe.source, "ai")

    def test_url_source(self):
        recipe = Recipe.objects.create(
            user=self.user,
            title="Web Recipe",
            steps="Steps",
            source="url",
        )
        self.assertEqual(recipe.source, "url")

    def test_family_source(self):
        recipe = Recipe.objects.create(
            user=self.user,
            title="Grandma's Cookies",
            steps="Steps",
            source="family",
        )
        self.assertEqual(recipe.source, "family")

    def test_ingredients_text_field(self):
        recipe = Recipe.objects.create(
            user=self.user,
            title="Test",
            steps="Steps",
            ingredients_text="Flour\nSugar\nButter",
        )
        self.assertEqual(recipe.ingredients_text, "Flour\nSugar\nButter")

    def test_ingredients_text_blank_allowed(self):
        recipe = Recipe.objects.create(
            user=self.user,
            title="No ingredients text",
            steps="Steps",
        )
        self.assertEqual(recipe.ingredients_text, "")

    def test_cooking_mode_steps_json(self):
        steps_data = [
            {"step": 1, "text": "Preheat oven", "timer": 300},
            {"step": 2, "text": "Mix ingredients"},
        ]
        recipe = Recipe.objects.create(
            user=self.user,
            title="JSON Steps",
            steps="Steps",
            cooking_mode_steps=steps_data,
        )
        recipe.refresh_from_db()
        self.assertEqual(recipe.cooking_mode_steps, steps_data)

    def test_default_servings_is_four(self):
        recipe = Recipe.objects.create(
            user=self.user,
            title="Serves Four",
            steps="Steps",
        )
        self.assertEqual(recipe.servings, 4)

    def test_total_time_property(self):
        recipe = Recipe.objects.create(
            user=self.user,
            title="Timed",
            steps="Steps",
            prep_time=10,
            cook_time=20,
        )
        self.assertEqual(recipe.total_time, 30)

    def test_total_time_none_when_no_times(self):
        recipe = Recipe.objects.create(
            user=self.user,
            title="No times",
            steps="Steps",
        )
        self.assertIsNone(recipe.total_time)


class MealPlanNotesFieldTests(TestCase):
    """Tests for the MealPlan notes field."""

    def setUp(self):
        self.user = User.objects.create_user("planner", password="pass1234")
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Dinner",
            steps="Cook it",
        )

    def test_meal_plan_with_notes(self):
        plan = MealPlan.objects.create(
            user=self.user,
            date=date(2026, 3, 28),
            meal_type="dinner",
            recipe=self.recipe,
            notes="Use leftovers from yesterday",
        )
        self.assertEqual(plan.notes, "Use leftovers from yesterday")

    def test_meal_plan_notes_default_blank(self):
        plan = MealPlan.objects.create(
            user=self.user,
            date=date(2026, 3, 28),
            meal_type="dinner",
            recipe=self.recipe,
        )
        self.assertEqual(plan.notes, "")

    def test_meal_choices_available(self):
        self.assertEqual(len(MEAL_CHOICES), 3)
        choices_dict = dict(MEAL_CHOICES)
        self.assertIn("breakfast", choices_dict)
        self.assertIn("lunch", choices_dict)
        self.assertIn("dinner", choices_dict)
