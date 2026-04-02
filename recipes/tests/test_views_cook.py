from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from recipes.models import (
    CookingNote,
    Ingredient,
    Recipe,
    RecipeIngredient,
)


class CookViewTest(TestCase):
    """Tests for cooking mode views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", password="testpass123"
        )
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Pasta Carbonara",
            steps="Boil water and cook pasta.\nFry guanciale.\nMix eggs and cheese.\nCombine everything.",
            cook_time=25,
        )
        self.client.login(username="testuser", password="testpass123")

    def test_cook_view_returns_200_for_owner(self):
        """Cooking mode should return 200 for the recipe owner."""
        response = self.client.get(reverse("cook", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "cook/cook.html")

    def test_cook_view_returns_404_for_other_user(self):
        """Cooking mode should return 404 for a non-owner."""
        self.client.login(username="otheruser", password="testpass123")
        response = self.client.get(reverse("cook", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 404)

    def test_cook_view_requires_login(self):
        """Cooking mode should redirect unauthenticated users to login."""
        self.client.logout()
        response = self.client.get(reverse("cook", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_cook_view_shows_recipe_title(self):
        """Cooking mode should display the recipe title."""
        response = self.client.get(reverse("cook", args=[self.recipe.pk]))
        self.assertContains(response, "Pasta Carbonara")

    def test_cook_view_has_total_steps(self):
        """Context should include total step count."""
        response = self.client.get(reverse("cook", args=[self.recipe.pk]))
        self.assertEqual(response.context["total_steps"], 4)

    def test_cook_step_returns_step_content(self):
        """cook_step should return the correct step content."""
        response = self.client.get(reverse("cook_step", args=[self.recipe.pk, 2]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fry guanciale")
        self.assertTemplateUsed(response, "cook/partials/step.html")

    def test_cook_step_zero_returns_404(self):
        """Step 0 should return 404."""
        response = self.client.get(reverse("cook_step", args=[self.recipe.pk, 0]))
        self.assertEqual(response.status_code, 404)

    def test_cook_step_beyond_total_returns_404(self):
        """Step beyond total should return 404."""
        response = self.client.get(reverse("cook_step", args=[self.recipe.pk, 99]))
        self.assertEqual(response.status_code, 404)

    def test_cook_done_get_renders_form(self):
        """GET to cook_done should render the rating form."""
        response = self.client.get(reverse("cook_done", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "rating")
        self.assertTemplateUsed(response, "cook/partials/done.html")

    def test_cook_done_post_creates_cooking_note(self):
        """POST to cook_done should create a CookingNote and redirect."""
        response = self.client.post(
            reverse("cook_done", args=[self.recipe.pk]),
            data={
                "rating": "4",
                "note": "Came out great!",
                "would_make_again": "1",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse("recipe_detail", args=[self.recipe.pk]),
            response.url,
        )
        note = CookingNote.objects.get(recipe=self.recipe, user=self.user)
        self.assertEqual(note.rating, 4)
        self.assertEqual(note.note, "Came out great!")
        self.assertTrue(note.would_make_again)

    def test_cook_done_post_without_would_make_again(self):
        """POST without would_make_again checkbox sets it to False."""
        self.client.post(
            reverse("cook_done", args=[self.recipe.pk]),
            data={
                "rating": "3",
                "note": "Okay",
            },
        )
        note = CookingNote.objects.get(recipe=self.recipe, user=self.user)
        self.assertFalse(note.would_make_again)

    def test_cook_step_shows_ingredients_on_step_1(self):
        """Step 1 should show all ingredients (plain text fallback)."""
        ingredient = Ingredient.objects.create(name="spaghetti", category="pantry")
        RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=ingredient,
            quantity=200,
            unit="g",
            order=0,
        )
        response = self.client.get(reverse("cook_step", args=[self.recipe.pk, 1]))
        self.assertContains(response, "spaghetti")

    def test_cook_step_no_ingredients_on_step_2(self):
        """Step 2+ should not show ingredients (plain text fallback)."""
        ingredient = Ingredient.objects.create(name="spaghetti", category="pantry")
        RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=ingredient,
            quantity=200,
            unit="g",
            order=0,
        )
        response = self.client.get(reverse("cook_step", args=[self.recipe.pk, 2]))
        self.assertNotContains(response, "cook-ingredient-card")


class CookViewWithStructuredStepsTest(TestCase):
    """Tests for cooking mode with cooking_mode_steps JSON."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.ingredient1 = Ingredient.objects.create(name="pasta", category="pantry")
        self.ingredient2 = Ingredient.objects.create(name="eggs", category="dairy")

        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Structured Pasta",
            steps="Step 1\nStep 2",
            cook_time=20,
        )
        self.ri1 = RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient1,
            quantity=200,
            unit="g",
            order=0,
        )
        self.ri2 = RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient2,
            quantity=2,
            unit="piece",
            order=1,
        )
        self.recipe.cooking_mode_steps = [
            {"text": "Cook the pasta", "ingredient_ids": [self.ri1.pk]},
            {"text": "Add the eggs", "ingredient_ids": [self.ri2.pk]},
        ]
        self.recipe.save()
        self.client.login(username="testuser", password="testpass123")

    def test_structured_steps_used(self):
        """Cooking mode should use cooking_mode_steps when available."""
        response = self.client.get(reverse("cook", args=[self.recipe.pk]))
        self.assertEqual(response.context["total_steps"], 2)
        self.assertContains(response, "Cook the pasta")

    def test_structured_step_shows_relevant_ingredients(self):
        """Each step should show only its relevant ingredients."""
        response = self.client.get(reverse("cook_step", args=[self.recipe.pk, 1]))
        self.assertContains(response, "pasta")
        self.assertNotContains(response, "eggs")

        response2 = self.client.get(reverse("cook_step", args=[self.recipe.pk, 2]))
        self.assertContains(response2, "eggs")
