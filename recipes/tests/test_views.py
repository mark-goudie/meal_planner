from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.http import HttpResponse
from unittest.mock import patch, Mock
from datetime import date, timedelta
from recipes.models import Recipe, Tag, MealPlan, FamilyPreference


class BaseViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        self.tag = Tag.objects.create(name='Test Tag')
        self.recipe = Recipe.objects.create(
            user=self.user,
            title='Test Recipe',
            ingredients='Test ingredients',
            steps='Test steps'
        )
        self.recipe.tags.add(self.tag)


class PublicViewTests(BaseViewTest):
    """Test views that don't require authentication"""

    def test_register_view_get(self):
        """Test GET request to register view"""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')

    def test_register_view_post_valid(self):
        """Test POST request to register view with valid data"""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful registration
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_view_post_invalid(self):
        """Test POST request to register view with invalid data"""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'invalid-email',
            'password1': 'pass',
            'password2': 'different'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_privacy_view(self):
        """Test privacy policy view"""
        response = self.client.get(reverse('privacy'))
        self.assertEqual(response.status_code, 200)

    def test_terms_view(self):
        """Test terms of service view"""
        response = self.client.get(reverse('terms'))
        self.assertEqual(response.status_code, 200)

    def test_disclaimer_view(self):
        """Test disclaimer view"""
        response = self.client.get(reverse('disclaimer'))
        self.assertEqual(response.status_code, 200)

    def test_getting_started_view(self):
        """Test getting started view"""
        response = self.client.get(reverse('getting_started'))
        self.assertEqual(response.status_code, 200)


class RecipeViewTests(BaseViewTest):
    """Test recipe-related views"""

    def test_recipe_list_requires_login(self):
        """Test that recipe list redirects to login for unauthenticated users"""
        response = self.client.get(reverse('recipe_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_recipe_list_authenticated(self):
        """Test recipe list view for authenticated users"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Recipe')

    def test_recipe_list_filtering_by_query(self):
        """Test recipe list filtering by search query"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_list'), {'q': 'Test'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Recipe')

    def test_recipe_list_filtering_by_tag(self):
        """Test recipe list filtering by tag"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_list'), {'tag': self.tag.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Recipe')

    def test_recipe_list_favourites_only(self):
        """Test recipe list showing favourites only"""
        self.recipe.favourited_by.add(self.user)
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_list'), {'favourites': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Recipe')

    def test_recipe_create_get(self):
        """Test GET request to recipe create view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')

    def test_recipe_create_post_valid(self):
        """Test POST request to recipe create view with valid data"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipe_create'), {
            'title': 'New Recipe',
            'ingredients': 'New ingredients',
            'steps': 'New steps'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Recipe.objects.filter(title='New Recipe').exists())

    def test_recipe_detail_view(self):
        """Test recipe detail view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_detail', kwargs={'pk': self.recipe.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Recipe')

    def test_recipe_detail_other_user_recipe(self):
        """Test that users can't view other users' recipes"""
        other_recipe = Recipe.objects.create(
            user=self.other_user,
            title='Other Recipe',
            ingredients='ingredients',
            steps='steps'
        )
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_detail', kwargs={'pk': other_recipe.pk}))
        self.assertEqual(response.status_code, 404)

    def test_recipe_update_view(self):
        """Test recipe update view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_update', kwargs={'pk': self.recipe.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Recipe')

    def test_recipe_update_post(self):
        """Test POST request to recipe update view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipe_update', kwargs={'pk': self.recipe.pk}), {
            'title': 'Updated Recipe',
            'ingredients': 'Updated ingredients',
            'steps': 'Updated steps'
        })
        self.assertEqual(response.status_code, 302)
        updated_recipe = Recipe.objects.get(pk=self.recipe.pk)
        self.assertEqual(updated_recipe.title, 'Updated Recipe')

    def test_recipe_delete_get(self):
        """Test GET request to recipe delete view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_delete', kwargs={'pk': self.recipe.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Recipe')

    def test_recipe_delete_post(self):
        """Test POST request to recipe delete view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('recipe_delete', kwargs={'pk': self.recipe.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Recipe.objects.filter(pk=self.recipe.pk).exists())

    def test_toggle_favourite(self):
        """Test toggling recipe favourite status"""
        self.client.login(username='testuser', password='testpass123')
        
        # Add to favourites
        response = self.client.post(reverse('toggle_favourite', kwargs={'recipe_id': self.recipe.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.user in self.recipe.favourited_by.all())
        
        # Remove from favourites
        response = self.client.post(reverse('toggle_favourite', kwargs={'recipe_id': self.recipe.id}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.user in self.recipe.favourited_by.all())


class AIViewTests(BaseViewTest):
    """Test AI-related views"""

    def test_ai_generate_recipe_get(self):
        """Test GET request to AI generate recipe view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('ai_generate_recipe'))
        self.assertEqual(response.status_code, 200)

    @patch('recipes.views.openai.OpenAI')
    def test_ai_generate_recipe_post_with_prompt(self, mock_openai):
        """Test POST request to AI generate recipe with prompt"""
        # Mock OpenAI response
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Title: AI Recipe\nIngredients: AI ingredients\nSteps: AI steps"
        mock_client.chat.completions.create.return_value = mock_response

        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('ai_generate_recipe'), {
            'prompt': 'chicken and rice'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AI Recipe')

    def test_ai_generate_recipe_use_recipe(self):
        """Test using generated AI recipe"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('ai_generate_recipe'), {
            'use_recipe': True,
            'generated_recipe': 'Title: Test AI Recipe\nIngredients: Test ingredients\nSteps: Test steps'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('recipe_create_from_ai'))

    def test_recipe_create_from_ai_get(self):
        """Test GET request to create recipe from AI data"""
        session = self.client.session
        session['ai_recipe_data'] = {
            'title': 'AI Recipe',
            'ingredients': 'AI ingredients',
            'steps': 'AI steps',
            'is_ai_generated': True
        }
        session.save()
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('recipe_create_from_ai'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AI Recipe')

    def test_ai_surprise_me(self):
        """Test AI surprise me functionality"""
        with patch('recipes.views.ai_generate_surprise_recipe') as mock_ai:
            mock_ai.return_value = "Title: Surprise Recipe\nIngredients: Surprise ingredients\nSteps: Surprise steps"
            
            self.client.login(username='testuser', password='testpass123')
            response = self.client.post(reverse('ai_surprise_me'))
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, reverse('recipe_create_from_ai'))


class MealPlanViewTests(BaseViewTest):
    """Test meal plan related views"""

    def test_meal_plan_list_view(self):
        """Test meal plan list view"""
        meal_plan = MealPlan.objects.create(
            user=self.user,
            date=date.today(),
            meal_type='breakfast',
            recipe=self.recipe
        )
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('meal_plan_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Recipe')

    def test_meal_plan_create_get(self):
        """Test GET request to meal plan create view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('meal_plan_create'))
        self.assertEqual(response.status_code, 200)

    def test_meal_plan_create_post(self):
        """Test POST request to meal plan create view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('meal_plan_create'), {
            'date': date.today(),
            'meal_type': 'breakfast',
            'recipe': self.recipe.id
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MealPlan.objects.filter(recipe=self.recipe).exists())

    def test_meal_plan_week_view(self):
        """Test weekly meal plan view"""
        MealPlan.objects.create(
            user=self.user,
            date=date.today(),
            meal_type='breakfast',
            recipe=self.recipe
        )
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('meal_plan_week'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Recipe')

    def test_meal_plan_week_with_offset(self):
        """Test weekly meal plan view with week offset"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('meal_plan_week'), {'week': 1})
        self.assertEqual(response.status_code, 200)


class FamilyPreferenceViewTests(BaseViewTest):
    """Test family preference related views"""

    def test_add_preference_get(self):
        """Test GET request to add preference view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('add_preference', kwargs={'recipe_id': self.recipe.id}))
        self.assertEqual(response.status_code, 200)

    def test_add_preference_post_new(self):
        """Test POST request to add new preference"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('add_preference', kwargs={'recipe_id': self.recipe.id}), {
            'family_member': 'Alice',
            'preference': 3
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(FamilyPreference.objects.filter(
            family_member='Alice',
            recipe=self.recipe,
            preference=3
        ).exists())

    def test_add_preference_post_update_existing(self):
        """Test POST request to update existing preference"""
        FamilyPreference.objects.create(
            user=self.user,
            family_member='Bob',
            recipe=self.recipe,
            preference=1
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('add_preference', kwargs={'recipe_id': self.recipe.id}), {
            'family_member': 'Bob',
            'preference': 3
        })
        self.assertEqual(response.status_code, 302)
        updated_pref = FamilyPreference.objects.get(family_member='Bob', recipe=self.recipe)
        self.assertEqual(updated_pref.preference, 3)


class ShoppingListViewTests(BaseViewTest):
    """Test shopping list related views"""

    def test_generate_shopping_list_get(self):
        """Test GET request to generate shopping list"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('generate_shopping_list'))
        self.assertEqual(response.status_code, 200)

    def test_generate_shopping_list_post(self):
        """Test POST request to generate shopping list"""
        recipe2 = Recipe.objects.create(
            user=self.user,
            title='Recipe 2',
            ingredients='Ingredient A\nIngredient B',
            steps='Steps'
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('generate_shopping_list'), {
            'recipe_ids': [self.recipe.id, recipe2.id]
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ingredient A')
        self.assertContains(response, 'Ingredient B')


class AuthenticationTests(BaseViewTest):
    """Test authentication and authorization"""

    def test_unauthenticated_access_redirects(self):
        """Test that protected views redirect unauthenticated users"""
        protected_urls = [
            'recipe_list',
            'recipe_create',
            'ai_generate_recipe',
            'meal_plan_list',
            'meal_plan_create',
            'meal_plan_week',
            'generate_shopping_list',
        ]
        
        for url_name in protected_urls:
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 302)
            self.assertIn('/accounts/login/', response.url)

    def test_user_can_only_access_own_data(self):
        """Test that users can only access their own recipes and meal plans"""
        other_recipe = Recipe.objects.create(
            user=self.other_user,
            title='Other Recipe',
            ingredients='ingredients',
            steps='steps'
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        # Should return 404 for other user's recipe
        response = self.client.get(reverse('recipe_detail', kwargs={'pk': other_recipe.pk}))
        self.assertEqual(response.status_code, 404)
        
        response = self.client.get(reverse('recipe_update', kwargs={'pk': other_recipe.pk}))
        self.assertEqual(response.status_code, 404)
        
        response = self.client.get(reverse('recipe_delete', kwargs={'pk': other_recipe.pk}))
        self.assertEqual(response.status_code, 404)