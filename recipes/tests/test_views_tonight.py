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
        # No meal planned today -> a confirm-or-swap suggestion should appear,
        # including at least one reason chip (e.g. "Never tried" for an uncooked recipe).
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Spaghetti Carbonara")
        self.assertContains(response, "plan tonight")  # accept button label
        self.assertContains(
            response, "Never tried"
        )  # reason chip for an uncooked recipe

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


class TonightSwapTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="swap_u", password="pw")
        self.household = Household.objects.create(name="Home")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.recipe = Recipe.objects.create(
            user=self.user, title="Pasta", steps="Cook.", cook_time=20
        )
        self.client.login(username="swap_u", password="pw")

    def test_swap_returns_hero_empty_partial(self):
        response = self.client.get(reverse("tonight_swap"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tonight/partials/hero_empty.html")

    def test_swap_excludes_specified_ids(self):
        Recipe.objects.create(
            user=self.user, title="Burger", steps="Grill.", cook_time=15
        )
        # Exclude the first recipe so only "Burger" can be suggested.
        response = self.client.get(
            reverse("tonight_swap") + f"?exclude={self.recipe.pk}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Burger")
        self.assertNotContains(response, "Pasta")

    def test_swap_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("tonight_swap"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)


class TonightAcceptTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="accept_u", password="pw")
        self.household = Household.objects.create(name="Home")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.recipe = Recipe.objects.create(
            user=self.user, title="Risotto", steps="Stir.", cook_time=30
        )
        self.client.login(username="accept_u", password="pw")

    def test_accept_creates_meal_plan_for_tonight(self):
        response = self.client.post(
            reverse("tonight_accept"), {"recipe_id": self.recipe.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            MealPlan.objects.filter(
                household=self.household,
                date=date.today(),
                meal_type="dinner",
                recipe=self.recipe,
            ).exists()
        )

    def test_accept_returns_hero_planned_partial(self):
        response = self.client.post(
            reverse("tonight_accept"), {"recipe_id": self.recipe.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tonight/partials/hero_planned.html")

    def test_accept_contains_recipe_title(self):
        response = self.client.post(
            reverse("tonight_accept"), {"recipe_id": self.recipe.pk}
        )
        self.assertContains(response, "Risotto")

    def test_accept_requires_login(self):
        self.client.logout()
        response = self.client.post(
            reverse("tonight_accept"), {"recipe_id": self.recipe.pk}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_accept_rejects_inaccessible_recipe(self):
        other_user = User.objects.create_user(username="other_accept", password="pw")
        private_recipe = Recipe.objects.create(
            user=other_user, title="Secret", steps="Shh.", shared=False
        )
        response = self.client.post(
            reverse("tonight_accept"), {"recipe_id": private_recipe.pk}
        )
        self.assertEqual(response.status_code, 404)
