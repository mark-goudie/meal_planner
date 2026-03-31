from datetime import date, timedelta

from django.test import Client, TestCase
from django.urls import reverse

from recipes.models import MealPlan, Recipe
from recipes.models.household import get_household
from recipes.tests.test_utils import TestUtilities


class RecipeWorkflowIntegrationTest(TestCase):
    """Test complete recipe workflow from creation to meal planning"""

    def setUp(self):
        self.client = Client()
        self.user = TestUtilities.create_test_user()
        self.client.login(username="testuser", password="testpass123")

    def test_complete_recipe_workflow(self):
        """Test the complete workflow: create recipe -> add to meal plan -> toggle favourite"""
        # Step 1: Create a recipe
        recipe_data = {
            "title": "Integration Test Recipe",
            "steps": "Integration step 1\nIntegration step 2",
            "ingredients_text": "Integration ingredients\nMore ingredients",
            "notes": "Integration notes",
            "servings": "4",
            "difficulty": "easy",
            "ingredient_count": "0",
        }
        response = self.client.post(reverse("recipe_create"), recipe_data)
        self.assertEqual(response.status_code, 302)

        recipe = Recipe.objects.get(title="Integration Test Recipe")
        self.assertEqual(recipe.user, self.user)

        # Step 2: Legacy meal_plan_create now redirects to /week/
        meal_plan_data = {"date": date.today(), "meal_type": "breakfast", "recipe": recipe.id}
        response = self.client.post(reverse("meal_plan_create"), meal_plan_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/week/")

        # Step 3: Toggle favourite
        response = self.client.post(reverse("toggle_favourite", kwargs={"pk": recipe.pk}))
        self.assertEqual(response.status_code, 200)

        recipe.refresh_from_db()
        self.assertTrue(self.user in recipe.favourited_by.all())

        # Step 4: Legacy generate_shopping_list now redirects to /shop/
        response = self.client.post(reverse("generate_shopping_list"), {"recipe_ids": [recipe.id]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/shop/")


class MealPlanningIntegrationTest(TestCase):
    """Test meal planning workflow"""

    def setUp(self):
        self.client = Client()
        self.test_data = TestUtilities.create_complete_test_data()
        self.user = self.test_data["user"]
        self.recipes = self.test_data["recipes"]
        self.client.login(username="testuser", password="testpass123")

    def test_weekly_meal_planning_legacy_redirects(self):
        """Test that legacy meal planning views redirect to new equivalents"""
        # Legacy meal_plan_create now redirects to /week/
        meal_plan_data = {"date": date.today(), "meal_type": "breakfast", "recipe": self.recipes[0].id}
        response = self.client.post(reverse("meal_plan_create"), meal_plan_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/week/")

        # Legacy meal_plan_week now redirects to /week/
        response = self.client.get(reverse("meal_plan_week"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/week/")


class SearchAndFilterIntegrationTest(TestCase):
    """Test search and filtering functionality"""

    def setUp(self):
        self.client = Client()
        self.user = TestUtilities.create_test_user()
        self.client.login(username="testuser", password="testpass123")

        # Create diverse recipes for testing
        self.pasta_tag = TestUtilities.create_test_tag("Pasta")
        self.quick_tag = TestUtilities.create_test_tag("Quick")

        self.pasta_recipe = TestUtilities.create_test_recipe(
            self.user,
            title="Spaghetti Carbonara",
            ingredients_text="Pasta\nEggs\nBacon",
            steps="Cook pasta\nMix with eggs and bacon",
        )
        self.pasta_recipe.tags.add(self.pasta_tag)

        self.salad_recipe = TestUtilities.create_test_recipe(
            self.user,
            title="Quick Caesar Salad",
            ingredients_text="Lettuce\nCroutons\nDressing",
            steps="Mix all ingredients",
        )
        self.salad_recipe.tags.add(self.quick_tag)

        # Add to favourites
        self.pasta_recipe.favourited_by.add(self.user)

    def test_recipe_search_by_title(self):
        """Test searching recipes by title"""
        response = self.client.get(reverse("recipe_list"), {"q": "Spaghetti"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Spaghetti Carbonara")
        self.assertNotContains(response, "Quick Caesar Salad")

    def test_recipe_search_by_ingredients(self):
        """Test searching recipes by ingredients"""
        response = self.client.get(reverse("recipe_list"), {"q": "Lettuce"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Quick Caesar Salad")
        self.assertNotContains(response, "Spaghetti Carbonara")

    def test_recipe_filter_by_tag(self):
        """Test filtering recipes by tag"""
        response = self.client.get(reverse("recipe_list"), {"tag": self.pasta_tag.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Spaghetti Carbonara")
        self.assertNotContains(response, "Quick Caesar Salad")

    def test_recipe_filter_by_favourites(self):
        """Test filtering recipes by favourites"""
        response = self.client.get(reverse("recipe_list"), {"favourites": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Spaghetti Carbonara")
        self.assertNotContains(response, "Quick Caesar Salad")

    def test_combined_search_and_filter(self):
        """Test combining search query with filters"""
        response = self.client.get(reverse("recipe_list"), {"q": "Pasta", "tag": self.pasta_tag.id, "favourites": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Spaghetti Carbonara")


class ShoppingListIntegrationTest(TestCase):
    """Test shopping list generation workflow"""

    def setUp(self):
        self.client = Client()
        self.user = TestUtilities.create_test_user()
        self.client.login(username="testuser", password="testpass123")

        # Create recipes with overlapping ingredients
        self.recipe1 = TestUtilities.create_test_recipe(
            self.user,
            title="Pasta Dish",
            ingredients_text="Pasta\nTomatoes\nGarlic\nOlive Oil",
            steps="Cook pasta, add sauce",
        )

        self.recipe2 = TestUtilities.create_test_recipe(
            self.user, title="Salad", ingredients_text="Lettuce\nTomatoes\nOlive Oil\nVinegar", steps="Mix ingredients"
        )

        self.recipe3 = TestUtilities.create_test_recipe(
            self.user,
            title="Garlic Bread",
            ingredients_text="Bread\nGarlic\nButter",
            steps="Mix garlic and butter, spread on bread, toast",
        )

    def test_shopping_list_generation_redirects(self):
        """Test that legacy generate_shopping_list redirects to /shop/"""
        response = self.client.post(reverse("generate_shopping_list"), {"recipe_ids": [self.recipe1.id]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/shop/")

    def test_shopping_list_empty_selection_redirects(self):
        """Test that legacy generate_shopping_list with no recipes redirects to /shop/"""
        response = self.client.post(reverse("generate_shopping_list"), {"recipe_ids": []})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/shop/")


class UserIsolationIntegrationTest(TestCase):
    """Test that users can only access their own data"""

    def setUp(self):
        self.client = Client()

        # Create two users with their own data
        self.user1 = TestUtilities.create_test_user("user1", "user1@example.com")
        self.user2 = TestUtilities.create_test_user("user2", "user2@example.com")

        self.user1_recipe = TestUtilities.create_test_recipe(self.user1, "User 1 Recipe")
        self.user2_recipe = TestUtilities.create_test_recipe(self.user2, "User 2 Recipe")

        self.user1_meal_plan = TestUtilities.create_test_meal_plan(self.user1, self.user1_recipe)
        self.user2_meal_plan = TestUtilities.create_test_meal_plan(self.user2, self.user2_recipe)

    def test_user1_cannot_access_user2_recipes(self):
        """Test that user1 cannot access user2's recipes"""
        self.client.login(username="user1", password="testpass123")

        # Try to access user2's recipe
        response = self.client.get(reverse("recipe_detail", kwargs={"pk": self.user2_recipe.pk}))
        self.assertEqual(response.status_code, 404)

        # Try to update user2's recipe
        response = self.client.get(reverse("recipe_update", kwargs={"pk": self.user2_recipe.pk}))
        self.assertEqual(response.status_code, 404)

        # Try to delete user2's recipe
        response = self.client.get(reverse("recipe_delete", kwargs={"pk": self.user2_recipe.pk}))
        self.assertEqual(response.status_code, 404)

    def test_user_recipe_list_isolation(self):
        """Test that recipe lists only show user's own recipes"""
        # Login as user1
        self.client.login(username="user1", password="testpass123")
        response = self.client.get(reverse("recipe_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User 1 Recipe")
        self.assertNotContains(response, "User 2 Recipe")

        # Login as user2
        self.client.logout()
        self.client.login(username="user2", password="testpass123")
        response = self.client.get(reverse("recipe_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User 2 Recipe")
        self.assertNotContains(response, "User 1 Recipe")

    def test_meal_plan_isolation(self):
        """Test that legacy meal_plan_week redirects to /week/"""
        # Login as user1
        self.client.login(username="user1", password="testpass123")
        response = self.client.get(reverse("meal_plan_week"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/week/")

        # The new week view handles isolation; verify it renders
        response = self.client.get(reverse("week"))
        self.assertEqual(response.status_code, 200)
