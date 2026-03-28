"""
Tests for updated service layer (Task 6).

Covers:
- RecipeService.generate_structured_shopping_list
- MealPlanningAssistantService.calculate_recipe_happiness_score
- MealPlanningAssistantService.get_recently_cooked_recipes
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from recipes.models import (
    CookingNote,
    Ingredient,
    Recipe,
    RecipeIngredient,
)
from recipes.services import RecipeService
from recipes.services.meal_planning_assistant import MealPlanningAssistantService


class GenerateStructuredShoppingListTests(TestCase):
    """Tests for RecipeService.generate_structured_shopping_list."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.eggs = Ingredient.objects.create(name="Eggs", category="dairy")
        self.flour = Ingredient.objects.create(name="Flour", category="pantry")
        self.butter = Ingredient.objects.create(name="Butter", category="dairy")

        self.recipe1 = Recipe.objects.create(
            user=self.user,
            title="Omelette",
            steps="Beat eggs, cook.",
        )
        self.recipe2 = Recipe.objects.create(
            user=self.user,
            title="Pancakes",
            steps="Mix and cook.",
        )

        # Both recipes use eggs (same unit) — quantities should sum
        RecipeIngredient.objects.create(
            recipe=self.recipe1,
            ingredient=self.eggs,
            quantity=Decimal("2"),
            unit="piece",
        )
        RecipeIngredient.objects.create(
            recipe=self.recipe2,
            ingredient=self.eggs,
            quantity=Decimal("3"),
            unit="piece",
        )
        # recipe2 also uses flour and butter
        RecipeIngredient.objects.create(
            recipe=self.recipe2,
            ingredient=self.flour,
            quantity=Decimal("1"),
            unit="cup",
        )
        RecipeIngredient.objects.create(
            recipe=self.recipe2,
            ingredient=self.butter,
            quantity=Decimal("2"),
            unit="tbsp",
        )

    def test_shared_ingredient_quantities_sum(self):
        """Two recipes sharing eggs (piece) produce a summed total of 5."""
        recipes = Recipe.objects.filter(id__in=[self.recipe1.id, self.recipe2.id])
        shopping_list = RecipeService.generate_structured_shopping_list(recipes)

        eggs_entry = next(e for e in shopping_list if e["ingredient"].name == "Eggs")
        self.assertEqual(eggs_entry["total_quantity"], Decimal("5"))

    def test_shared_ingredient_recipes_tracked(self):
        """Both recipe titles are present in the recipes set for the shared ingredient."""
        recipes = Recipe.objects.filter(id__in=[self.recipe1.id, self.recipe2.id])
        shopping_list = RecipeService.generate_structured_shopping_list(recipes)

        eggs_entry = next(e for e in shopping_list if e["ingredient"].name == "Eggs")
        self.assertIn("Omelette", eggs_entry["recipes"])
        self.assertIn("Pancakes", eggs_entry["recipes"])

    def test_items_grouped_by_category(self):
        """Items are sorted by category first, then ingredient name."""
        recipes = Recipe.objects.filter(id__in=[self.recipe1.id, self.recipe2.id])
        shopping_list = RecipeService.generate_structured_shopping_list(recipes)

        categories = [e["category"] for e in shopping_list]
        self.assertEqual(categories, sorted(categories), "Items should be sorted by category")

    def test_dairy_items_appear_before_pantry(self):
        """Dairy category ('dairy') sorts before 'pantry' alphabetically."""
        recipes = Recipe.objects.filter(id__in=[self.recipe1.id, self.recipe2.id])
        shopping_list = RecipeService.generate_structured_shopping_list(recipes)

        category_order = [e["category"] for e in shopping_list]
        # dairy < pantry alphabetically
        first_pantry = next((i for i, c in enumerate(category_order) if c == "pantry"), None)
        first_dairy = next((i for i, c in enumerate(category_order) if c == "dairy"), None)
        if first_dairy is not None and first_pantry is not None:
            self.assertLess(first_dairy, first_pantry)

    def test_different_units_are_separate_entries(self):
        """Same ingredient with different units produces separate list entries."""
        # Add eggs in 'g' (grams) unit to recipe1 alongside the existing 'piece' entry
        RecipeIngredient.objects.create(
            recipe=self.recipe1,
            ingredient=self.eggs,
            quantity=Decimal("50"),
            unit="g",
        )
        recipes = Recipe.objects.filter(id__in=[self.recipe1.id, self.recipe2.id])
        shopping_list = RecipeService.generate_structured_shopping_list(recipes)

        egg_entries = [e for e in shopping_list if e["ingredient"].name == "Eggs"]
        self.assertEqual(len(egg_entries), 2, "Different units should be separate entries")

    def test_empty_recipe_list_returns_empty(self):
        """An empty queryset produces an empty shopping list."""
        result = RecipeService.generate_structured_shopping_list(Recipe.objects.none())
        self.assertEqual(result, [])


class CalculateRecipeHappinessScoreTests(TestCase):
    """Tests for MealPlanningAssistantService.calculate_recipe_happiness_score."""

    def setUp(self):
        self.user = User.objects.create_user(username="scoreuser", password="password")
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Test Recipe",
            steps="Do stuff.",
        )

    def test_no_notes_returns_neutral_50(self):
        """A recipe with no cooking notes returns a score of 50."""
        score = MealPlanningAssistantService.calculate_recipe_happiness_score(self.recipe, self.user)
        self.assertEqual(score, Decimal("50.0"))

    def test_perfect_rating_returns_100(self):
        """All 5-star ratings with would_make_again=True returns 100."""
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date.today(),
            rating=5,
            would_make_again=True,
        )
        score = MealPlanningAssistantService.calculate_recipe_happiness_score(self.recipe, self.user)
        self.assertEqual(score, Decimal("100.0"))

    def test_average_rating_converted_correctly(self):
        """Rating of 3 (mid-scale) should produce a score of 50."""
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date.today(),
            rating=3,
            would_make_again=True,
        )
        score = MealPlanningAssistantService.calculate_recipe_happiness_score(self.recipe, self.user)
        self.assertEqual(score, Decimal("50.0"))

    def test_would_make_again_false_penalises_score(self):
        """Latest note with would_make_again=False deducts 20 from the score."""
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date.today(),
            rating=5,
            would_make_again=False,
        )
        score = MealPlanningAssistantService.calculate_recipe_happiness_score(self.recipe, self.user)
        # 5-star = 100, minus 20 penalty = 80
        self.assertEqual(score, Decimal("80.0"))

    def test_would_make_again_penalty_does_not_go_below_zero(self):
        """Penalty should not produce a negative score."""
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date.today(),
            rating=1,
            would_make_again=False,
        )
        score = MealPlanningAssistantService.calculate_recipe_happiness_score(self.recipe, self.user)
        self.assertGreaterEqual(score, Decimal("0"))

    def test_multiple_notes_average_is_used(self):
        """Score reflects the average of multiple notes."""
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date.today() - timedelta(days=2),
            rating=5,
            would_make_again=True,
        )
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date.today(),
            rating=3,
            would_make_again=True,
        )
        # Average = 4, score = ((4-1)/4)*100 = 75
        score = MealPlanningAssistantService.calculate_recipe_happiness_score(self.recipe, self.user)
        self.assertEqual(score, Decimal("75.0"))

    def test_notes_without_rating_excluded_from_average(self):
        """Notes with rating=None do not contribute to the average."""
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date.today(),
            rating=None,
            would_make_again=True,
        )
        score = MealPlanningAssistantService.calculate_recipe_happiness_score(self.recipe, self.user)
        # No rated notes — should return neutral 50
        self.assertEqual(score, Decimal("50.0"))


class GetRecentlyCookedRecipesTests(TestCase):
    """Tests for MealPlanningAssistantService.get_recently_cooked_recipes."""

    def setUp(self):
        self.user = User.objects.create_user(username="recentuser", password="password")
        self.other_user = User.objects.create_user(username="otheruser", password="password")
        self.recipe1 = Recipe.objects.create(
            user=self.user,
            title="Recent Recipe",
            steps="Steps.",
        )
        self.recipe2 = Recipe.objects.create(
            user=self.user,
            title="Old Recipe",
            steps="Steps.",
        )
        self.recipe3 = Recipe.objects.create(
            user=self.other_user,
            title="Other User Recipe",
            steps="Steps.",
        )

    def test_returns_recently_cooked_recipe_ids(self):
        """Returns recipe IDs cooked within the last 14 days."""
        CookingNote.objects.create(
            recipe=self.recipe1,
            user=self.user,
            cooked_date=date.today() - timedelta(days=7),
        )
        result = MealPlanningAssistantService.get_recently_cooked_recipes(self.user, days=14)
        self.assertIn(self.recipe1.id, result)

    def test_excludes_recipes_outside_date_range(self):
        """Recipes cooked more than N days ago are not returned."""
        CookingNote.objects.create(
            recipe=self.recipe2,
            user=self.user,
            cooked_date=date.today() - timedelta(days=20),
        )
        result = MealPlanningAssistantService.get_recently_cooked_recipes(self.user, days=14)
        self.assertNotIn(self.recipe2.id, result)

    def test_excludes_other_users_recipes(self):
        """Recipes cooked by other users are not returned."""
        CookingNote.objects.create(
            recipe=self.recipe3,
            user=self.other_user,
            cooked_date=date.today(),
        )
        result = MealPlanningAssistantService.get_recently_cooked_recipes(self.user, days=14)
        self.assertNotIn(self.recipe3.id, result)

    def test_returns_distinct_ids(self):
        """A recipe cooked multiple times within the window appears only once."""
        CookingNote.objects.create(
            recipe=self.recipe1,
            user=self.user,
            cooked_date=date.today() - timedelta(days=3),
        )
        CookingNote.objects.create(
            recipe=self.recipe1,
            user=self.user,
            cooked_date=date.today() - timedelta(days=7),
        )
        result = MealPlanningAssistantService.get_recently_cooked_recipes(self.user, days=14)
        self.assertEqual(result.count(self.recipe1.id), 1)

    def test_empty_when_no_cooking_notes(self):
        """Returns empty list when user has no cooking notes."""
        result = MealPlanningAssistantService.get_recently_cooked_recipes(self.user, days=14)
        self.assertEqual(result, [])

    def test_custom_days_parameter(self):
        """Custom days parameter respected — short window excludes older records."""
        CookingNote.objects.create(
            recipe=self.recipe1,
            user=self.user,
            cooked_date=date.today() - timedelta(days=5),
        )
        # Within 7 days — should be included
        result_7 = MealPlanningAssistantService.get_recently_cooked_recipes(self.user, days=7)
        self.assertIn(self.recipe1.id, result_7)

        # Outside 3 days — should be excluded
        result_3 = MealPlanningAssistantService.get_recently_cooked_recipes(self.user, days=3)
        self.assertNotIn(self.recipe1.id, result_3)
