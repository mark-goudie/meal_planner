from django.test import TestCase
from unittest.mock import patch, MagicMock
from recipes.services.ai_service import AIService


class AIStructuredRecipeTest(TestCase):
    @patch('recipes.services.ai_service.openai')
    def test_parse_structured_recipe(self, mock_openai):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"title": "Lemon Chicken", "description": "Simple lemon chicken", "prep_time": 10, "cook_time": 30, "servings": 4, "difficulty": "easy", "ingredients": [{"name": "chicken breast", "quantity": 500, "unit": "g", "category": "meat", "preparation_notes": ""}], "steps": ["Season chicken", "Bake at 200C"]}'
        mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            from django.conf import settings
            original = getattr(settings, 'OPENAI_API_KEY', None)
            settings.OPENAI_API_KEY = 'test-key'
            try:
                result = AIService.generate_structured_recipe("chicken and lemon")
                self.assertEqual(result['title'], "Lemon Chicken")
                self.assertEqual(len(result['ingredients']), 1)
                self.assertEqual(result['ingredients'][0]['name'], 'chicken breast')
                self.assertEqual(len(result['steps']), 2)
            finally:
                settings.OPENAI_API_KEY = original

    @patch('recipes.services.ai_service.openai')
    def test_strips_markdown_fences(self, mock_openai):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '```json\n{"title": "Test", "ingredients": [], "steps": []}\n```'
        mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response

        from django.conf import settings
        original = getattr(settings, 'OPENAI_API_KEY', None)
        settings.OPENAI_API_KEY = 'test-key'
        try:
            result = AIService.generate_structured_recipe("test")
            self.assertEqual(result['title'], "Test")
        finally:
            settings.OPENAI_API_KEY = original
