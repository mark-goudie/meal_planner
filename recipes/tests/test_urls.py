from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import resolve, reverse

from recipes import views
from recipes.models import Recipe


class UrlsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.recipe = Recipe.objects.create(user=self.user, title="Test Recipe", steps="Test steps")

    # --- Redesign URLs ---

    def test_home_url(self):
        """Test home URL resolves to week_view"""
        url = reverse("home")
        self.assertEqual(url, "/")
        self.assertEqual(resolve(url).func, views.week_view)

    def test_week_url(self):
        """Test week URL resolves correctly"""
        url = reverse("week")
        self.assertEqual(url, "/week/")
        self.assertEqual(resolve(url).func, views.week_view)

    def test_recipe_list_url(self):
        """Test recipe list URL resolves correctly"""
        url = reverse("recipe_list")
        self.assertEqual(url, "/recipes/")
        self.assertEqual(resolve(url).func, views.recipe_list_view)

    def test_recipe_create_url(self):
        """Test recipe create URL resolves correctly"""
        url = reverse("recipe_create")
        self.assertEqual(url, "/recipes/new/")
        self.assertEqual(resolve(url).func, views.recipe_create_view)

    def test_recipe_detail_url(self):
        """Test recipe detail URL resolves correctly"""
        url = reverse("recipe_detail", kwargs={"pk": self.recipe.pk})
        self.assertEqual(url, f"/recipes/{self.recipe.pk}/")
        self.assertEqual(resolve(url).func, views.recipe_detail_view)

    def test_recipe_update_url(self):
        """Test recipe update URL resolves correctly"""
        url = reverse("recipe_update", kwargs={"pk": self.recipe.pk})
        self.assertEqual(url, f"/recipes/{self.recipe.pk}/edit/")
        self.assertEqual(resolve(url).func, views.recipe_update_view)

    def test_recipe_delete_url(self):
        """Test recipe delete URL resolves correctly"""
        url = reverse("recipe_delete", kwargs={"pk": self.recipe.pk})
        self.assertEqual(url, f"/recipes/{self.recipe.pk}/delete/")
        self.assertEqual(resolve(url).func, views.recipe_delete_view)

    def test_toggle_favourite_url(self):
        """Test toggle favourite URL resolves correctly"""
        url = reverse("toggle_favourite", kwargs={"pk": self.recipe.pk})
        self.assertEqual(url, f"/recipes/{self.recipe.pk}/favourite/")
        self.assertEqual(resolve(url).func, views.toggle_favourite_view)

    def test_recipe_search_url(self):
        """Test recipe search URL resolves correctly"""
        url = reverse("recipe_search")
        self.assertEqual(url, "/recipes/search/")
        self.assertEqual(resolve(url).func, views.recipe_search)

    # --- Legacy URLs still in use ---

    def test_ai_generate_recipe_url(self):
        """Test AI generate recipe URL resolves correctly"""
        url = reverse("ai_generate_recipe")
        self.assertEqual(url, "/recipes/ai/generate/")
        self.assertEqual(resolve(url).func, views.ai_generate_recipe)

    def test_ai_create_recipe_url(self):
        """Test AI create recipe URL resolves correctly"""
        url = reverse("recipe_create_from_ai")
        self.assertEqual(url, "/recipes/ai-create/")
        self.assertEqual(resolve(url).func, views.recipe_create_from_ai)

    def test_meal_plan_list_url(self):
        """Test meal plan list URL resolves correctly"""
        url = reverse("meal_plan_list")
        self.assertEqual(url, "/meal-plan/")
        self.assertEqual(resolve(url).func, views.meal_plan_list)

    def test_meal_plan_create_url(self):
        """Test meal plan create URL resolves correctly"""
        url = reverse("meal_plan_create")
        self.assertEqual(url, "/meal-plan/new/")
        self.assertEqual(resolve(url).func, views.meal_plan_create)

    def test_meal_plan_week_url(self):
        """Test meal plan week URL resolves correctly"""
        url = reverse("meal_plan_week")
        self.assertEqual(url, "/meal-plan/week/")
        self.assertEqual(resolve(url).func, views.meal_plan_week)

    def test_register_url(self):
        """Test register URL resolves correctly"""
        url = reverse("register")
        self.assertEqual(url, "/register/")
        self.assertEqual(resolve(url).func, views.register_view)

    def test_generate_shopping_list_url(self):
        """Test generate shopping list URL resolves correctly"""
        url = reverse("generate_shopping_list")
        self.assertEqual(url, "/shopping-list/")
        self.assertEqual(resolve(url).func, views.generate_shopping_list)

    def test_privacy_url(self):
        """Test privacy policy URL resolves correctly"""
        url = reverse("privacy")
        self.assertEqual(url, "/privacy/")
        self.assertEqual(resolve(url).func, views.privacy)

    def test_terms_url(self):
        """Test terms of service URL resolves correctly"""
        url = reverse("terms")
        self.assertEqual(url, "/terms/")
        self.assertEqual(resolve(url).func, views.terms)

    def test_disclaimer_url(self):
        """Test disclaimer URL resolves correctly"""
        url = reverse("disclaimer")
        self.assertEqual(url, "/disclaimer/")
        self.assertEqual(resolve(url).func, views.disclaimer)

    def test_getting_started_url(self):
        """Test getting started URL resolves correctly"""
        url = reverse("getting_started")
        self.assertEqual(url, "/getting-started/")
        self.assertEqual(resolve(url).func, views.getting_started)

    def test_ai_surprise_me_url(self):
        """Test AI surprise me URL resolves correctly"""
        url = reverse("ai_surprise_me")
        self.assertEqual(url, "/ai-surprise-me/")
        self.assertEqual(resolve(url).func, views.ai_surprise_me)

    # --- New redesign URLs ---

    def test_shop_url(self):
        """Test shop URL resolves correctly"""
        url = reverse("shop")
        self.assertEqual(url, "/shop/")
        self.assertEqual(resolve(url).func, views.shop_view)

    def test_settings_url(self):
        """Test settings URL resolves correctly"""
        url = reverse("settings")
        self.assertEqual(url, "/settings/")
        self.assertEqual(resolve(url).func, views.settings_view)

    def test_cook_url(self):
        """Test cook URL resolves correctly"""
        url = reverse("cook", kwargs={"pk": self.recipe.pk})
        self.assertEqual(url, f"/cook/{self.recipe.pk}/")
        self.assertEqual(resolve(url).func, views.cook_view)

    # --- Access control ---

    def test_url_accessibility_without_login(self):
        """Test which URLs are accessible without login"""
        public_urls = ["register", "privacy", "terms", "disclaimer"]

        for url_name in public_urls:
            url = reverse(url_name)
            response = self.client.get(url)
            self.assertNotEqual(response.status_code, 302, f"URL {url_name} should be accessible without login")

    def test_protected_urls_require_login(self):
        """Test that protected URLs redirect to login"""
        protected_urls = [
            "recipe_list",
            "recipe_create",
            "ai_generate_recipe",
            "recipe_create_from_ai",
            "meal_plan_list",
            "meal_plan_create",
            "meal_plan_week",
            "generate_shopping_list",
            "ai_surprise_me",
            "week",
            "shop",
            "settings",
        ]

        for url_name in protected_urls:
            url = reverse(url_name)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, f"URL {url_name} should require login")
            self.assertIn("/accounts/login/", response.url, f"URL {url_name} should redirect to login")

    def test_object_specific_urls_require_login(self):
        """Test that object-specific URLs redirect to login for unauthenticated users"""
        object_specific_urls = [
            ("recipe_detail", {"pk": self.recipe.pk}),
            ("recipe_update", {"pk": self.recipe.pk}),
            ("recipe_delete", {"pk": self.recipe.pk}),
            ("toggle_favourite", {"pk": self.recipe.pk}),
            ("cook", {"pk": self.recipe.pk}),
        ]

        for url_name, kwargs in object_specific_urls:
            url = reverse(url_name, kwargs=kwargs)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, f"URL {url_name} should require login")
            self.assertIn("/accounts/login/", response.url, f"URL {url_name} should redirect to login")
