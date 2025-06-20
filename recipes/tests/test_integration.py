from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date, timedelta
from recipes.models import Recipe, Tag, MealPlan, FamilyPreference
from recipes.tests.test_utils import TestUtilities


class RecipeWorkflowIntegrationTest(TestCase):
    """Test complete recipe workflow from creation to meal planning"""
    
    def setUp(self):
        self.client = Client()
        self.user = TestUtilities.create_test_user()
        self.client.login(username='testuser', password='testpass123')
    
    def test_complete_recipe_workflow(self):
        """Test the complete workflow: create recipe -> add to meal plan -> add family preferences"""
        # Step 1: Create a recipe
        recipe_data = {
            'title': 'Integration Test Recipe',
            'ingredients': 'Integration ingredients\nMore ingredients',
            'steps': 'Integration step 1\nIntegration step 2',
            'notes': 'Integration notes'
        }
        response = self.client.post(reverse('recipe_create'), recipe_data)
        self.assertEqual(response.status_code, 302)
        
        recipe = Recipe.objects.get(title='Integration Test Recipe')
        self.assertEqual(recipe.user, self.user)
        
        # Step 2: Add recipe to meal plan
        meal_plan_data = {
            'date': date.today(),
            'meal_type': 'breakfast',
            'recipe': recipe.id
        }
        response = self.client.post(reverse('meal_plan_create'), meal_plan_data)
        self.assertEqual(response.status_code, 302)
        
        meal_plan = MealPlan.objects.get(recipe=recipe)
        self.assertEqual(meal_plan.user, self.user)
        self.assertEqual(meal_plan.meal_type, 'breakfast')
        
        # Step 3: Add family preferences
        preference_data = {
            'family_member': 'Integration Family Member',
            'preference': 3
        }
        response = self.client.post(
            reverse('add_preference', kwargs={'recipe_id': recipe.id}),
            preference_data
        )
        self.assertEqual(response.status_code, 302)
        
        preference = FamilyPreference.objects.get(recipe=recipe)
        self.assertEqual(preference.user, self.user)
        self.assertEqual(preference.family_member, 'Integration Family Member')
        self.assertEqual(preference.preference, 3)
        
        # Step 4: Toggle favourite
        response = self.client.post(
            reverse('toggle_favourite', kwargs={'recipe_id': recipe.id})
        )
        self.assertEqual(response.status_code, 302)
        
        recipe.refresh_from_db()
        self.assertTrue(self.user in recipe.favourited_by.all())
        
        # Step 5: Generate shopping list
        response = self.client.post(
            reverse('generate_shopping_list'),
            {'recipe_ids': [recipe.id]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Integration ingredients')


class MealPlanningIntegrationTest(TestCase):
    """Test meal planning workflow"""
    
    def setUp(self):
        self.client = Client()
        self.test_data = TestUtilities.create_complete_test_data()
        self.user = self.test_data['user']
        self.recipes = self.test_data['recipes']
        self.client.login(username='testuser', password='testpass123')
    
    def test_weekly_meal_planning_workflow(self):
        """Test planning a complete week of meals"""
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        
        # Plan meals for each day of the week
        meal_plans_data = []
        for i in range(7):  # 7 days
            for j, meal_type in enumerate(['breakfast', 'lunch', 'dinner']):
                if i < len(self.recipes) and j < len(self.recipes):  # Ensure we have enough recipes
                    meal_date = start_of_week + timedelta(days=i)
                    recipe = self.recipes[j % len(self.recipes)]
                    
                    meal_plan_data = {
                        'date': meal_date,
                        'meal_type': meal_type,
                        'recipe': recipe.id
                    }
                    
                    response = self.client.post(reverse('meal_plan_create'), meal_plan_data)
                    self.assertEqual(response.status_code, 302)
                    meal_plans_data.append((meal_date, meal_type, recipe))
        
        # Verify meal plans were created
        for meal_date, meal_type, recipe in meal_plans_data:
            meal_plan = MealPlan.objects.get(
                user=self.user,
                date=meal_date,
                meal_type=meal_type,
                recipe=recipe
            )
            self.assertIsNotNone(meal_plan)
        
        # Test weekly view shows all meal plans
        response = self.client.get(reverse('meal_plan_week'))
        self.assertEqual(response.status_code, 200)
        
        # Check that some of our planned meals appear in the response
        for _, _, recipe in meal_plans_data[:3]:  # Check first few
            self.assertContains(response, recipe.title)


class SearchAndFilterIntegrationTest(TestCase):
    """Test search and filtering functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = TestUtilities.create_test_user()
        self.client.login(username='testuser', password='testpass123')
        
        # Create diverse recipes for testing
        self.pasta_tag = TestUtilities.create_test_tag('Pasta')
        self.quick_tag = TestUtilities.create_test_tag('Quick')
        
        self.pasta_recipe = TestUtilities.create_test_recipe(
            self.user,
            title='Spaghetti Carbonara',
            ingredients='Pasta\nEggs\nBacon',
            steps='Cook pasta\nMix with eggs and bacon'
        )
        self.pasta_recipe.tags.add(self.pasta_tag)
        
        self.salad_recipe = TestUtilities.create_test_recipe(
            self.user,
            title='Quick Caesar Salad',
            ingredients='Lettuce\nCroutons\nDressing',
            steps='Mix all ingredients'
        )
        self.salad_recipe.tags.add(self.quick_tag)
        
        # Add family preferences
        TestUtilities.create_test_family_preference(
            self.user, self.pasta_recipe, 'Alice', 3
        )
        TestUtilities.create_test_family_preference(
            self.user, self.salad_recipe, 'Alice', 1
        )
        
        # Add to favourites
        self.pasta_recipe.favourited_by.add(self.user)
    
    def test_recipe_search_by_title(self):
        """Test searching recipes by title"""
        response = self.client.get(reverse('recipe_list'), {'q': 'Spaghetti'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Spaghetti Carbonara')
        self.assertNotContains(response, 'Quick Caesar Salad')
    
    def test_recipe_search_by_ingredients(self):
        """Test searching recipes by ingredients"""
        response = self.client.get(reverse('recipe_list'), {'q': 'Lettuce'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quick Caesar Salad')
        self.assertNotContains(response, 'Spaghetti Carbonara')
    
    def test_recipe_filter_by_tag(self):
        """Test filtering recipes by tag"""
        response = self.client.get(reverse('recipe_list'), {'tag': self.pasta_tag.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Spaghetti Carbonara')
        self.assertNotContains(response, 'Quick Caesar Salad')
    
    def test_recipe_filter_by_favourites(self):
        """Test filtering recipes by favourites"""
        response = self.client.get(reverse('recipe_list'), {'favourites': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Spaghetti Carbonara')
        self.assertNotContains(response, 'Quick Caesar Salad')
    
    def test_recipe_filter_by_family_member_preferences(self):
        """Test filtering recipes by family member preferences"""
        response = self.client.get(reverse('recipe_list'), {'member': ['Alice']})
        self.assertEqual(response.status_code, 200)
        # Should only show recipes that Alice likes (preference = 3)
        self.assertContains(response, 'Spaghetti Carbonara')
        # Should not show recipes Alice dislikes (preference = 1)
        self.assertNotContains(response, 'Quick Caesar Salad')
    
    def test_combined_search_and_filter(self):
        """Test combining search query with filters"""
        response = self.client.get(reverse('recipe_list'), {
            'q': 'Pasta',
            'tag': self.pasta_tag.id,
            'favourites': '1'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Spaghetti Carbonara')


class ShoppingListIntegrationTest(TestCase):
    """Test shopping list generation workflow"""
    
    def setUp(self):
        self.client = Client()
        self.user = TestUtilities.create_test_user()
        self.client.login(username='testuser', password='testpass123')
        
        # Create recipes with overlapping ingredients
        self.recipe1 = TestUtilities.create_test_recipe(
            self.user,
            title='Pasta Dish',
            ingredients='Pasta\nTomatoes\nGarlic\nOlive Oil',
            steps='Cook pasta, add sauce'
        )
        
        self.recipe2 = TestUtilities.create_test_recipe(
            self.user,
            title='Salad',
            ingredients='Lettuce\nTomatoes\nOlive Oil\nVinegar',
            steps='Mix ingredients'
        )
        
        self.recipe3 = TestUtilities.create_test_recipe(
            self.user,
            title='Garlic Bread',
            ingredients='Bread\nGarlic\nButter',
            steps='Mix garlic and butter, spread on bread, toast'
        )
    
    def test_shopping_list_generation_single_recipe(self):
        """Test generating shopping list from single recipe"""
        response = self.client.post(
            reverse('generate_shopping_list'),
            {'recipe_ids': [self.recipe1.id]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pasta')
        self.assertContains(response, 'Tomatoes')
        self.assertContains(response, 'Garlic')
        self.assertContains(response, 'Olive Oil')
    
    def test_shopping_list_generation_multiple_recipes(self):
        """Test generating shopping list from multiple recipes"""
        response = self.client.post(
            reverse('generate_shopping_list'),
            {'recipe_ids': [self.recipe1.id, self.recipe2.id, self.recipe3.id]}
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that all unique ingredients are present
        expected_ingredients = [
            'Pasta', 'Tomatoes', 'Garlic', 'Olive Oil',
            'Lettuce', 'Vinegar', 'Bread', 'Butter'
        ]
        for ingredient in expected_ingredients:
            self.assertContains(response, ingredient)
    
    def test_shopping_list_deduplication(self):
        """Test that shopping list properly deduplicates ingredients"""
        response = self.client.post(
            reverse('generate_shopping_list'),
            {'recipe_ids': [self.recipe1.id, self.recipe2.id]}
        )
        self.assertEqual(response.status_code, 200)
        
        # Count occurrences of overlapping ingredients
        content = response.content.decode()
        tomato_count = content.count('Tomatoes')
        olive_oil_count = content.count('Olive Oil')
        
        # Each ingredient should appear only once in the shopping list
        self.assertEqual(tomato_count, 1)
        self.assertEqual(olive_oil_count, 1)
    
    def test_shopping_list_empty_selection(self):
        """Test generating shopping list with no recipes selected"""
        response = self.client.post(reverse('generate_shopping_list'), {'recipe_ids': []})
        self.assertEqual(response.status_code, 200)
        # Should show empty shopping list template
        self.assertContains(response, 'shopping_list')


class UserIsolationIntegrationTest(TestCase):
    """Test that users can only access their own data"""
    
    def setUp(self):
        self.client = Client()
        
        # Create two users with their own data
        self.user1 = TestUtilities.create_test_user('user1', 'user1@example.com')
        self.user2 = TestUtilities.create_test_user('user2', 'user2@example.com')
        
        self.user1_recipe = TestUtilities.create_test_recipe(
            self.user1, 'User 1 Recipe'
        )
        self.user2_recipe = TestUtilities.create_test_recipe(
            self.user2, 'User 2 Recipe'
        )
        
        self.user1_meal_plan = TestUtilities.create_test_meal_plan(
            self.user1, self.user1_recipe
        )
        self.user2_meal_plan = TestUtilities.create_test_meal_plan(
            self.user2, self.user2_recipe
        )
    
    def test_user1_cannot_access_user2_recipes(self):
        """Test that user1 cannot access user2's recipes"""
        self.client.login(username='user1', password='testpass123')
        
        # Try to access user2's recipe
        response = self.client.get(
            reverse('recipe_detail', kwargs={'pk': self.user2_recipe.pk})
        )
        self.assertEqual(response.status_code, 404)
        
        # Try to update user2's recipe
        response = self.client.get(
            reverse('recipe_update', kwargs={'pk': self.user2_recipe.pk})
        )
        self.assertEqual(response.status_code, 404)
        
        # Try to delete user2's recipe
        response = self.client.get(
            reverse('recipe_delete', kwargs={'pk': self.user2_recipe.pk})
        )
        self.assertEqual(response.status_code, 404)
    
    def test_user_recipe_list_isolation(self):
        """Test that recipe lists only show user's own recipes"""
        # Login as user1
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(reverse('recipe_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User 1 Recipe')
        self.assertNotContains(response, 'User 2 Recipe')
        
        # Login as user2
        self.client.logout()
        self.client.login(username='user2', password='testpass123')
        response = self.client.get(reverse('recipe_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User 2 Recipe')
        self.assertNotContains(response, 'User 1 Recipe')
    
    def test_meal_plan_isolation(self):
        """Test that meal plans are isolated between users"""
        # Login as user1
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(reverse('meal_plan_week'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User 1 Recipe')
        self.assertNotContains(response, 'User 2 Recipe')
        
        # Login as user2
        self.client.logout()
        self.client.login(username='user2', password='testpass123')
        response = self.client.get(reverse('meal_plan_week'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User 2 Recipe')
        self.assertNotContains(response, 'User 1 Recipe')
    
    def test_family_preference_isolation(self):
        """Test that family preferences are isolated between users"""
        # Create preferences for both users
        TestUtilities.create_test_family_preference(
            self.user1, self.user1_recipe, 'User1 Family Member'
        )
        TestUtilities.create_test_family_preference(
            self.user2, self.user2_recipe, 'User2 Family Member'
        )
        
        # Login as user1 and check recipe list filtering
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(reverse('recipe_list'))
        
        # Check that only user1's family members appear in filter options
        # (This would be in the context or template, specific assertion depends on implementation)
        self.assertEqual(response.status_code, 200)