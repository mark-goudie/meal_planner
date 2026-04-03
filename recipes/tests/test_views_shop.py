from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from recipes.models import (
    Ingredient,
    MealPlan,
    Recipe,
    RecipeIngredient,
    ShoppingListItem,
)
from recipes.models.household import Household, HouseholdMembership


class ShopViewTest(TestCase):
    """Tests for the shopping list views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.household = Household.objects.create(name="Test")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Test Soup",
            steps="Make soup.",
            cook_time=30,
        )
        # Create a structured ingredient
        self.ingredient = Ingredient.objects.create(name="carrots", category="produce")
        RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient,
            quantity=3,
            unit="piece",
            order=0,
        )
        self.client.login(username="testuser", password="testpass123")

    def test_shop_view_returns_200(self):
        """Shop view should return 200 for authenticated users."""
        response = self.client.get(reverse("shop"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shop/shop.html")

    def test_shop_view_requires_login(self):
        """Shop view should redirect unauthenticated users."""
        self.client.logout()
        response = self.client.get(reverse("shop"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_shop_view_shows_generated_items(self):
        """Shop view should show ingredients from planned meals."""
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today(),
            meal_type="dinner",
            recipe=self.recipe,
        )
        response = self.client.get(reverse("shop"))
        self.assertContains(response, "carrots")

    def test_shop_view_empty_when_no_meals(self):
        """Shop view should show empty state when no meals are planned."""
        response = self.client.get(reverse("shop"))
        self.assertContains(response, "No meals planned")

    def test_shop_toggle_toggles_checked(self):
        """Toggle should switch checked state of a shopping item."""
        item = ShoppingListItem.objects.create(
            household=self.household, added_by=self.user, name="Milk", checked=False
        )
        response = self.client.post(reverse("shop_toggle", args=[item.pk]))
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertTrue(item.checked)

        # Toggle back
        response = self.client.post(reverse("shop_toggle", args=[item.pk]))
        item.refresh_from_db()
        self.assertFalse(item.checked)

    def test_shop_toggle_returns_item_partial(self):
        """Toggle should return the updated item partial."""
        item = ShoppingListItem.objects.create(
            household=self.household, added_by=self.user, name="Bread", checked=False
        )
        response = self.client.post(reverse("shop_toggle", args=[item.pk]))
        self.assertTemplateUsed(response, "shop/partials/item.html")
        self.assertContains(response, "Bread")

    def test_shop_add_creates_manual_item(self):
        """Adding a manual item should create a ShoppingListItem."""
        response = self.client.post(
            reverse("shop_add"),
            data={"name": "Bananas"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            ShoppingListItem.objects.filter(
                household=self.household, name="Bananas"
            ).exists()
        )

    def test_shop_add_empty_name_returns_empty(self):
        """Adding with empty name should return empty response."""
        response = self.client.post(
            reverse("shop_add"),
            data={"name": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ShoppingListItem.objects.filter(household=self.household).count(), 0
        )

    def test_shop_generate_clears_generated_items(self):
        """Regenerate should clear generated items but keep manual items."""
        ShoppingListItem.objects.create(
            household=self.household,
            added_by=self.user,
            name="Generated",
            is_generated=True,
        )
        ShoppingListItem.objects.create(
            household=self.household,
            added_by=self.user,
            name="Manual Item",
            is_generated=False,
        )
        response = self.client.post(reverse("shop_generate"))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            ShoppingListItem.objects.filter(
                household=self.household, is_generated=True
            ).exists()
        )
        self.assertTrue(
            ShoppingListItem.objects.filter(
                household=self.household, name="Manual Item"
            ).exists()
        )

    def test_shop_generate_with_selected_meals(self):
        """Regenerate with selected meals should only include those meals."""
        meal = MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today(),
            meal_type="dinner",
            recipe=self.recipe,
        )
        response = self.client.post(reverse("shop_generate"), {"meals": [meal.pk]})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ShoppingListItem.objects.filter(
                household=self.household, is_generated=True
            ).exists()
        )

    def test_shop_toggle_other_user_returns_404(self):
        """Toggling another user's item should return 404."""
        other_user = User.objects.create_user(
            username="otheruser", password="testpass123"
        )
        other_household = Household.objects.create(name="Other")
        HouseholdMembership.objects.create(user=other_user, household=other_household)
        item = ShoppingListItem.objects.create(
            household=other_household, added_by=other_user, name="Secret Item"
        )
        response = self.client.post(reverse("shop_toggle", args=[item.pk]))
        self.assertEqual(response.status_code, 404)

    def test_shop_regenerates_when_meals_added_after_initial_generation(self):
        """Shopping list should include new meals added after initial generation."""
        # First visit: one meal exists, auto-generates
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today(),
            meal_type="dinner",
            recipe=self.recipe,
        )
        response = self.client.get(reverse("shop"))
        self.assertContains(response, "carrots")

        # Add a second meal with a different recipe
        recipe2 = Recipe.objects.create(
            user=self.user, title="Pasta", steps="Boil.", cook_time=20
        )
        onion = Ingredient.objects.create(name="onion", category="produce")
        RecipeIngredient.objects.create(
            recipe=recipe2, ingredient=onion, quantity=2, unit="piece", order=0
        )
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today() + timedelta(days=1),
            meal_type="dinner",
            recipe=recipe2,
        )

        # Second visit: should now include BOTH meals' ingredients
        response = self.client.get(reverse("shop"))
        self.assertContains(response, "carrots")
        self.assertContains(response, "onion")

    def test_shop_includes_text_only_ingredients(self):
        """Recipes with only ingredients_text (no structured ingredients) should appear."""
        text_recipe = Recipe.objects.create(
            user=self.user,
            title="Simple Salad",
            steps="Mix it.",
            cook_time=10,
            ingredients_text="2 tomatoes\n1 cucumber\n100g feta cheese",
        )
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today(),
            meal_type="dinner",
            recipe=text_recipe,
        )
        response = self.client.get(reverse("shop"))
        self.assertContains(response, "tomatoes")
        self.assertContains(response, "cucumber")
        self.assertContains(response, "feta cheese")

    def test_shop_meal_count_matches_upcoming_meals(self):
        """The meal_count context should reflect actual upcoming meals."""
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today(),
            meal_type="dinner",
            recipe=self.recipe,
        )
        recipe2 = Recipe.objects.create(
            user=self.user, title="Pasta", steps="Boil.", cook_time=20
        )
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today() + timedelta(days=1),
            meal_type="dinner",
            recipe=recipe2,
        )
        response = self.client.get(reverse("shop"))
        self.assertEqual(response.context["meal_count"], 2)

    def test_shop_generate_updates_list_to_match_selection(self):
        """Posting shop_generate with specific meals should show only those ingredients."""
        recipe2 = Recipe.objects.create(
            user=self.user, title="Pasta", steps="Boil.", cook_time=20
        )
        garlic = Ingredient.objects.create(name="garlic", category="produce")
        RecipeIngredient.objects.create(
            recipe=recipe2, ingredient=garlic, quantity=3, unit="clove", order=0
        )
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today(),
            meal_type="dinner",
            recipe=self.recipe,
        )
        meal2 = MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today() + timedelta(days=1),
            meal_type="dinner",
            recipe=recipe2,
        )

        # Generate for only meal2
        self.client.post(reverse("shop_generate"), {"meals": [meal2.pk]})

        # Should have garlic but not carrots
        self.assertTrue(
            ShoppingListItem.objects.filter(
                household=self.household, name="garlic", is_generated=True
            ).exists()
        )
        self.assertFalse(
            ShoppingListItem.objects.filter(
                household=self.household, name="carrots", is_generated=True
            ).exists()
        )

    def test_shop_includes_all_ingredients_when_structured_is_partial(self):
        """If a recipe has some structured ingredients but more in text, include both."""
        recipe = Recipe.objects.create(
            user=self.user,
            title="Yakitori Bowl",
            steps="Make it.",
            cook_time=30,
            ingredients_text="500g chicken breast\n2 tbsp soy sauce\n1 tbsp sugar\n1 tbsp mirin\nsteamed rice",
        )
        # Only 2 of 5 ingredients are structured
        chicken = Ingredient.objects.create(name="chicken breast", category="meat")
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=chicken, quantity=500, unit="g", order=0
        )
        sugar = Ingredient.objects.create(name="sugar", category="pantry")
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=sugar, quantity=1, unit="tbsp", order=1
        )
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today(),
            meal_type="dinner",
            recipe=recipe,
        )
        response = self.client.get(reverse("shop"))
        # Structured ingredients should appear
        self.assertContains(response, "chicken breast")
        self.assertContains(response, "sugar")
        # Text-only ingredients should also appear
        self.assertContains(response, "soy sauce")
        self.assertContains(response, "mirin")
        self.assertContains(response, "steamed rice")

    def test_shop_toggle_updates_progress_counter(self):
        """Toggling an item should return updated progress info."""
        item = ShoppingListItem.objects.create(
            household=self.household,
            added_by=self.user,
            name="Milk",
            is_generated=True,
            checked=False,
        )
        ShoppingListItem.objects.create(
            household=self.household,
            added_by=self.user,
            name="Bread",
            is_generated=True,
            checked=False,
        )
        response = self.client.post(reverse("shop_toggle", args=[item.pk]))
        self.assertEqual(response.status_code, 200)
        # Should contain the progress partial with updated count
        self.assertContains(response, "1 of 2 items")

    def test_shop_weekend_meals_included(self):
        """Meals on Saturday and Sunday of current week should appear in shopping list."""
        today = date.today()
        # Find next Saturday from today
        days_to_sat = (5 - today.weekday()) % 7
        if days_to_sat == 0 and today.weekday() != 5:
            days_to_sat = 7
        saturday = today + timedelta(days=days_to_sat)
        sunday = saturday + timedelta(days=1)

        recipe_sat = Recipe.objects.create(
            user=self.user, title="Saturday Roast", steps="Roast it.", cook_time=60
        )
        lamb = Ingredient.objects.create(name="lamb", category="meat")
        RecipeIngredient.objects.create(
            recipe=recipe_sat, ingredient=lamb, quantity=1, unit="kg", order=0
        )
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=saturday,
            meal_type="dinner",
            recipe=recipe_sat,
        )

        recipe_sun = Recipe.objects.create(
            user=self.user, title="Sunday Stew", steps="Stew it.", cook_time=90
        )
        beef = Ingredient.objects.create(name="beef", category="meat")
        RecipeIngredient.objects.create(
            recipe=recipe_sun, ingredient=beef, quantity=500, unit="g", order=0
        )
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=sunday,
            meal_type="dinner",
            recipe=recipe_sun,
        )

        response = self.client.get(reverse("shop"))
        self.assertContains(response, "lamb")
        self.assertContains(response, "beef")
