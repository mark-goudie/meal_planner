"""
Tests for service layer components.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
from datetime import date, timedelta
import openai

from recipes.models import Recipe, MealPlan, Tag, FamilyPreference
from recipes.services import (
    RecipeService,
    MealPlanService,
    AIService,
    AIConfigurationError,
    AIValidationError,
    AIAPIError
)


class RecipeServiceTest(TestCase):
    """Tests for RecipeService"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.other_user = User.objects.create_user(username='otheruser', password='testpass')

        self.recipe1 = Recipe.objects.create(
            user=self.user,
            title='Test Recipe 1',
            ingredients='ingredient 1\ningredient 2',
            steps='step 1\nstep 2'
        )

        self.recipe2 = Recipe.objects.create(
            user=self.user,
            title='Test Recipe 2',
            ingredients='ingredient 3\ningredient 4',
            steps='step 3\nstep 4'
        )

        self.tag1 = Tag.objects.create(name='Dinner')
        self.recipe1.tags.add(self.tag1)

    def test_get_recipes_for_user(self):
        """Test getting recipes for a user"""
        recipes = RecipeService.get_recipes_for_user(self.user)
        # Should only get recipes for this user
        self.assertGreaterEqual(recipes.count(), 2)
        # Verify all returned recipes belong to the user
        for recipe in recipes:
            self.assertEqual(recipe.user, self.user)

    def test_get_recipes_with_query(self):
        """Test recipe search"""
        recipes = RecipeService.get_recipes_for_user(self.user, query='Recipe 1')
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipes.first().title, 'Test Recipe 1')

    def test_get_recipes_with_tag_filter(self):
        """Test filtering by tag"""
        recipes = RecipeService.get_recipes_for_user(self.user, tag_id=self.tag1.id)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipes.first().title, 'Test Recipe 1')

    def test_get_recipes_favourites_only(self):
        """Test filtering by favourites"""
        self.recipe1.favourited_by.add(self.user)
        recipes = RecipeService.get_recipes_for_user(self.user, favourites_only=True)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipes.first().title, 'Test Recipe 1')

    def test_create_recipe(self):
        """Test creating a recipe"""
        recipe_data = {
            'title': 'New Recipe',
            'ingredients': 'New ingredients',
            'steps': 'New steps'
        }
        recipe = RecipeService.create_recipe(self.user, recipe_data)
        self.assertEqual(recipe.title, 'New Recipe')
        self.assertEqual(recipe.user, self.user)

    def test_update_recipe(self):
        """Test updating a recipe"""
        updated_data = {'title': 'Updated Recipe'}
        recipe = RecipeService.update_recipe(self.recipe1, updated_data)
        self.assertEqual(recipe.title, 'Updated Recipe')

    def test_delete_recipe(self):
        """Test deleting a recipe"""
        recipe_id = self.recipe1.id
        RecipeService.delete_recipe(self.recipe1)
        self.assertFalse(Recipe.objects.filter(id=recipe_id).exists())

    def test_toggle_favourite_add(self):
        """Test adding recipe to favourites"""
        is_favourited = RecipeService.toggle_favourite(self.user, self.recipe1)
        self.assertTrue(is_favourited)
        self.assertIn(self.user, self.recipe1.favourited_by.all())

    def test_toggle_favourite_remove(self):
        """Test removing recipe from favourites"""
        self.recipe1.favourited_by.add(self.user)
        is_favourited = RecipeService.toggle_favourite(self.user, self.recipe1)
        self.assertFalse(is_favourited)
        self.assertNotIn(self.user, self.recipe1.favourited_by.all())

    def test_add_or_update_preference_new(self):
        """Test adding a new family preference"""
        pref = RecipeService.add_or_update_preference(
            self.user, self.recipe1, 'John', 3
        )
        self.assertEqual(pref.family_member, 'John')
        self.assertEqual(pref.preference, 3)

    def test_add_or_update_preference_update(self):
        """Test updating an existing family preference"""
        FamilyPreference.objects.create(
            user=self.user,
            recipe=self.recipe1,
            family_member='John',
            preference=1
        )
        pref = RecipeService.add_or_update_preference(
            self.user, self.recipe1, 'John', 3
        )
        self.assertEqual(pref.preference, 3)

    def test_generate_shopping_list(self):
        """Test generating shopping list from multiple recipes"""
        recipe_ids = [self.recipe1.id, self.recipe2.id]
        shopping_list = RecipeService.generate_shopping_list(self.user, recipe_ids)
        self.assertEqual(len(shopping_list), 4)
        self.assertIn('ingredient 1', shopping_list)
        self.assertIn('ingredient 4', shopping_list)

    def test_get_family_members(self):
        """Test getting family members for a user"""
        FamilyPreference.objects.create(
            user=self.user,
            recipe=self.recipe1,
            family_member='John',
            preference=3
        )
        FamilyPreference.objects.create(
            user=self.user,
            recipe=self.recipe2,
            family_member='Jane',
            preference=2
        )
        members = RecipeService.get_family_members(self.user)
        self.assertEqual(members.count(), 2)


class MealPlanServiceTest(TestCase):
    """Tests for MealPlanService"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.recipe = Recipe.objects.create(
            user=self.user,
            title='Test Recipe',
            ingredients='ingredients',
            steps='steps'
        )
        self.today = date.today()

    def test_get_meal_plans_for_user(self):
        """Test getting meal plans for a user"""
        MealPlan.objects.create(
            user=self.user,
            recipe=self.recipe,
            date=self.today,
            meal_type='breakfast'
        )
        plans = MealPlanService.get_meal_plans_for_user(self.user)
        self.assertEqual(plans.count(), 1)

    def test_get_meal_plans_upcoming_only(self):
        """Test filtering for upcoming meal plans"""
        # Create past meal plan
        MealPlan.objects.create(
            user=self.user,
            recipe=self.recipe,
            date=self.today - timedelta(days=5),
            meal_type='breakfast'
        )
        # Create future meal plan
        MealPlan.objects.create(
            user=self.user,
            recipe=self.recipe,
            date=self.today + timedelta(days=2),
            meal_type='lunch'
        )

        plans = MealPlanService.get_meal_plans_for_user(self.user, upcoming_only=True)
        self.assertEqual(plans.count(), 1)
        self.assertEqual(plans.first().meal_type, 'lunch')

    def test_create_or_update_meal_plan_create(self):
        """Test creating a new meal plan"""
        meal_plan, created = MealPlanService.create_or_update_meal_plan(
            user=self.user,
            recipe=self.recipe,
            plan_date=self.today,
            meal_type='dinner'
        )
        self.assertTrue(created)
        self.assertEqual(meal_plan.meal_type, 'dinner')

    def test_create_or_update_meal_plan_update(self):
        """Test updating an existing meal plan"""
        # Create initial meal plan
        MealPlan.objects.create(
            user=self.user,
            recipe=self.recipe,
            date=self.today,
            meal_type='breakfast'
        )

        # Create new recipe for update
        new_recipe = Recipe.objects.create(
            user=self.user,
            title='New Recipe',
            ingredients='new ingredients',
            steps='new steps'
        )

        # Update the meal plan
        meal_plan, created = MealPlanService.create_or_update_meal_plan(
            user=self.user,
            recipe=new_recipe,
            plan_date=self.today,
            meal_type='breakfast'
        )

        self.assertFalse(created)
        self.assertEqual(meal_plan.recipe.title, 'New Recipe')

    def test_get_weekly_meal_plan(self):
        """Test getting structured weekly meal plan"""
        # Create meal plans for this week
        start_of_week = self.today - timedelta(days=self.today.weekday())

        MealPlan.objects.create(
            user=self.user,
            recipe=self.recipe,
            date=start_of_week,
            meal_type='breakfast'
        )

        result = MealPlanService.get_weekly_meal_plan(self.user, week_offset=0)

        self.assertIn('week_days', result)
        self.assertIn('week_start', result)
        self.assertIn('week_end', result)
        self.assertEqual(len(result['week_days']), 7)


class AIServiceTest(TestCase):
    """Tests for AIService"""

    def test_validate_api_key_missing(self):
        """Test API key validation with missing key"""
        with patch('recipes.services.ai_service.settings.OPENAI_API_KEY', None):
            with self.assertRaises(AIConfigurationError):
                AIService.validate_api_key()

    def test_validate_api_key_empty(self):
        """Test API key validation with empty key"""
        with patch('recipes.services.ai_service.settings.OPENAI_API_KEY', '   '):
            with self.assertRaises(AIConfigurationError):
                AIService.validate_api_key()

    def test_validate_prompt_empty(self):
        """Test prompt validation with empty prompt"""
        with self.assertRaises(AIValidationError):
            AIService.validate_prompt('')

    def test_validate_prompt_too_long(self):
        """Test prompt validation with too long prompt"""
        long_prompt = 'a' * 501
        with self.assertRaises(AIValidationError):
            AIService.validate_prompt(long_prompt)

    def test_validate_prompt_valid(self):
        """Test prompt validation with valid prompt"""
        prompt = AIService.validate_prompt('  Valid prompt  ')
        self.assertEqual(prompt, 'Valid prompt')

    @patch('recipes.services.ai_service.openai.OpenAI')
    @patch('recipes.services.ai_service.settings.OPENAI_API_KEY', 'test-key')
    def test_generate_recipe_from_prompt_success(self, mock_openai_class):
        """Test successful recipe generation"""
        # Mock the OpenAI API response
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Title: Test Recipe\nIngredients: Test ingredients\nSteps: Test steps"
        mock_client.chat.completions.create.return_value = mock_response

        result = AIService.generate_recipe_from_prompt('chicken and rice')

        self.assertIn('Test Recipe', result)
        mock_client.chat.completions.create.assert_called_once()

    @patch('recipes.services.ai_service.openai.OpenAI')
    @patch('recipes.services.ai_service.settings.OPENAI_API_KEY', 'test-key')
    def test_generate_recipe_authentication_error(self, mock_openai_class):
        """Test recipe generation with authentication error"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Create a mock response and body for AuthenticationError
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_client.chat.completions.create.side_effect = openai.AuthenticationError(
            'Auth failed',
            response=mock_response,
            body={}
        )

        with self.assertRaises(AIAPIError) as context:
            AIService.generate_recipe_from_prompt('chicken and rice')

        self.assertIn('authentication failed', str(context.exception).lower())

    def test_parse_generated_recipe_complete(self):
        """Test parsing a complete generated recipe"""
        text = """Title: Test Recipe
Ingredients:
- ingredient 1
- ingredient 2
Steps:
1. Step 1
2. Step 2"""

        title, ingredients, steps = AIService.parse_generated_recipe(text)

        self.assertEqual(title, 'Test Recipe')
        self.assertIn('ingredient 1', ingredients)
        self.assertIn('Step 1', steps)

    def test_parse_generated_recipe_directions(self):
        """Test parsing recipe with 'Directions' instead of 'Steps'"""
        text = """Title: Test Recipe
Ingredients:
- ingredient 1
Directions:
1. Step 1"""

        title, ingredients, steps = AIService.parse_generated_recipe(text)

        self.assertEqual(title, 'Test Recipe')
        self.assertIn('Step 1', steps)
