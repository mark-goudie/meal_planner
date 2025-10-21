"""
Tests for Smart Meal Planner functionality.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date, timedelta
from decimal import Decimal

from recipes.models import (
    Recipe, Tag, FamilyPreference, MealPlan,
    MealPlannerPreferences, DietaryRestriction,
    GeneratedMealPlan, GeneratedMealPlanEntry,
    RecipeCookingHistory
)
from recipes.services import MealPlanningAssistantService


class MealPlannerPreferencesModelTest(TestCase):
    """Test the MealPlannerPreferences model"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')

    def test_create_preferences_with_defaults(self):
        """Test creating preferences with default values"""
        prefs = MealPlannerPreferences.objects.create(user=self.user)
        self.assertEqual(prefs.max_weeknight_time, 45)
        self.assertEqual(prefs.max_weekend_time, 90)
        self.assertEqual(prefs.avoid_repeat_days, 14)
        self.assertEqual(prefs.variety_score, 7)
        self.assertTrue(prefs.use_leftovers)
        self.assertFalse(prefs.batch_cooking_friendly)

    def test_one_preference_per_user(self):
        """Test that users can only have one preference object"""
        MealPlannerPreferences.objects.create(user=self.user)
        # Creating another should work but there should still be only one
        prefs = MealPlannerPreferences.objects.get_or_create(user=self.user)[0]
        self.assertEqual(MealPlannerPreferences.objects.filter(user=self.user).count(), 1)


class RecipeCookingHistoryModelTest(TestCase):
    """Test the RecipeCookingHistory model"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.recipe = Recipe.objects.create(
            user=self.user,
            title='Test Recipe',
            ingredients='Test ingredients',
            steps='Test steps'
        )

    def test_create_cooking_history(self):
        """Test creating a cooking history entry"""
        history = RecipeCookingHistory.objects.create(
            user=self.user,
            recipe=self.recipe,
            cooked_date=date.today(),
            meal_type='dinner',
            rating=5
        )
        self.assertEqual(history.rating, 5)
        self.assertEqual(history.meal_type, 'dinner')

    def test_cooking_history_ordering(self):
        """Test that cooking history is ordered by date descending"""
        # Create multiple entries
        RecipeCookingHistory.objects.create(
            user=self.user,
            recipe=self.recipe,
            cooked_date=date.today() - timedelta(days=2),
            meal_type='dinner'
        )
        RecipeCookingHistory.objects.create(
            user=self.user,
            recipe=self.recipe,
            cooked_date=date.today(),
            meal_type='dinner'
        )

        history = RecipeCookingHistory.objects.all()
        self.assertEqual(history[0].cooked_date, date.today())


class MealPlanningAssistantServiceTest(TestCase):
    """Test the Meal Planning Assistant Service"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')

        # Create some test recipes
        self.recipe1 = Recipe.objects.create(
            user=self.user,
            title='Quick Pasta',
            ingredients='pasta, sauce',
            steps='cook pasta',
            prep_time=10,
            cook_time=20
        )
        self.recipe2 = Recipe.objects.create(
            user=self.user,
            title='Slow Roast',
            ingredients='meat, vegetables',
            steps='roast slowly',
            prep_time=20,
            cook_time=120
        )
        self.recipe3 = Recipe.objects.create(
            user=self.user,
            title='Quick Stir Fry',
            ingredients='vegetables, sauce',
            steps='stir fry',
            prep_time=10,
            cook_time=15
        )

        # Add family preferences
        FamilyPreference.objects.create(
            user=self.user,
            recipe=self.recipe1,
            family_member='John',
            preference=3  # Like
        )
        FamilyPreference.objects.create(
            user=self.user,
            recipe=self.recipe2,
            family_member='John',
            preference=1  # Dislike
        )

    def test_get_or_create_preferences(self):
        """Test getting or creating user preferences"""
        prefs = MealPlanningAssistantService.get_or_create_preferences(self.user)
        self.assertIsNotNone(prefs)
        self.assertEqual(prefs.user, self.user)

        # Getting again should return same object
        prefs2 = MealPlanningAssistantService.get_or_create_preferences(self.user)
        self.assertEqual(prefs.id, prefs2.id)

    def test_calculate_recipe_happiness_score(self):
        """Test happiness score calculation"""
        prefs = MealPlanningAssistantService.get_or_create_preferences(self.user)

        # Recipe1 has "like" preference
        score1 = MealPlanningAssistantService.calculate_recipe_happiness_score(
            self.recipe1, self.user, prefs
        )
        self.assertGreater(score1, Decimal('75'))  # Should be high

        # Recipe2 has "dislike" preference
        score2 = MealPlanningAssistantService.calculate_recipe_happiness_score(
            self.recipe2, self.user, prefs
        )
        self.assertLess(score2, Decimal('25'))  # Should be low

        # Recipe3 has no preferences
        score3 = MealPlanningAssistantService.calculate_recipe_happiness_score(
            self.recipe3, self.user, prefs
        )
        self.assertEqual(score3, Decimal('50'))  # Should be neutral

    def test_get_recently_cooked_recipes(self):
        """Test getting recently cooked recipes"""
        # Cook recipe1 today
        RecipeCookingHistory.objects.create(
            user=self.user,
            recipe=self.recipe1,
            cooked_date=date.today(),
            meal_type='dinner'
        )

        # Cook recipe2 20 days ago
        RecipeCookingHistory.objects.create(
            user=self.user,
            recipe=self.recipe2,
            cooked_date=date.today() - timedelta(days=20),
            meal_type='dinner'
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

    def test_calculate_variety_score(self):
        """Test variety score calculation"""
        prefs = MealPlanningAssistantService.get_or_create_preferences(self.user)

        # All different recipes = high variety
        score1 = MealPlanningAssistantService.calculate_variety_score(
            [self.recipe1, self.recipe2, self.recipe3],
            prefs
        )
        self.assertGreater(score1, Decimal('0'))

        # Same recipe repeated = low variety
        score2 = MealPlanningAssistantService.calculate_variety_score(
            [self.recipe1, self.recipe1, self.recipe1],
            prefs
        )
        self.assertGreater(score1, score2)

    def test_generate_weekly_plan(self):
        """Test generating a weekly meal plan"""
        plan = MealPlanningAssistantService.generate_weekly_plan(
            user=self.user,
            meals_per_day=['dinner']
        )

        self.assertIsNotNone(plan)
        self.assertEqual(plan.user, self.user)
        self.assertIsNotNone(plan.week_start)
        self.assertIsNotNone(plan.week_end)

        # Should have 7 dinner entries
        entries = plan.entries.all()
        self.assertEqual(entries.count(), 7)

        # Each entry should have a recipe and happiness score
        for entry in entries:
            self.assertIsNotNone(entry.recipe)
            self.assertIsNotNone(entry.happiness_score)
            self.assertEqual(entry.meal_type, 'dinner')

    def test_generate_plan_multiple_meals(self):
        """Test generating plan with multiple meals per day"""
        plan = MealPlanningAssistantService.generate_weekly_plan(
            user=self.user,
            meals_per_day=['breakfast', 'dinner']
        )

        # Should have 14 entries (7 days * 2 meals)
        self.assertEqual(plan.entries.count(), 14)

    def test_approve_plan(self):
        """Test approving a generated plan"""
        plan = MealPlanningAssistantService.generate_weekly_plan(
            user=self.user,
            meals_per_day=['dinner']
        )

        self.assertFalse(plan.approved)

        # Approve the plan
        MealPlanningAssistantService.approve_plan(plan)

        plan.refresh_from_db()
        self.assertTrue(plan.approved)
        self.assertIsNotNone(plan.approved_at)

        # Should have created actual meal plans
        meal_plans = MealPlan.objects.filter(user=self.user)
        self.assertEqual(meal_plans.count(), 7)

    def test_regenerate_single_meal(self):
        """Test regenerating a single meal in the plan"""
        plan = MealPlanningAssistantService.generate_weekly_plan(
            user=self.user,
            meals_per_day=['dinner']
        )

        # Get first entry
        entry = plan.entries.first()
        original_recipe = entry.recipe

        # Regenerate
        updated_entry = MealPlanningAssistantService.regenerate_single_meal(plan, entry)

        # Recipe might be different (if alternatives available)
        self.assertIsNotNone(updated_entry.recipe)


class MealPlannerViewsTest(TestCase):
    """Test the meal planner views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')

        # Create a test recipe
        self.recipe = Recipe.objects.create(
            user=self.user,
            title='Test Recipe',
            ingredients='Test ingredients',
            steps='Test steps'
        )

    def test_meal_planner_preferences_view_get(self):
        """Test GET request to preferences view"""
        response = self.client.get(reverse('meal_planner_preferences'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Meal Planner Preferences')

    def test_meal_planner_preferences_view_post(self):
        """Test POST request to update preferences"""
        data = {
            'max_weeknight_time': 30,
            'max_weekend_time': 60,
            'avoid_repeat_days': 7,
            'variety_score': 8,
            'vegetarian_meals_per_week': 2,
            'use_leftovers': True,
            'batch_cooking_friendly': False,
        }
        response = self.client.post(reverse('meal_planner_preferences'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after success

        # Check preferences were saved
        prefs = MealPlannerPreferences.objects.get(user=self.user)
        self.assertEqual(prefs.max_weeknight_time, 30)
        self.assertEqual(prefs.variety_score, 8)

    def test_smart_meal_planner_view_get(self):
        """Test GET request to smart planner view"""
        response = self.client.get(reverse('smart_meal_planner'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Smart Weekly Meal Planner')

    def test_smart_meal_planner_view_post(self):
        """Test POST request to generate plan"""
        tomorrow = date.today() + timedelta(days=1)
        data = {
            'week_start': tomorrow.strftime('%Y-%m-%d'),
            'meals_to_plan': ['dinner']
        }
        response = self.client.post(reverse('smart_meal_planner'), data)

        # Should redirect to review page
        self.assertEqual(response.status_code, 302)

        # Should have created a plan
        plan = GeneratedMealPlan.objects.filter(user=self.user).first()
        self.assertIsNotNone(plan)

    def test_review_meal_plan_view(self):
        """Test reviewing a generated plan"""
        plan = MealPlanningAssistantService.generate_weekly_plan(
            user=self.user,
            meals_per_day=['dinner']
        )

        response = self.client.get(reverse('review_meal_plan', args=[plan.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Review Your Meal Plan')

    def test_approve_meal_plan_view(self):
        """Test approving a meal plan"""
        plan = MealPlanningAssistantService.generate_weekly_plan(
            user=self.user,
            meals_per_day=['dinner']
        )

        response = self.client.post(reverse('approve_meal_plan', args=[plan.id]))
        self.assertEqual(response.status_code, 302)

        # Plan should be approved
        plan.refresh_from_db()
        self.assertTrue(plan.approved)

    def test_regenerate_meal_view(self):
        """Test regenerating a single meal"""
        plan = MealPlanningAssistantService.generate_weekly_plan(
            user=self.user,
            meals_per_day=['dinner']
        )

        entry = plan.entries.first()
        response = self.client.post(reverse('regenerate_meal', args=[entry.id]))

        self.assertEqual(response.status_code, 302)

    def test_delete_generated_plan_view(self):
        """Test deleting a generated plan"""
        plan = MealPlanningAssistantService.generate_weekly_plan(
            user=self.user,
            meals_per_day=['dinner']
        )

        response = self.client.post(reverse('delete_generated_plan', args=[plan.id]))
        self.assertEqual(response.status_code, 302)

        # Plan should be deleted
        self.assertFalse(GeneratedMealPlan.objects.filter(id=plan.id).exists())

    def test_unauthenticated_access(self):
        """Test that unauthenticated users are redirected"""
        self.client.logout()

        response = self.client.get(reverse('smart_meal_planner'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
