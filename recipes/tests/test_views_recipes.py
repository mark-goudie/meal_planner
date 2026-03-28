from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from recipes.models import (
    CookingNote,
    Ingredient,
    Recipe,
    RecipeIngredient,
    Tag,
)


class RecipeListViewTest(TestCase):
    """Tests for the recipe list view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Spaghetti Carbonara",
            steps="Cook pasta.",
            cook_time=30,
            servings=4,
            difficulty="medium",
        )
        self.client.login(username="testuser", password="testpass123")

    def test_recipe_list_returns_200(self):
        """Recipe list should return 200 for authenticated users."""
        response = self.client.get(reverse("recipe_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "recipes/list.html")

    def test_recipe_list_shows_user_recipes(self):
        """Recipe list should show the user's recipes."""
        response = self.client.get(reverse("recipe_list"))
        self.assertContains(response, "Spaghetti Carbonara")

    def test_recipe_list_does_not_show_other_user_recipes(self):
        """Recipe list should not show recipes from other users."""
        other_user = User.objects.create_user(username="otheruser", password="testpass123")
        Recipe.objects.create(
            user=other_user,
            title="Secret Recipe",
            steps="Hidden.",
        )
        response = self.client.get(reverse("recipe_list"))
        self.assertNotContains(response, "Secret Recipe")

    def test_recipe_list_requires_login(self):
        """Unauthenticated users should be redirected to login."""
        self.client.logout()
        response = self.client.get(reverse("recipe_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_recipe_list_pagination(self):
        """Recipe list should paginate results."""
        for i in range(15):
            Recipe.objects.create(
                user=self.user,
                title=f"Recipe {i}",
                steps="Steps.",
            )
        response = self.client.get(reverse("recipe_list"))
        self.assertEqual(response.status_code, 200)
        # Should have pagination (12 per page, 16 total)
        self.assertEqual(len(response.context["recipes"]), 12)

    def test_recipe_list_sort_newest(self):
        """Sort by newest should be default."""
        response = self.client.get(reverse("recipe_list"))
        self.assertEqual(response.context["sort"], "newest")


class RecipeSearchViewTest(TestCase):
    """Tests for the HTMX recipe search endpoint."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.recipe1 = Recipe.objects.create(
            user=self.user,
            title="Thai Green Curry",
            steps="Cook curry.",
        )
        self.recipe2 = Recipe.objects.create(
            user=self.user,
            title="Spaghetti Carbonara",
            steps="Cook pasta.",
        )
        self.client.login(username="testuser", password="testpass123")

    def test_search_returns_partial(self):
        """Search should return the search results partial template."""
        response = self.client.get(reverse("recipe_search"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "recipes/partials/search_results.html")

    def test_search_filters_by_query(self):
        """Search with ?q= should filter recipes by title."""
        response = self.client.get(reverse("recipe_search") + "?q=Thai")
        self.assertContains(response, "Thai Green Curry")
        self.assertNotContains(response, "Spaghetti Carbonara")

    def test_search_filters_by_tag(self):
        """Search with ?tag= should filter recipes by tag."""
        tag = Tag.objects.create(name="Italian", tag_type="cuisine")
        self.recipe2.tags.add(tag)

        response = self.client.get(reverse("recipe_search") + f"?tag={tag.pk}")
        self.assertContains(response, "Spaghetti Carbonara")
        self.assertNotContains(response, "Thai Green Curry")

    def test_search_favourites_filter(self):
        """Search with ?favourites=1 should only show favourited recipes."""
        self.recipe1.favourited_by.add(self.user)

        response = self.client.get(reverse("recipe_search") + "?favourites=1")
        self.assertContains(response, "Thai Green Curry")
        self.assertNotContains(response, "Spaghetti Carbonara")

    def test_search_sort_rating(self):
        """Search with ?sort=rating should order by rating."""
        CookingNote.objects.create(
            recipe=self.recipe1,
            user=self.user,
            cooked_date=date.today(),
            rating=5,
        )
        CookingNote.objects.create(
            recipe=self.recipe2,
            user=self.user,
            cooked_date=date.today(),
            rating=2,
        )
        response = self.client.get(reverse("recipe_search") + "?sort=rating")
        self.assertEqual(response.status_code, 200)
        recipes = list(response.context["recipes"])
        self.assertEqual(recipes[0].title, "Thai Green Curry")

    def test_search_requires_login(self):
        """Unauthenticated users should be redirected."""
        self.client.logout()
        response = self.client.get(reverse("recipe_search"))
        self.assertEqual(response.status_code, 302)


class RecipeDetailViewTest(TestCase):
    """Tests for the recipe detail view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Spaghetti Carbonara",
            description="Classic Italian pasta.",
            steps="Cook pasta.\nMake sauce.\nCombine.",
            cook_time=30,
            servings=4,
        )
        self.client.login(username="testuser", password="testpass123")

    def test_detail_returns_200(self):
        """Recipe detail should return 200."""
        response = self.client.get(reverse("recipe_detail", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "recipes/detail.html")

    def test_detail_shows_recipe_info(self):
        """Recipe detail should show title, description, steps."""
        response = self.client.get(reverse("recipe_detail", args=[self.recipe.pk]))
        self.assertContains(response, "Spaghetti Carbonara")
        self.assertContains(response, "Classic Italian pasta.")
        self.assertContains(response, "Cook pasta.")

    def test_detail_shows_structured_ingredients(self):
        """Recipe detail should show structured ingredients."""
        ingredient = Ingredient.objects.create(name="pasta", category="pantry")
        RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=ingredient,
            quantity=Decimal("400"),
            unit="g",
            order=0,
        )
        response = self.client.get(reverse("recipe_detail", args=[self.recipe.pk]))
        self.assertContains(response, "pasta")
        self.assertContains(response, "400")

    def test_detail_shows_cooking_notes(self):
        """Recipe detail should show cooking notes."""
        CookingNote.objects.create(
            recipe=self.recipe,
            user=self.user,
            cooked_date=date.today(),
            rating=4,
            note="Turned out great!",
        )
        response = self.client.get(reverse("recipe_detail", args=[self.recipe.pk]))
        self.assertContains(response, "Turned out great!")

    def test_detail_only_accessible_to_owner(self):
        """Recipe detail should return 404 for non-owners."""
        User.objects.create_user(username="otheruser", password="testpass123")
        self.client.login(username="otheruser", password="testpass123")
        response = self.client.get(reverse("recipe_detail", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 404)

    def test_detail_shows_favourite_button(self):
        """Recipe detail should show the favourite toggle button."""
        response = self.client.get(reverse("recipe_detail", args=[self.recipe.pk]))
        self.assertContains(response, "favourite")

    def test_detail_shows_edit_delete_buttons(self):
        """Recipe detail should show edit and delete links for owner."""
        response = self.client.get(reverse("recipe_detail", args=[self.recipe.pk]))
        self.assertContains(response, "Edit")
        self.assertContains(response, "Delete")

    def test_detail_falls_back_to_ingredients_text(self):
        """When no structured ingredients, should show ingredients_text."""
        self.recipe.ingredients_text = "400g pasta\n200g guanciale"
        self.recipe.save()
        response = self.client.get(reverse("recipe_detail", args=[self.recipe.pk]))
        self.assertContains(response, "400g pasta")


class RecipeCreateViewTest(TestCase):
    """Tests for the recipe create view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.login(username="testuser", password="testpass123")

    def test_create_get_returns_200(self):
        """GET to create should return the form."""
        response = self.client.get(reverse("recipe_create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "recipes/form.html")

    def test_create_recipe(self):
        """POST should create a recipe and redirect to detail."""
        response = self.client.post(
            reverse("recipe_create"),
            {
                "title": "New Recipe",
                "steps": "Step 1.\nStep 2.",
                "servings": "4",
                "difficulty": "easy",
                "ingredient_count": "0",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Recipe.objects.filter(title="New Recipe", user=self.user).exists())

    def test_create_recipe_with_structured_ingredients(self):
        """POST with ingredient fields should create RecipeIngredients."""
        response = self.client.post(
            reverse("recipe_create"),
            {
                "title": "Recipe With Ingredients",
                "steps": "Cook it.",
                "servings": "4",
                "difficulty": "medium",
                "ingredient_count": "2",
                "ing_name_0": "Chicken",
                "ing_qty_0": "500",
                "ing_unit_0": "g",
                "ing_notes_0": "diced",
                "ing_name_1": "Onion",
                "ing_qty_1": "2",
                "ing_unit_1": "piece",
                "ing_notes_1": "chopped",
            },
        )
        self.assertEqual(response.status_code, 302)
        recipe = Recipe.objects.get(title="Recipe With Ingredients")
        self.assertEqual(recipe.recipe_ingredients.count(), 2)

        chicken_ri = recipe.recipe_ingredients.get(ingredient__name="chicken")
        self.assertEqual(chicken_ri.quantity, Decimal("500"))
        self.assertEqual(chicken_ri.unit, "g")
        self.assertEqual(chicken_ri.preparation_notes, "diced")

    def test_create_recipe_empty_title_shows_error(self):
        """POST with empty title should show error."""
        response = self.client.post(
            reverse("recipe_create"),
            {
                "title": "",
                "steps": "Step 1.",
                "ingredient_count": "0",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Title is required")

    def test_create_requires_login(self):
        """Unauthenticated users should be redirected."""
        self.client.logout()
        response = self.client.get(reverse("recipe_create"))
        self.assertEqual(response.status_code, 302)

    def test_create_with_tags(self):
        """POST with tags should associate tags with recipe."""
        tag = Tag.objects.create(name="Italian", tag_type="cuisine")
        response = self.client.post(
            reverse("recipe_create"),
            {
                "title": "Tagged Recipe",
                "steps": "Steps.",
                "servings": "4",
                "difficulty": "easy",
                "ingredient_count": "0",
                "tags": [str(tag.pk)],
            },
        )
        self.assertEqual(response.status_code, 302)
        recipe = Recipe.objects.get(title="Tagged Recipe")
        self.assertIn(tag, recipe.tags.all())


class RecipeUpdateViewTest(TestCase):
    """Tests for the recipe update view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Original Title",
            steps="Original steps.",
            servings=4,
        )
        self.client.login(username="testuser", password="testpass123")

    def test_update_get_returns_200(self):
        """GET to update should return the form with existing data."""
        response = self.client.get(reverse("recipe_update", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "recipes/form.html")
        self.assertContains(response, "Original Title")

    def test_update_modifies_recipe(self):
        """POST should update the recipe."""
        response = self.client.post(
            reverse("recipe_update", args=[self.recipe.pk]),
            {
                "title": "Updated Title",
                "steps": "Updated steps.",
                "servings": "6",
                "difficulty": "hard",
                "ingredient_count": "0",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.title, "Updated Title")
        self.assertEqual(self.recipe.servings, 6)

    def test_update_only_by_owner(self):
        """Other users should not be able to update the recipe."""
        User.objects.create_user(username="otheruser", password="testpass123")
        self.client.login(username="otheruser", password="testpass123")
        response = self.client.get(reverse("recipe_update", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 404)

    def test_update_structured_ingredients(self):
        """POST should update structured ingredients."""
        # Create initial ingredient
        ingredient = Ingredient.objects.create(name="old item", category="other")
        RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=ingredient,
            quantity=Decimal("100"),
            unit="g",
            order=0,
        )
        response = self.client.post(
            reverse("recipe_update", args=[self.recipe.pk]),
            {
                "title": "Updated Recipe",
                "steps": "Updated.",
                "servings": "4",
                "difficulty": "medium",
                "ingredient_count": "1",
                "ing_name_0": "New Item",
                "ing_qty_0": "200",
                "ing_unit_0": "ml",
                "ing_notes_0": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.recipe.refresh_from_db()
        # Old ingredient removed, new one added
        self.assertEqual(self.recipe.recipe_ingredients.count(), 1)
        ri = self.recipe.recipe_ingredients.first()
        self.assertEqual(ri.ingredient.name, "new item")
        self.assertEqual(ri.quantity, Decimal("200"))


class RecipeDeleteViewTest(TestCase):
    """Tests for the recipe delete view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="To Delete",
            steps="Steps.",
        )
        self.client.login(username="testuser", password="testpass123")

    def test_delete_get_shows_confirmation(self):
        """GET to delete should show confirmation page."""
        response = self.client.get(reverse("recipe_delete", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "recipes/confirm_delete.html")
        self.assertContains(response, "To Delete")

    def test_delete_post_removes_recipe(self):
        """POST to delete should remove the recipe and redirect."""
        response = self.client.post(reverse("recipe_delete", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Recipe.objects.filter(pk=self.recipe.pk).exists())

    def test_delete_only_by_owner(self):
        """Other users should not be able to delete the recipe."""
        User.objects.create_user(username="otheruser", password="testpass123")
        self.client.login(username="otheruser", password="testpass123")
        response = self.client.post(reverse("recipe_delete", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 404)
        # Recipe should still exist
        self.assertTrue(Recipe.objects.filter(pk=self.recipe.pk).exists())


class ToggleFavouriteViewTest(TestCase):
    """Tests for the toggle favourite HTMX endpoint."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Favourite Test",
            steps="Steps.",
        )
        self.client.login(username="testuser", password="testpass123")

    def test_toggle_adds_favourite(self):
        """POST should add recipe to favourites."""
        response = self.client.post(reverse("toggle_favourite", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.user, self.recipe.favourited_by.all())

    def test_toggle_removes_favourite(self):
        """POST again should remove recipe from favourites."""
        self.recipe.favourited_by.add(self.user)

        response = self.client.post(reverse("toggle_favourite", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.user, self.recipe.favourited_by.all())

    def test_toggle_returns_partial(self):
        """POST should return the favourite button partial."""
        response = self.client.post(reverse("toggle_favourite", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "recipes/partials/favourite_button.html")

    def test_toggle_only_for_own_recipe(self):
        """Should return 404 for recipes not owned by the user."""
        other_user = User.objects.create_user(username="otheruser", password="testpass123")
        other_recipe = Recipe.objects.create(
            user=other_user,
            title="Not Mine",
            steps="Steps.",
        )
        response = self.client.post(reverse("toggle_favourite", args=[other_recipe.pk]))
        self.assertEqual(response.status_code, 404)

    def test_toggle_requires_login(self):
        """Unauthenticated users should be redirected."""
        self.client.logout()
        response = self.client.post(reverse("toggle_favourite", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 302)
