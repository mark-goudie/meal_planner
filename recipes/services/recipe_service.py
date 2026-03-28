"""
Recipe Service - Business logic for recipe management.

This service encapsulates all recipe-related operations including:
- Recipe creation, updating, deletion
- Recipe filtering and search
- Favourites management
- Shopping list generation
"""

from decimal import Decimal
from typing import List, Optional, Set

from django.contrib.auth.models import User
from django.db.models import Q, QuerySet

from ..models import Recipe, Tag


class RecipeService:
    """Service for managing recipe operations."""

    @staticmethod
    def get_recipes_for_user(
        user: User,
        query: Optional[str] = None,
        tag_id: Optional[int] = None,
        favourites_only: bool = False,
        **kwargs,
    ) -> QuerySet:
        """
        Get recipes for a user with optional filters.

        Args:
            user: The user whose recipes to retrieve
            query: Search query for title/ingredients
            tag_id: Filter by tag ID
            favourites_only: Show only favourited recipes

        Returns:
            QuerySet of Recipe objects with optimized queries
        """
        recipes = Recipe.objects.filter(user=user)

        # Apply search filter
        if query:
            recipes = recipes.filter(Q(title__icontains=query) | Q(ingredients_text__icontains=query))

        # Apply tag filter
        if tag_id:
            recipes = recipes.filter(tags__id=tag_id)

        # Apply favourites filter
        if favourites_only:
            recipes = recipes.filter(favourited_by=user)

        # Optimize queries
        recipes = (
            recipes.distinct().select_related("user").prefetch_related("tags", "favourited_by").order_by("-created_at")
        )

        return recipes

    @staticmethod
    def create_recipe(user: User, recipe_data: dict) -> Recipe:
        """
        Create a new recipe for a user.

        Args:
            user: The user creating the recipe
            recipe_data: Dictionary containing recipe fields

        Returns:
            The created Recipe instance
        """
        tags = recipe_data.pop("tags", [])
        recipe = Recipe.objects.create(user=user, **recipe_data)
        if tags:
            recipe.tags.set(tags)
        return recipe

    @staticmethod
    def update_recipe(recipe: Recipe, recipe_data: dict) -> Recipe:
        """
        Update an existing recipe.

        Args:
            recipe: The recipe to update
            recipe_data: Dictionary containing updated fields

        Returns:
            The updated Recipe instance
        """
        tags = recipe_data.pop("tags", None)
        for key, value in recipe_data.items():
            setattr(recipe, key, value)
        recipe.save()
        if tags is not None:
            recipe.tags.set(tags)
        return recipe

    @staticmethod
    def delete_recipe(recipe: Recipe) -> None:
        """Delete a recipe."""
        recipe.delete()

    @staticmethod
    def toggle_favourite(user: User, recipe: Recipe) -> bool:
        """
        Toggle favourite status for a recipe.

        Args:
            user: The user toggling the favourite
            recipe: The recipe to toggle

        Returns:
            True if recipe is now favourited, False otherwise
        """
        if user in recipe.favourited_by.all():
            recipe.favourited_by.remove(user)
            return False
        else:
            recipe.favourited_by.add(user)
            return True

    @staticmethod
    def generate_shopping_list(user: User, recipe_ids: List[int]) -> List[str]:
        """
        Generate a deduplicated shopping list from multiple recipes.

        Args:
            user: The user generating the list
            recipe_ids: List of recipe IDs to include

        Returns:
            Sorted list of unique ingredients
        """
        recipes = Recipe.objects.filter(id__in=recipe_ids, user=user)
        ingredient_set: Set[str] = set()

        for recipe in recipes:
            if recipe.ingredients_text:
                for line in recipe.ingredients_text.splitlines():
                    line = line.strip()
                    if line:
                        ingredient_set.add(line)

        return sorted(ingredient_set)

    @staticmethod
    def get_all_tags() -> QuerySet:
        """Get all available tags."""
        return Tag.objects.all()

    @staticmethod
    def generate_structured_shopping_list(recipes):
        """Generate a shopping list with summed quantities from structured ingredients."""
        from collections import defaultdict

        aggregated = defaultdict(
            lambda: {
                "ingredient": None,
                "category": "",
                "total_quantity": Decimal("0"),
                "unit": "",
                "recipes": set(),
            }
        )

        for recipe in recipes:
            for ri in recipe.recipe_ingredients.select_related("ingredient").all():
                key = (ri.ingredient_id, ri.unit)
                entry = aggregated[key]
                entry["ingredient"] = ri.ingredient
                entry["category"] = ri.ingredient.category
                if ri.quantity:
                    entry["total_quantity"] += ri.quantity
                entry["unit"] = ri.unit
                entry["recipes"].add(recipe.title)

        return sorted(aggregated.values(), key=lambda x: (x["category"], x["ingredient"].name))
