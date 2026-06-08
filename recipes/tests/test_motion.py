from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from recipes.models import Recipe
from recipes.models.household import Household, HouseholdMembership


class MotionAttributeTests(TestCase):
    """Regression: the View Transition hx modifiers must stay on the daily swaps."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="m", password="pw")
        self.household = Household.objects.create(name="Home")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Stir Fry",
            steps="Chop veg.\nHeat wok.\nToss and serve.",
            cook_time=15,
        )
        self.client.login(username="m", password="pw")

    def test_tonight_hero_swaps_use_transition(self):
        # No dinner today -> confirm-or-swap hero whose swaps use transition:true.
        response = self.client.get(reverse("home"))
        self.assertContains(response, "transition:true")

    def test_recipe_search_input_uses_transition(self):
        response = self.client.get(reverse("recipe_list"))
        self.assertContains(response, "transition:true")

    def test_week_nav_uses_directional_transition(self):
        response = self.client.get(reverse("week"))
        self.assertContains(response, "transition:true")
        self.assertContains(response, 'data-vt-dir="back"')
        self.assertContains(response, 'data-vt-dir="forward"')

    def test_cook_step_uses_directional_transition(self):
        response = self.client.get(reverse("cook", args=[self.recipe.pk]))
        self.assertContains(response, "transition:true")
        self.assertContains(response, "data-vt-dir")
