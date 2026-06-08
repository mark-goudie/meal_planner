from datetime import date

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from recipes.models import CookingNote, MealPlan, Recipe
from recipes.models.household import Household, HouseholdMembership


class TonightViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="t", password="pw")
        self.household = Household.objects.create(name="Home")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.recipe = Recipe.objects.create(
            user=self.user, title="Spaghetti Carbonara", steps="Cook.", cook_time=20
        )
        self.client.login(username="t", password="pw")

    def test_home_renders_tonight(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tonight/tonight.html")

    def test_planned_tonight_shows_meal_and_start_cooking(self):
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today(),
            meal_type="dinner",
            recipe=self.recipe,
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Spaghetti Carbonara")
        self.assertContains(response, "Start Cooking")

    def test_empty_tonight_shows_suggestion_with_reason(self):
        # No meal planned today -> a confirm-or-swap suggestion should appear.
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Spaghetti Carbonara")
        self.assertContains(response, "plan tonight")  # accept button label

    def test_memory_cue_shows_last_note(self):
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today(),
            meal_type="dinner",
            recipe=self.recipe,
        )
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date.today(),
            rating=5,
            note="halve the chilli",
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, "halve the chilli")

    def test_no_recipes_shows_add_cta(self):
        Recipe.objects.all().delete()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add your first recipe")

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)
