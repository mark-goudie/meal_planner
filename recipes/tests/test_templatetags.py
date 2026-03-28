from datetime import date
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase

from recipes.models import MealPlan, Recipe
from recipes.models.household import Household, HouseholdMembership
from recipes.templatetags.recipe_extras import ai_generate_surprise_recipe, get, get_meal


class RecipeExtrasTemplateTagsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.household = Household.objects.create(name="Test")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.recipe1 = Recipe.objects.create(
            user=self.user, title="Breakfast Recipe", ingredients_text="Breakfast ingredients", steps="Breakfast steps"
        )
        self.recipe2 = Recipe.objects.create(
            user=self.user, title="Lunch Recipe", ingredients_text="Lunch ingredients", steps="Lunch steps"
        )
        self.meal_plan1 = MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today(),
            meal_type="breakfast",
            recipe=self.recipe1,
        )
        self.meal_plan2 = MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today(),
            meal_type="lunch",
            recipe=self.recipe2,
        )

    def test_get_meal_filter_finds_breakfast(self):
        """Test get_meal filter returns correct breakfast meal plan"""
        plans = [self.meal_plan1, self.meal_plan2]
        result = get_meal(plans, "breakfast")
        self.assertEqual(result, self.meal_plan1)
        self.assertEqual(result.recipe, self.recipe1)

    def test_get_meal_filter_finds_lunch(self):
        """Test get_meal filter returns correct lunch meal plan"""
        plans = [self.meal_plan1, self.meal_plan2]
        result = get_meal(plans, "lunch")
        self.assertEqual(result, self.meal_plan2)
        self.assertEqual(result.recipe, self.recipe2)

    def test_get_meal_filter_finds_dinner(self):
        """Test get_meal filter returns None for missing dinner"""
        plans = [self.meal_plan1, self.meal_plan2]
        result = get_meal(plans, "dinner")
        self.assertIsNone(result)

    def test_get_meal_filter_empty_list(self):
        """Test get_meal filter with empty list"""
        plans = []
        result = get_meal(plans, "breakfast")
        self.assertIsNone(result)

    def test_get_meal_filter_invalid_meal_type(self):
        """Test get_meal filter with invalid meal type"""
        plans = [self.meal_plan1, self.meal_plan2]
        result = get_meal(plans, "invalid_meal")
        self.assertIsNone(result)

    def test_get_meal_filter_returns_first_match(self):
        """Test get_meal filter returns first matching meal plan when filtering a list"""
        # Create a dinner meal plan (different meal_type, so no conflict)
        dinner_plan = MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today(),
            meal_type="dinner",
            recipe=self.recipe2,
        )

        # Filter should find breakfast from list containing multiple meal types
        plans = [self.meal_plan1, self.meal_plan2, dinner_plan]
        result = get_meal(plans, "breakfast")
        self.assertEqual(result, self.meal_plan1)  # Should return the breakfast plan

    def test_get_meal_filter_with_objects_without_meal_type(self):
        """Test get_meal filter handles objects without meal_type attribute"""
        # Create a mock object without meal_type
        mock_object = Mock()
        del mock_object.meal_type  # Remove the attribute

        plans = [mock_object, self.meal_plan1]
        result = get_meal(plans, "breakfast")
        self.assertEqual(result, self.meal_plan1)

    def test_get_filter_with_valid_key(self):
        """Test get filter returns correct value for valid key"""
        test_dict = {"key1": "value1", "key2": "value2"}
        result = get(test_dict, "key1")
        self.assertEqual(result, "value1")

    def test_get_filter_with_invalid_key(self):
        """Test get filter returns None for invalid key"""
        test_dict = {"key1": "value1", "key2": "value2"}
        result = get(test_dict, "invalid_key")
        self.assertIsNone(result)

    def test_get_filter_with_empty_dict(self):
        """Test get filter with empty dictionary"""
        test_dict = {}
        result = get(test_dict, "any_key")
        self.assertIsNone(result)

    def test_get_filter_with_none_dict(self):
        """Test get filter handles None dictionary gracefully"""
        test_dict = None
        # This should raise an AttributeError since None doesn't have .get()
        with self.assertRaises(AttributeError):
            get(test_dict, "any_key")

    def test_get_filter_with_nested_values(self):
        """Test get filter with complex nested values"""
        test_dict = {"simple": "value", "complex": {"nested": "nested_value"}, "list": [1, 2, 3]}

        self.assertEqual(get(test_dict, "simple"), "value")
        self.assertEqual(get(test_dict, "complex"), {"nested": "nested_value"})
        self.assertEqual(get(test_dict, "list"), [1, 2, 3])

    @patch("recipes.templatetags.recipe_extras.anthropic.Anthropic")
    @patch("recipes.templatetags.recipe_extras.settings.ANTHROPIC_API_KEY", "test-api-key")
    def test_ai_generate_surprise_recipe_success(self, mock_anthropic):
        """Test ai_generate_surprise_recipe function with successful API call"""
        # Mock Anthropic response
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "Title: Surprise Recipe\nIngredients: Surprise ingredients\nSteps: Surprise steps"
        mock_response = Mock()
        mock_response.content = [mock_text_block]
        mock_client.messages.create.return_value = mock_response

        result = ai_generate_surprise_recipe()

        self.assertEqual(result, "Title: Surprise Recipe\nIngredients: Surprise ingredients\nSteps: Surprise steps")

        # Verify Anthropic was called correctly
        mock_anthropic.assert_called_once_with(api_key="test-api-key")
        mock_client.messages.create.assert_called_once()

        # Check the call arguments
        call_args = mock_client.messages.create.call_args
        self.assertEqual(call_args[1]["model"], "claude-haiku-4-5")
        self.assertEqual(len(call_args[1]["messages"]), 1)

    @patch("recipes.templatetags.recipe_extras.anthropic.Anthropic")
    @patch("recipes.templatetags.recipe_extras.settings.ANTHROPIC_API_KEY", "test-api-key")
    def test_ai_generate_surprise_recipe_empty_content(self, mock_anthropic):
        """Test ai_generate_surprise_recipe function with empty content"""
        # Mock Anthropic response with no text blocks
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        mock_response = Mock()
        mock_response.content = []
        mock_client.messages.create.return_value = mock_response

        result = ai_generate_surprise_recipe()
        self.assertIsNone(result)

    @patch("recipes.templatetags.recipe_extras.anthropic.Anthropic")
    @patch("recipes.templatetags.recipe_extras.settings.ANTHROPIC_API_KEY", "test-api-key")
    def test_ai_generate_surprise_recipe_whitespace_content(self, mock_anthropic):
        """Test ai_generate_surprise_recipe function with whitespace-only content"""
        # Mock Anthropic response with whitespace content
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "   \n\t   "
        mock_response = Mock()
        mock_response.content = [mock_text_block]
        mock_client.messages.create.return_value = mock_response

        result = ai_generate_surprise_recipe()
        self.assertEqual(result, "")  # Should be stripped to empty string

    @patch("recipes.templatetags.recipe_extras.anthropic.Anthropic")
    @patch("recipes.templatetags.recipe_extras.settings.ANTHROPIC_API_KEY", "test-api-key")
    def test_ai_generate_surprise_recipe_strips_whitespace(self, mock_anthropic):
        """Test ai_generate_surprise_recipe function strips leading/trailing whitespace"""
        # Mock Anthropic response with content that has whitespace
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "  \n  Title: Clean Recipe\nIngredients: Clean ingredients  \n  "
        mock_response = Mock()
        mock_response.content = [mock_text_block]
        mock_client.messages.create.return_value = mock_response

        result = ai_generate_surprise_recipe()
        self.assertEqual(result, "Title: Clean Recipe\nIngredients: Clean ingredients")

    @patch("recipes.templatetags.recipe_extras.anthropic.Anthropic")
    @patch("recipes.templatetags.recipe_extras.settings.ANTHROPIC_API_KEY", "test-api-key")
    def test_ai_generate_surprise_recipe_prompt_content(self, mock_anthropic):
        """Test that ai_generate_surprise_recipe sends correct prompt"""
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "Mock content"
        mock_response = Mock()
        mock_response.content = [mock_text_block]
        mock_client.messages.create.return_value = mock_response

        ai_generate_surprise_recipe()

        # Check the messages sent to Anthropic
        call_args = mock_client.messages.create.call_args

        # Check system message
        self.assertEqual(call_args[1]["system"], "You're a helpful chef assistant.")

        # Check user message contains expected prompt elements
        messages = call_args[1]["messages"]
        user_content = messages[0]["content"]
        self.assertIn("unique, family-friendly recipe", user_content)
        self.assertIn("common and surprising ingredients", user_content)
        self.assertIn("Title:", user_content)
        self.assertIn("Ingredients:", user_content)
        self.assertIn("Steps:", user_content)


class TemplateTagIntegrationTest(TestCase):
    """Test template tags working together in realistic scenarios"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser2", email="test2@example.com", password="testpass123")
        self.household = Household.objects.create(name="Test2")
        HouseholdMembership.objects.create(user=self.user, household=self.household)

    def test_get_meal_with_real_meal_plan_data(self):
        """Test get_meal filter with realistic meal plan data structure"""
        # Create meal plans for different meals
        breakfast_recipe = Recipe.objects.create(
            user=self.user, title="Pancakes", ingredients_text="Flour, eggs, milk", steps="Mix and cook"
        )
        lunch_recipe = Recipe.objects.create(
            user=self.user, title="Sandwich", ingredients_text="Bread, meat, cheese", steps="Assemble and serve"
        )

        meal_plans = [
            MealPlan.objects.create(
                household=self.household,
                added_by=self.user,
                date=date.today(),
                meal_type="breakfast",
                recipe=breakfast_recipe,
            ),
            MealPlan.objects.create(
                household=self.household,
                added_by=self.user,
                date=date.today(),
                meal_type="lunch",
                recipe=lunch_recipe,
            ),
        ]

        # Test getting each meal type
        breakfast_plan = get_meal(meal_plans, "breakfast")
        lunch_plan = get_meal(meal_plans, "lunch")
        dinner_plan = get_meal(meal_plans, "dinner")

        self.assertEqual(breakfast_plan.recipe.title, "Pancakes")
        self.assertEqual(lunch_plan.recipe.title, "Sandwich")
        self.assertIsNone(dinner_plan)

    def test_get_filter_with_template_context_data(self):
        """Test get filter with typical template context data"""
        # Simulate template context data structure
        context_data = {
            "week_days": [{"date": date.today(), "name": "Monday", "breakfast": None, "lunch": None, "dinner": None}],
            "meal_types": ["breakfast", "lunch", "dinner"],
            "user": self.user,
        }

        # Test accessing various context data
        self.assertEqual(get(context_data, "meal_types"), ["breakfast", "lunch", "dinner"])
        self.assertEqual(get(context_data, "user"), self.user)
        self.assertIsInstance(get(context_data, "week_days"), list)
        self.assertIsNone(get(context_data, "nonexistent_key"))
