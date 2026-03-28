from unittest.mock import MagicMock, patch

from django.test import TestCase

from recipes.services.ai_service import AIService


class AIStructuredRecipeTest(TestCase):
    @patch("recipes.services.ai_service.anthropic")
    def test_parse_structured_recipe(self, mock_anthropic):
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = (
            '{"title": "Lemon Chicken", "description": "Simple lemon chicken", "prep_time": 10,'
            ' "cook_time": 30, "servings": 4, "difficulty": "easy",'
            ' "ingredients": [{"name": "chicken breast", "quantity": 500, "unit": "g",'
            ' "category": "meat", "preparation_notes": ""}],'
            ' "steps": ["Season chicken", "Bake at 200C"]}'
        )
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            from django.conf import settings

            original = getattr(settings, "ANTHROPIC_API_KEY", None)
            settings.ANTHROPIC_API_KEY = "test-key"
            try:
                result = AIService.generate_structured_recipe("chicken and lemon")
                self.assertEqual(result["title"], "Lemon Chicken")
                self.assertEqual(len(result["ingredients"]), 1)
                self.assertEqual(result["ingredients"][0]["name"], "chicken breast")
                self.assertEqual(len(result["steps"]), 2)
            finally:
                settings.ANTHROPIC_API_KEY = original

    @patch("recipes.services.ai_service.anthropic")
    def test_strips_markdown_fences(self, mock_anthropic):
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = '```json\n{"title": "Test", "ingredients": [], "steps": []}\n```'
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        from django.conf import settings

        original = getattr(settings, "ANTHROPIC_API_KEY", None)
        settings.ANTHROPIC_API_KEY = "test-key"
        try:
            result = AIService.generate_structured_recipe("test")
            self.assertEqual(result["title"], "Test")
        finally:
            settings.ANTHROPIC_API_KEY = original
