from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from recipes.models import Recipe
from recipes.models.household import Household, HouseholdMembership


class GeneratePreferencesTest(TestCase):
    """Tests for the recipe generator preference selection and progress views."""

    def setUp(self):
        self.user = User.objects.create_user("testuser", password="testpass123")
        self.household = Household.objects.create(name="Test")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_preferences_page_returns_200(self):
        response = self.client.get(reverse("generate_preferences"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Italian")
        self.assertContains(response, "Chicken")

    def test_preferences_post_stores_session_and_redirects(self):
        response = self.client.post(
            reverse("generate_preferences"),
            {
                "cuisines": ["Italian", "Asian"],
                "proteins": ["Chicken"],
                "count": "5",
            },
        )
        self.assertEqual(response.status_code, 302)
        session = self.client.session
        self.assertEqual(session["gen_cuisines"], ["Italian", "Asian"])
        self.assertEqual(session["gen_proteins"], ["Chicken"])
        self.assertEqual(session["gen_count"], 5)
        self.assertEqual(session["gen_completed"], 0)
        self.assertEqual(session["gen_titles"], [])

    def test_preferences_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("generate_preferences"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_count_capped_at_20(self):
        self.client.post(reverse("generate_preferences"), {"count": "50"})
        self.assertEqual(self.client.session["gen_count"], 20)

    def test_progress_redirects_without_session(self):
        response = self.client.get(reverse("generate_progress"))
        self.assertEqual(response.status_code, 302)

    @patch("recipes.views.generate.AIService.generate_structured_recipe")
    def test_generate_next_creates_recipe(self, mock_generate):
        mock_generate.return_value = {
            "title": "Test Recipe",
            "description": "A test",
            "prep_time": 10,
            "cook_time": 20,
            "servings": 4,
            "difficulty": "easy",
            "ingredients": [
                {
                    "name": "chicken",
                    "quantity": 500,
                    "unit": "g",
                    "category": "meat",
                    "preparation_notes": "",
                }
            ],
            "steps": ["Cook it"],
        }
        session = self.client.session
        session["gen_count"] = 2
        session["gen_completed"] = 0
        session["gen_titles"] = []
        session["gen_cuisines"] = ["Italian"]
        session["gen_proteins"] = []
        session["gen_dietary"] = []
        session["gen_styles"] = []
        session["gen_avoid"] = []
        session.save()

        response = self.client.get(reverse("generate_next"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Recipe.objects.filter(title="Test Recipe").exists())
        self.assertEqual(self.client.session["gen_completed"], 1)

        recipe = Recipe.objects.get(title="Test Recipe")
        self.assertEqual(recipe.source, "ai")
        self.assertTrue(recipe.is_ai_generated)
        self.assertEqual(recipe.user, self.user)
        self.assertEqual(recipe.recipe_ingredients.count(), 1)

    @patch("recipes.views.generate.AIService.generate_structured_recipe")
    def test_generate_next_returns_complete_when_done(self, mock_generate):
        session = self.client.session
        session["gen_count"] = 1
        session["gen_completed"] = 1
        session["gen_titles"] = ["Test"]
        session["gen_cuisines"] = []
        session["gen_proteins"] = []
        session["gen_dietary"] = []
        session["gen_styles"] = []
        session["gen_avoid"] = []
        session.save()

        response = self.client.get(reverse("generate_next"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "recipes added")
        # Session keys should be cleaned up
        self.assertNotIn("gen_count", self.client.session)

    @patch("recipes.views.generate.AIService.generate_structured_recipe")
    def test_generate_next_handles_ai_error(self, mock_generate):
        from recipes.services.ai_service import AIServiceException

        mock_generate.side_effect = AIServiceException("API error")
        recipe_count_before = Recipe.objects.filter(user=self.user).count()
        session = self.client.session
        session["gen_count"] = 2
        session["gen_completed"] = 0
        session["gen_titles"] = []
        session["gen_cuisines"] = []
        session["gen_proteins"] = []
        session["gen_dietary"] = []
        session["gen_styles"] = []
        session["gen_avoid"] = []
        session.save()

        response = self.client.get(reverse("generate_next"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Skipped")
        self.assertEqual(self.client.session["gen_completed"], 1)
        # No new recipe should have been created
        self.assertEqual(
            Recipe.objects.filter(user=self.user).count(), recipe_count_before
        )
