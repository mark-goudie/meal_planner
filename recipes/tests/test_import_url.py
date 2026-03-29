from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from recipes.models.household import Household, HouseholdMembership
from recipes.services.ai_service import AIAPIError, AIService, AIValidationError


class ImportRecipeFromURLServiceTest(TestCase):
    """Tests for AIService.import_recipe_from_url."""

    def test_empty_url_raises_validation_error(self):
        with self.assertRaises(AIValidationError):
            AIService.import_recipe_from_url("")

    def test_blank_url_raises_validation_error(self):
        with self.assertRaises(AIValidationError):
            AIService.import_recipe_from_url("   ")

    def test_invalid_url_raises_validation_error(self):
        with self.assertRaises(AIValidationError):
            AIService.import_recipe_from_url("not-a-url")

    @patch("recipes.services.ai_service.anthropic.Anthropic")
    @patch("recipes.services.ai_service.settings")
    def test_import_url_success(self, mock_settings, mock_anthropic_cls):
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = (
            '{"title": "Pasta", "description": "Simple pasta", "prep_time": 5, '
            '"cook_time": 10, "servings": 2, "difficulty": "easy", '
            '"ingredients": [{"name": "pasta", "quantity": 200, "unit": "g", '
            '"category": "pantry", "preparation_notes": ""}], '
            '"steps": ["Boil water", "Cook pasta"]}'
        )
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_anthropic_cls.return_value.messages.create.return_value = mock_response

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = (
                "<html><body><h1>Pasta Recipe</h1>"
                "<p>Boil pasta with sauce and cheese and serve with bread and butter on the side</p>"
                "</body></html>"
            )
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            result = AIService.import_recipe_from_url("https://example.com/recipe")
            self.assertEqual(result["title"], "Pasta")
            self.assertEqual(len(result["ingredients"]), 1)
            self.assertEqual(len(result["steps"]), 2)

    @patch("recipes.services.ai_service.anthropic.Anthropic")
    @patch("recipes.services.ai_service.settings")
    def test_import_url_no_recipe_found(self, mock_settings, mock_anthropic_cls):
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = '{"error": "No recipe found on this page."}'
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_anthropic_cls.return_value.messages.create.return_value = mock_response

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = (
                "<html><body><p>This is a blog post about travel with lots of text content here "
                "and more words to ensure it passes the minimum length check.</p></body></html>"
            )
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            with self.assertRaises(AIValidationError):
                AIService.import_recipe_from_url("https://example.com/blog")

    @patch("recipes.services.ai_service.settings")
    def test_import_url_fetch_failure(self, mock_settings):
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection error")

            with self.assertRaises(AIAPIError):
                AIService.import_recipe_from_url("https://example.com/recipe")

    @patch("recipes.services.ai_service.settings")
    def test_import_url_too_little_content(self, mock_settings):
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = "<html><body>Hi</body></html>"
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            with self.assertRaises(AIValidationError):
                AIService.import_recipe_from_url("https://example.com/recipe")


class ImportRecipeURLViewTest(TestCase):
    """Tests for the import_recipe_url view."""

    def setUp(self):
        self.user = User.objects.create_user("testuser", password="testpass123")
        self.household = Household.objects.create(name="Test")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_import_url_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse("import_recipe_url"), {"url": "https://example.com"})
        self.assertEqual(response.status_code, 302)

    def test_import_url_requires_post(self):
        response = self.client.get(reverse("import_recipe_url"))
        self.assertEqual(response.status_code, 405)

    def test_import_url_requires_url(self):
        response = self.client.post(reverse("import_recipe_url"), {"url": ""})
        self.assertEqual(response.status_code, 400)

    @patch("recipes.views.recipes.AIService.import_recipe_from_url")
    def test_import_url_success(self, mock_import):
        mock_import.return_value = {
            "title": "Pasta",
            "description": "Simple pasta",
            "prep_time": 5,
            "cook_time": 10,
            "servings": 2,
            "difficulty": "easy",
            "ingredients": [
                {"name": "pasta", "quantity": 200, "unit": "g", "category": "pantry", "preparation_notes": ""}
            ],
            "steps": ["Boil water", "Cook pasta"],
        }

        response = self.client.post(reverse("import_recipe_url"), {"url": "https://example.com/recipe"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "Pasta")
        self.assertEqual(len(data["ingredients"]), 1)
        self.assertEqual(len(data["steps"]), 2)

    @patch("recipes.views.recipes.AIService.import_recipe_from_url")
    def test_import_url_service_error(self, mock_import):
        from recipes.services.ai_service import AIServiceException

        mock_import.side_effect = AIServiceException("Couldn't access that URL.")
        response = self.client.post(reverse("import_recipe_url"), {"url": "https://example.com/bad"})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"], "Couldn't access that URL.")
