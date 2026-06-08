from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from recipes.models import CookingNote, Recipe
from recipes.models.household import Household, HouseholdMembership
from recipes.services.meal_planning_assistant import MealPlanningAssistantService as S


class HouseholdScoringTests(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Home")
        self.alice = User.objects.create_user(username="alice", password="x")
        self.bob = User.objects.create_user(username="bob", password="x")
        HouseholdMembership.objects.create(user=self.alice, household=self.household)
        HouseholdMembership.objects.create(user=self.bob, household=self.household)
        self.recipe = Recipe.objects.create(
            user=self.alice, title="Curry", steps="Cook."
        )

    def test_partner_rating_counts_toward_happiness_score(self):
        # Bob rates 5 stars; Alice has no notes. Household-wide score = 100.
        CookingNote.objects.create(
            recipe=self.recipe, user=self.bob, cooked_date=date.today(), rating=5
        )
        score = S.calculate_recipe_happiness_score(self.recipe, self.alice)
        self.assertEqual(score, Decimal("100.0"))

    def test_partner_recent_cook_excludes_recipe_for_household(self):
        CookingNote.objects.create(
            recipe=self.recipe, user=self.bob, cooked_date=date.today()
        )
        recent = S.get_recently_cooked_recipes(self.alice, days=14)
        self.assertIn(self.recipe.id, recent)

    def test_solo_user_without_household_unaffected(self):
        solo = User.objects.create_user(username="solo", password="x")
        r = Recipe.objects.create(user=solo, title="Solo", steps="x")
        CookingNote.objects.create(
            recipe=r, user=solo, cooked_date=date.today(), rating=4
        )
        self.assertEqual(S.calculate_recipe_happiness_score(r, solo), Decimal("75.0"))
