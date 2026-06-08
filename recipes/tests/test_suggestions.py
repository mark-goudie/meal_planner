from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from recipes.models import CookingNote, Recipe
from recipes.models.household import Household, HouseholdMembership
from recipes.services.suggestions import SuggestionService


class RankForSlotTests(TestCase):
    def setUp(self):
        self.hh = Household.objects.create(name="Home")
        self.u = User.objects.create_user(username="u", password="x")
        HouseholdMembership.objects.create(user=self.u, household=self.hh)
        self.high = Recipe.objects.create(
            user=self.u, title="High", steps="x", cook_time=20
        )
        self.low = Recipe.objects.create(
            user=self.u, title="Low", steps="x", cook_time=20
        )
        # Cooked 30 days ago (outside the 14-day avoid window), so both are eligible.
        CookingNote.objects.create(
            recipe=self.high,
            user=self.u,
            cooked_date=date.today() - timedelta(days=30),
            rating=5,
        )
        CookingNote.objects.create(
            recipe=self.low,
            user=self.u,
            cooked_date=date.today() - timedelta(days=30),
            rating=1,
        )

    def test_top_pick_is_highest_scored(self):
        ranked = SuggestionService.rank_for_slot(self.hh, self.u, date.today())
        self.assertEqual(ranked[0]["recipe"], self.high)

    def test_exclude_ids_skips_recipe(self):
        ranked = SuggestionService.rank_for_slot(
            self.hh, self.u, date.today(), exclude_ids=[self.high.id]
        )
        self.assertNotIn(self.high, [r["recipe"] for r in ranked])

    def test_each_suggestion_has_reasons(self):
        ranked = SuggestionService.rank_for_slot(self.hh, self.u, date.today())
        self.assertTrue(ranked[0]["reasons"])
        self.assertIn("text", ranked[0]["reasons"][0])

    def test_empty_when_no_recipes(self):
        Recipe.objects.all().delete()
        self.assertEqual(
            SuggestionService.rank_for_slot(self.hh, self.u, date.today()), []
        )


class BuildReasonsTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="r", password="x")
        self.recipe = Recipe.objects.create(
            user=self.u, title="X", steps="x", cook_time=25
        )

    def test_never_tried_recipe_reason(self):
        from recipes.services.meal_planning_assistant import (
            MealPlanningAssistantService,
        )

        prefs = MealPlanningAssistantService.get_or_create_preferences(self.u)
        reasons = SuggestionService.build_reasons(
            self.recipe, date.today(), prefs, self.u
        )
        texts = [r["text"] for r in reasons]
        self.assertIn("Never tried", texts)

    def test_time_reason_present(self):
        from recipes.services.meal_planning_assistant import (
            MealPlanningAssistantService,
        )

        prefs = MealPlanningAssistantService.get_or_create_preferences(self.u)
        reasons = SuggestionService.build_reasons(
            self.recipe, date.today(), prefs, self.u
        )
        texts = [r["text"] for r in reasons]
        self.assertIn("25 min", texts)
