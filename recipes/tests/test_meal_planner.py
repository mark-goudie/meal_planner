"""
Tests for Smart Meal Planner functionality.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from recipes.models import (
    CookingNote,
    MealPlan,
    MealPlannerPreferences,
    Recipe,
)
from recipes.models.household import Household, HouseholdMembership
from recipes.services import MealPlanningAssistantService


class MealPlannerPreferencesModelTest(TestCase):
    """Test the MealPlannerPreferences model"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")

    def test_create_preferences_with_defaults(self):
        """Test creating preferences with default values"""
        prefs = MealPlannerPreferences.objects.create(user=self.user)
        self.assertEqual(prefs.max_weeknight_time, 45)
        self.assertEqual(prefs.max_weekend_time, 90)
        self.assertEqual(prefs.avoid_repeat_days, 14)

    def test_one_preference_per_user(self):
        """Test that users can only have one preference object"""
        MealPlannerPreferences.objects.create(user=self.user)
        MealPlannerPreferences.objects.get_or_create(user=self.user)
        self.assertEqual(MealPlannerPreferences.objects.filter(user=self.user).count(), 1)


class MealPlanningAssistantServiceTest(TestCase):
    """Test the Meal Planning Assistant Service"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.household = Household.objects.create(name="Test")
        HouseholdMembership.objects.create(user=self.user, household=self.household)

        # Create some test recipes
        self.recipe1 = Recipe.objects.create(
            user=self.user,
            title="Quick Pasta",
            ingredients_text="pasta, sauce",
            steps="cook pasta",
            prep_time=10,
            cook_time=20,
        )
        self.recipe2 = Recipe.objects.create(
            user=self.user,
            title="Slow Roast",
            ingredients_text="meat, vegetables",
            steps="roast slowly",
            prep_time=20,
            cook_time=120,
        )
        self.recipe3 = Recipe.objects.create(
            user=self.user,
            title="Quick Stir Fry",
            ingredients_text="vegetables, sauce",
            steps="stir fry",
            prep_time=10,
            cook_time=15,
        )

    def test_get_or_create_preferences(self):
        """Test getting or creating user preferences"""
        prefs = MealPlanningAssistantService.get_or_create_preferences(self.user)
        self.assertIsNotNone(prefs)
        self.assertEqual(prefs.user, self.user)

        # Getting again should return same object
        prefs2 = MealPlanningAssistantService.get_or_create_preferences(self.user)
        self.assertEqual(prefs.id, prefs2.id)

    def test_calculate_recipe_happiness_score_neutral(self):
        """Test happiness score calculation with no notes (neutral)"""
        score = MealPlanningAssistantService.calculate_recipe_happiness_score(self.recipe3, self.user)
        self.assertEqual(score, Decimal("50.0"))

    def test_calculate_recipe_happiness_score_high(self):
        """Test happiness score calculation with high rating"""
        CookingNote.objects.create(
            recipe=self.recipe1,
            user=self.user,
            cooked_date=date.today(),
            rating=5,
            would_make_again=True,
        )
        score = MealPlanningAssistantService.calculate_recipe_happiness_score(self.recipe1, self.user)
        self.assertEqual(score, Decimal("100.0"))

    def test_calculate_recipe_happiness_score_low(self):
        """Test happiness score calculation with low rating"""
        CookingNote.objects.create(
            recipe=self.recipe2,
            user=self.user,
            cooked_date=date.today(),
            rating=1,
            would_make_again=False,
        )
        score = MealPlanningAssistantService.calculate_recipe_happiness_score(self.recipe2, self.user)
        self.assertLessEqual(score, Decimal("25"))

    def test_get_recently_cooked_recipes(self):
        """Test getting recently cooked recipes"""
        # Cook recipe1 today
        CookingNote.objects.create(
            user=self.user,
            recipe=self.recipe1,
            cooked_date=date.today(),
        )

        # Cook recipe2 20 days ago
        CookingNote.objects.create(
            user=self.user,
            recipe=self.recipe2,
            cooked_date=date.today() - timedelta(days=20),
        )

        # Get recipes from last 14 days
        recent_ids = MealPlanningAssistantService.get_recently_cooked_recipes(self.user, 14)

        self.assertIn(self.recipe1.id, recent_ids)
        self.assertNotIn(self.recipe2.id, recent_ids)

    def test_filter_recipes_by_time_constraint(self):
        """Test filtering recipes by cooking time"""
        recipes = [self.recipe1, self.recipe2, self.recipe3]

        # Filter for max 45 minutes
        filtered = MealPlanningAssistantService.filter_recipes_by_time_constraint(recipes, 45)

        self.assertIn(self.recipe1, filtered)  # 30 min total
        self.assertIn(self.recipe3, filtered)  # 25 min total
        self.assertNotIn(self.recipe2, filtered)  # 140 min total

    def test_generate_weekly_plan(self):
        """Test generating a weekly meal plan creates MealPlan entries"""
        MealPlanningAssistantService.generate_weekly_plan(user=self.user, meals_per_day=["dinner"])

        # Should have created 7 dinner entries
        meal_plans = MealPlan.objects.filter(household=self.household, meal_type="dinner")
        self.assertEqual(meal_plans.count(), 7)

        # Each entry should have a recipe
        for plan in meal_plans:
            self.assertIsNotNone(plan.recipe)

    def test_generate_plan_multiple_meals(self):
        """Test generating plan with multiple meals per day"""
        MealPlanningAssistantService.generate_weekly_plan(user=self.user, meals_per_day=["breakfast", "dinner"])

        # Should have 14 entries (7 days * 2 meals)
        meal_plans = MealPlan.objects.filter(household=self.household)
        self.assertEqual(meal_plans.count(), 14)


class MealPlannerViewsTest(TestCase):
    """Test the meal planner views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.household = Household.objects.create(name="Test")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.client.login(username="testuser", password="testpass")

        # Create a test recipe
        self.recipe = Recipe.objects.create(
            user=self.user, title="Test Recipe", ingredients_text="Test ingredients", steps="Test steps"
        )

    def test_meal_planner_preferences_view_get(self):
        """Test GET request to preferences view redirects to /settings/"""
        response = self.client.get(reverse("meal_planner_preferences"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/settings/")

    def test_meal_planner_preferences_view_post(self):
        """Test POST request to preferences view redirects to /settings/"""
        data = {
            "max_weeknight_time": 30,
            "max_weekend_time": 60,
            "avoid_repeat_days": 7,
            "reminder_time": "16:00",
        }
        response = self.client.post(reverse("meal_planner_preferences"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/settings/")

    def test_smart_meal_planner_view_get(self):
        """Test GET request to smart planner view redirects to /week/"""
        response = self.client.get(reverse("smart_meal_planner"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/week/")

    def test_smart_meal_planner_view_post(self):
        """Test POST request to smart planner redirects to /week/"""
        tomorrow = date.today() + timedelta(days=1)
        data = {"week_start": tomorrow.strftime("%Y-%m-%d"), "meals_to_plan": ["dinner"]}
        response = self.client.post(reverse("smart_meal_planner"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/week/")

    def test_unauthenticated_access(self):
        """Test that unauthenticated users are redirected"""
        self.client.logout()

        response = self.client.get(reverse("smart_meal_planner"))
        self.assertEqual(response.status_code, 302)  # Redirect to login
