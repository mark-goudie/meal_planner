from django.test import TestCase
from django.urls import reverse, resolve
from django.contrib.auth.models import User
from recipes import views
from recipes.models import Recipe


class UrlsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.recipe = Recipe.objects.create(
            user=self.user,
            title='Test Recipe',
            ingredients='Test ingredients',
            steps='Test steps'
        )

    def test_recipe_list_url(self):
        """Test recipe list URL resolves correctly"""
        url = reverse('recipe_list')
        self.assertEqual(url, '/')
        self.assertEqual(resolve(url).func, views.recipe_list)

    def test_recipe_create_url(self):
        """Test recipe create URL resolves correctly"""
        url = reverse('recipe_create')
        self.assertEqual(url, '/new/')
        self.assertEqual(resolve(url).func, views.recipe_create)

    def test_recipe_detail_url(self):
        """Test recipe detail URL resolves correctly"""
        url = reverse('recipe_detail', kwargs={'pk': self.recipe.pk})
        self.assertEqual(url, f'/{self.recipe.pk}/')
        self.assertEqual(resolve(url).func, views.recipe_detail)

    def test_recipe_update_url(self):
        """Test recipe update URL resolves correctly"""
        url = reverse('recipe_update', kwargs={'pk': self.recipe.pk})
        self.assertEqual(url, f'/{self.recipe.pk}/update/')
        self.assertEqual(resolve(url).func, views.recipe_update)

    def test_recipe_delete_url(self):
        """Test recipe delete URL resolves correctly"""
        url = reverse('recipe_delete', kwargs={'pk': self.recipe.pk})
        self.assertEqual(url, f'/{self.recipe.pk}/delete/')
        self.assertEqual(resolve(url).func, views.recipe_delete)

    def test_ai_generate_recipe_url(self):
        """Test AI generate recipe URL resolves correctly"""
        url = reverse('ai_generate_recipe')
        self.assertEqual(url, '/ai/generate/')
        self.assertEqual(resolve(url).func, views.ai_generate_recipe)

    def test_ai_create_recipe_url(self):
        """Test AI create recipe URL resolves correctly"""
        url = reverse('recipe_create_from_ai')
        self.assertEqual(url, '/ai-create/')
        self.assertEqual(resolve(url).func, views.recipe_create_from_ai)

    def test_meal_plan_list_url(self):
        """Test meal plan list URL resolves correctly"""
        url = reverse('meal_plan_list')
        self.assertEqual(url, '/meal-plan/')
        self.assertEqual(resolve(url).func, views.meal_plan_list)

    def test_meal_plan_create_url(self):
        """Test meal plan create URL resolves correctly"""
        url = reverse('meal_plan_create')
        self.assertEqual(url, '/meal-plan/new/')
        self.assertEqual(resolve(url).func, views.meal_plan_create)

    def test_meal_plan_week_url(self):
        """Test meal plan week URL resolves correctly"""
        url = reverse('meal_plan_week')
        self.assertEqual(url, '/meal-plan/week/')
        self.assertEqual(resolve(url).func, views.meal_plan_week)

    def test_add_preference_url(self):
        """Test add preference URL resolves correctly"""
        url = reverse('add_preference', kwargs={'recipe_id': self.recipe.id})
        self.assertEqual(url, f'/{self.recipe.id}/rate/')
        self.assertEqual(resolve(url).func, views.add_preference)

    def test_register_url(self):
        """Test register URL resolves correctly"""
        url = reverse('register')
        self.assertEqual(url, '/register/')
        self.assertEqual(resolve(url).func, views.register)

    def test_toggle_favourite_url(self):
        """Test toggle favourite URL resolves correctly"""
        url = reverse('toggle_favourite', kwargs={'recipe_id': self.recipe.id})
        self.assertEqual(url, f'/{self.recipe.id}/favourite/')
        self.assertEqual(resolve(url).func, views.toggle_favourite)

    def test_generate_shopping_list_url(self):
        """Test generate shopping list URL resolves correctly"""
        url = reverse('generate_shopping_list')
        self.assertEqual(url, '/shopping-list/')
        self.assertEqual(resolve(url).func, views.generate_shopping_list)

    def test_privacy_url(self):
        """Test privacy policy URL resolves correctly"""
        url = reverse('privacy')
        self.assertEqual(url, '/privacy/')
        self.assertEqual(resolve(url).func, views.privacy)

    def test_terms_url(self):
        """Test terms of service URL resolves correctly"""
        url = reverse('terms')
        self.assertEqual(url, '/terms/')
        self.assertEqual(resolve(url).func, views.terms)

    def test_disclaimer_url(self):
        """Test disclaimer URL resolves correctly"""
        url = reverse('disclaimer')
        self.assertEqual(url, '/disclaimer/')
        self.assertEqual(resolve(url).func, views.disclaimer)

    def test_getting_started_url(self):
        """Test getting started URL resolves correctly"""
        url = reverse('getting_started')
        self.assertEqual(url, '/getting-started/')
        self.assertEqual(resolve(url).func, views.getting_started)

    def test_ai_surprise_me_url(self):
        """Test AI surprise me URL resolves correctly"""
        url = reverse('ai_surprise_me')
        self.assertEqual(url, '/ai-surprise-me/')
        self.assertEqual(resolve(url).func, views.ai_surprise_me)

    def test_url_names_are_consistent(self):
        """Test that all URL names are accessible and consistent"""
        url_names = [
            'recipe_list',
            'recipe_create',
            'recipe_detail',
            'recipe_update',
            'recipe_delete',
            'ai_generate_recipe',
            'recipe_create_from_ai',
            'meal_plan_list',
            'meal_plan_create',
            'meal_plan_week',
            'add_preference',
            'register',
            'toggle_favourite',
            'generate_shopping_list',
            'privacy',
            'terms',
            'disclaimer',
            'getting_started',
            'ai_surprise_me',
        ]
        
        for url_name in url_names:
            if url_name in ['recipe_detail', 'recipe_update', 'recipe_delete']:
                # These require a pk argument
                url = reverse(url_name, kwargs={'pk': self.recipe.pk})
            elif url_name in ['add_preference', 'toggle_favourite']:
                # These require a recipe_id argument
                url = reverse(url_name, kwargs={'recipe_id': self.recipe.id})
            else:
                # These don't require arguments
                url = reverse(url_name)
            
            # Test that the URL was generated successfully
            self.assertIsInstance(url, str)
            self.assertTrue(url.startswith('/'))


    def test_url_accessibility_without_login(self):
        """Test which URLs are accessible without login"""
        public_urls = [
            'register',
            'privacy',
            'terms',
            'disclaimer',
            'getting_started'
        ]
        
        for url_name in public_urls:
            url = reverse(url_name)
            response = self.client.get(url)
            # Should not redirect to login (status 200 or other non-302)
            self.assertNotEqual(response.status_code, 302, 
                               f"URL {url_name} should be accessible without login")

    def test_protected_urls_require_login(self):
        """Test that protected URLs redirect to login"""
        protected_urls = [
            'recipe_list',
            'recipe_create',
            'ai_generate_recipe',
            'recipe_create_from_ai',
            'meal_plan_list',
            'meal_plan_create',
            'meal_plan_week',
            'generate_shopping_list',
            'ai_surprise_me'
        ]
        
        for url_name in protected_urls:
            url = reverse(url_name)
            response = self.client.get(url)
            # Should redirect to login
            self.assertEqual(response.status_code, 302,
                           f"URL {url_name} should require login")
            self.assertIn('/accounts/login/', response.url,
                         f"URL {url_name} should redirect to login")

    def test_object_specific_urls_require_login(self):
        """Test that object-specific URLs redirect to login for unauthenticated users"""
        object_specific_urls = [
            ('recipe_detail', {'pk': self.recipe.pk}),
            ('recipe_update', {'pk': self.recipe.pk}),
            ('recipe_delete', {'pk': self.recipe.pk}),
            ('add_preference', {'recipe_id': self.recipe.id}),
            ('toggle_favourite', {'recipe_id': self.recipe.id})
        ]
        
        for url_name, kwargs in object_specific_urls:
            url = reverse(url_name, kwargs=kwargs)
            response = self.client.get(url)
            # Should redirect to login
            self.assertEqual(response.status_code, 302,
                           f"URL {url_name} should require login")
            self.assertIn('/accounts/login/', response.url,
                         f"URL {url_name} should redirect to login")