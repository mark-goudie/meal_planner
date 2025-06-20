from django.test import TestCase
from django.contrib.auth.models import User
from recipes.models import Recipe, Tag, MealPlan, FamilyPreference
from recipes.views import parse_generated_recipe
from datetime import date, timedelta


class TestUtilities:
    """Utility class for common test operations"""
    
    @staticmethod
    def create_test_user(username='testuser', email='test@example.com', password='testpass123'):
        """Create a test user with default or custom credentials"""
        return User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
    
    @staticmethod
    def create_test_recipe(user, title='Test Recipe', ingredients='Test ingredients', steps='Test steps', **kwargs):
        """Create a test recipe with default or custom data"""
        defaults = {
            'user': user,
            'title': title,
            'ingredients': ingredients,
            'steps': steps
        }
        defaults.update(kwargs)
        return Recipe.objects.create(**defaults)
    
    @staticmethod
    def create_test_tag(name='Test Tag'):
        """Create a test tag"""
        tag, _ = Tag.objects.get_or_create(name=name)
        return tag
    
    @staticmethod
    def create_test_meal_plan(user, recipe, meal_type='breakfast', plan_date=None):
        """Create a test meal plan"""
        if plan_date is None:
            plan_date = date.today()
        return MealPlan.objects.create(
            user=user,
            recipe=recipe,
            meal_type=meal_type,
            date=plan_date
        )
    
    @staticmethod
    def create_test_family_preference(user, recipe, family_member='Test Member', preference=3):
        """Create a test family preference"""
        return FamilyPreference.objects.create(
            user=user,
            recipe=recipe,
            family_member=family_member,
            preference=preference
        )
    
    @staticmethod
    def create_complete_test_data(username='testuser'):
        """Create a complete set of test data including user, recipes, tags, meal plans, and preferences"""
        user = TestUtilities.create_test_user(username=username)
        
        # Create tags
        tag1 = TestUtilities.create_test_tag('Breakfast')
        tag2 = TestUtilities.create_test_tag('Quick')
        tag3 = TestUtilities.create_test_tag('Healthy')
        
        # Create recipes
        recipe1 = TestUtilities.create_test_recipe(
            user=user,
            title='Pancakes',
            ingredients='Flour\nEggs\nMilk',
            steps='Mix ingredients\nCook on griddle'
        )
        recipe1.tags.add(tag1, tag2)
        
        recipe2 = TestUtilities.create_test_recipe(
            user=user,
            title='Salad',
            ingredients='Lettuce\nTomatoes\nCucumber',
            steps='Chop vegetables\nMix together'
        )
        recipe2.tags.add(tag3)
        
        # Create meal plans
        meal_plan1 = TestUtilities.create_test_meal_plan(user, recipe1, 'breakfast')
        meal_plan2 = TestUtilities.create_test_meal_plan(user, recipe2, 'lunch')
        
        # Create family preferences
        pref1 = TestUtilities.create_test_family_preference(user, recipe1, 'Alice', 3)
        pref2 = TestUtilities.create_test_family_preference(user, recipe2, 'Bob', 2)
        
        return {
            'user': user,
            'tags': [tag1, tag2, tag3],
            'recipes': [recipe1, recipe2],
            'meal_plans': [meal_plan1, meal_plan2],
            'preferences': [pref1, pref2]
        }


class ParseGeneratedRecipeTest(TestCase):
    """Test the parse_generated_recipe utility function"""
    
    def test_parse_complete_recipe(self):
        """Test parsing a complete AI-generated recipe"""
        generated_text = """Title: Delicious Pasta
Ingredients:
- 2 cups pasta
- 1 cup tomato sauce
- 1/2 cup cheese
Steps:
1. Boil pasta
2. Add sauce
3. Top with cheese"""
        
        title, ingredients, steps = parse_generated_recipe(generated_text)
        
        self.assertEqual(title, 'Delicious Pasta')
        self.assertIn('2 cups pasta', ingredients)
        self.assertIn('1 cup tomato sauce', ingredients)
        self.assertIn('1/2 cup cheese', ingredients)
        self.assertIn('1. Boil pasta', steps)
        self.assertIn('2. Add sauce', steps)
        self.assertIn('3. Top with cheese', steps)
    
    def test_parse_recipe_with_directions_instead_of_steps(self):
        """Test parsing recipe that uses 'Directions:' instead of 'Steps:'"""
        generated_text = """Title: Quick Sandwich
Ingredients:
- Bread
- Ham
- Cheese
Directions:
- Toast bread
- Add ham and cheese
- Serve immediately"""
        
        title, ingredients, steps = parse_generated_recipe(generated_text)
        
        self.assertEqual(title, 'Quick Sandwich')
        self.assertIn('Bread', ingredients)
        self.assertIn('Toast bread', steps)
        self.assertIn('Add ham and cheese', steps)
    
    def test_parse_recipe_case_insensitive(self):
        """Test parsing recipe with different case variations"""
        generated_text = """title: Lowercase Recipe
ingredients:
- Some ingredient
steps:
- Some step"""
        
        title, ingredients, steps = parse_generated_recipe(generated_text)
        
        self.assertEqual(title, 'Lowercase Recipe')
        self.assertIn('Some ingredient', ingredients)
        self.assertIn('Some step', steps)
    
    def test_parse_recipe_missing_sections(self):
        """Test parsing recipe with missing sections"""
        generated_text = """Title: Incomplete Recipe
Ingredients:
- Only ingredients here
Steps:"""
        
        title, ingredients, steps = parse_generated_recipe(generated_text)
        
        self.assertEqual(title, 'Incomplete Recipe')
        self.assertIn('Only ingredients here', ingredients)
        self.assertEqual(steps, '')  # Should be empty string
    
    def test_parse_recipe_no_title(self):
        """Test parsing recipe without title"""
        generated_text = """Ingredients:
- Some ingredients
Steps:
- Some steps"""
        
        title, ingredients, steps = parse_generated_recipe(generated_text)
        
        self.assertEqual(title, '')  # Should be empty string
        self.assertIn('Some ingredients', ingredients)
        self.assertIn('Some steps', steps)
    
    def test_parse_recipe_malformed_text(self):
        """Test parsing completely malformed text"""
        generated_text = "This is just random text without proper structure"
        
        title, ingredients, steps = parse_generated_recipe(generated_text)
        
        self.assertEqual(title, '')
        self.assertEqual(ingredients, '')
        self.assertEqual(steps, '')
    
    def test_parse_recipe_empty_text(self):
        """Test parsing empty text"""
        generated_text = ""
        
        title, ingredients, steps = parse_generated_recipe(generated_text)
        
        self.assertEqual(title, '')
        self.assertEqual(ingredients, '')
        self.assertEqual(steps, '')
    
    def test_parse_recipe_strips_whitespace(self):
        """Test that parsing strips whitespace from extracted sections"""
        generated_text = """Title:   Recipe with Spaces   
Ingredients:
   - Ingredient 1
   - Ingredient 2
Steps:
   - Step 1
   - Step 2"""
        
        title, ingredients, steps = parse_generated_recipe(generated_text)
        
        self.assertEqual(title, 'Recipe with Spaces')
        # Check that title was stripped of whitespace
        self.assertFalse(title.startswith(' '))
        self.assertFalse(title.endswith(' '))
    
    def test_parse_recipe_multiline_sections(self):
        """Test parsing recipe with multi-line sections"""
        generated_text = """Title: Complex Recipe
Ingredients:
- First ingredient
- Second ingredient with
  multiple lines
- Third ingredient
Steps:
1. First step
2. Second step that spans
   multiple lines for clarity
3. Final step"""
        
        title, ingredients, steps = parse_generated_recipe(generated_text)
        
        self.assertEqual(title, 'Complex Recipe')
        self.assertIn('First ingredient', ingredients)
        self.assertIn('multiple lines', ingredients)
        self.assertIn('First step', steps)
        self.assertIn('multiple lines for clarity', steps)


class TestUtilitiesTest(TestCase):
    """Test the test utilities themselves"""
    
    def test_create_test_user(self):
        """Test creating a test user with defaults"""
        user = TestUtilities.create_test_user()
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
    
    def test_create_test_user_custom(self):
        """Test creating a test user with custom values"""
        user = TestUtilities.create_test_user(
            username='customuser',
            email='custom@example.com',
            password='custompass'
        )
        self.assertEqual(user.username, 'customuser')
        self.assertEqual(user.email, 'custom@example.com')
        self.assertTrue(user.check_password('custompass'))
    
    def test_create_test_recipe(self):
        """Test creating a test recipe"""
        user = TestUtilities.create_test_user()
        recipe = TestUtilities.create_test_recipe(user)
        
        self.assertEqual(recipe.user, user)
        self.assertEqual(recipe.title, 'Test Recipe')
        self.assertEqual(recipe.ingredients, 'Test ingredients')
        self.assertEqual(recipe.steps, 'Test steps')
    
    def test_create_test_recipe_custom(self):
        """Test creating a test recipe with custom values"""
        user = TestUtilities.create_test_user()
        recipe = TestUtilities.create_test_recipe(
            user,
            title='Custom Recipe',
            author='Custom Author',
            is_ai_generated=True
        )
        
        self.assertEqual(recipe.title, 'Custom Recipe')
        self.assertEqual(recipe.author, 'Custom Author')
        self.assertTrue(recipe.is_ai_generated)
    
    def test_create_complete_test_data(self):
        """Test creating complete test data set"""
        data = TestUtilities.create_complete_test_data('completeuser')
        
        self.assertEqual(data['user'].username, 'completeuser')
        self.assertEqual(len(data['tags']), 3)
        self.assertEqual(len(data['recipes']), 2)
        self.assertEqual(len(data['meal_plans']), 2)
        self.assertEqual(len(data['preferences']), 2)
        
        # Check relationships
        self.assertEqual(data['recipes'][0].user, data['user'])
        self.assertEqual(data['meal_plans'][0].user, data['user'])
        self.assertEqual(data['preferences'][0].user, data['user'])
    
    def test_create_test_meal_plan_default_date(self):
        """Test creating meal plan with default date"""
        user = TestUtilities.create_test_user()
        recipe = TestUtilities.create_test_recipe(user)
        meal_plan = TestUtilities.create_test_meal_plan(user, recipe)
        
        self.assertEqual(meal_plan.date, date.today())
        self.assertEqual(meal_plan.meal_type, 'breakfast')
    
    def test_create_test_meal_plan_custom_date(self):
        """Test creating meal plan with custom date"""
        user = TestUtilities.create_test_user()
        recipe = TestUtilities.create_test_recipe(user)
        custom_date = date.today() + timedelta(days=7)
        meal_plan = TestUtilities.create_test_meal_plan(
            user, recipe, 'dinner', custom_date
        )
        
        self.assertEqual(meal_plan.date, custom_date)
        self.assertEqual(meal_plan.meal_type, 'dinner')


class DatabaseTestCase(TestCase):
    """Base test case with common database operations"""
    
    def setUp(self):
        """Set up common test data"""
        self.test_data = TestUtilities.create_complete_test_data()
        self.user = self.test_data['user']
        self.recipes = self.test_data['recipes']
        self.tags = self.test_data['tags']
    
    def tearDown(self):
        """Clean up after tests"""
        # Django's TestCase handles database cleanup automatically
        pass
    
    def assertRecipeExists(self, title):
        """Assert that a recipe with the given title exists"""
        self.assertTrue(
            Recipe.objects.filter(title=title).exists(),
            f"Recipe '{title}' does not exist"
        )
    
    def assertUserHasRecipe(self, user, recipe_title):
        """Assert that a user has a recipe with the given title"""
        self.assertTrue(
            Recipe.objects.filter(user=user, title=recipe_title).exists(),
            f"User '{user.username}' does not have recipe '{recipe_title}'"
        )
    
    def assertMealPlanExists(self, user, date, meal_type):
        """Assert that a meal plan exists for the given user, date, and meal type"""
        self.assertTrue(
            MealPlan.objects.filter(user=user, date=date, meal_type=meal_type).exists(),
            f"Meal plan for {meal_type} on {date} does not exist for user {user.username}"
        )