from datetime import date

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
        self.user = User.objects.create_user(username="testuser", password="testpass123")
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
        item = ShoppingListItem.objects.create(household=self.household, added_by=self.user, name="Milk", checked=False)
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
        self.assertTrue(ShoppingListItem.objects.filter(household=self.household, name="Bananas").exists())

    def test_shop_add_empty_name_returns_empty(self):
        """Adding with empty name should return empty response."""
        response = self.client.post(
            reverse("shop_add"),
            data={"name": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ShoppingListItem.objects.filter(household=self.household).count(), 0)

    def test_shop_generate_clears_generated_items(self):
        """Regenerate should clear generated items but keep manual items."""
        ShoppingListItem.objects.create(
            household=self.household, added_by=self.user, name="Generated", is_generated=True
        )
        ShoppingListItem.objects.create(
            household=self.household, added_by=self.user, name="Manual Item", is_generated=False
        )
        response = self.client.post(reverse("shop_generate"))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ShoppingListItem.objects.filter(household=self.household, is_generated=True).exists())
        self.assertTrue(ShoppingListItem.objects.filter(household=self.household, name="Manual Item").exists())

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
        self.assertTrue(ShoppingListItem.objects.filter(household=self.household, is_generated=True).exists())

    def test_shop_toggle_other_user_returns_404(self):
        """Toggling another user's item should return 404."""
        other_user = User.objects.create_user(username="otheruser", password="testpass123")
        other_household = Household.objects.create(name="Other")
        HouseholdMembership.objects.create(user=other_user, household=other_household)
        item = ShoppingListItem.objects.create(household=other_household, added_by=other_user, name="Secret Item")
        response = self.client.post(reverse("shop_toggle", args=[item.pk]))
        self.assertEqual(response.status_code, 404)
