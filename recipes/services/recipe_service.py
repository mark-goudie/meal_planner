"""
Recipe Service - Business logic for recipe management.

This service encapsulates all recipe-related operations including:
- Recipe creation, updating, deletion
- Recipe filtering and search
- Family preferences
- Favourites management
- Shopping list generation
"""

from typing import List, Optional, Set
from django.db.models import Q, Count, QuerySet
from django.contrib.auth.models import User

from ..models import Recipe, FamilyPreference, Tag


class RecipeService:
    """Service for managing recipe operations."""

    @staticmethod
    def get_recipes_for_user(
        user: User,
        query: Optional[str] = None,
        tag_id: Optional[int] = None,
        selected_members: Optional[List[str]] = None,
        favourites_only: bool = False
    ) -> QuerySet:
        """
        Get recipes for a user with optional filters.

        Args:
            user: The user whose recipes to retrieve
            query: Search query for title/ingredients
            tag_id: Filter by tag ID
            selected_members: Filter by family members who like the recipe
            favourites_only: Show only favourited recipes

        Returns:
            QuerySet of Recipe objects with optimized queries
        """
        recipes = Recipe.objects.filter(user=user)

        # Apply search filter
        if query:
            recipes = recipes.filter(
                Q(title__icontains=query) |
                Q(ingredients__icontains=query)
            )

        # Apply tag filter
        if tag_id:
            recipes = recipes.filter(tags__id=tag_id)

        # Apply family member preference filter
        if selected_members:
            recipes = recipes.annotate(
                matching_likes=Count(
                    'familypreference',
                    filter=Q(
                        familypreference__preference=3,
                        familypreference__family_member__in=selected_members,
                        familypreference__user=user
                    ),
                    distinct=True
                )
            ).filter(matching_likes=len(selected_members))

        # Apply favourites filter
        if favourites_only:
            recipes = recipes.filter(favourited_by=user)

        # Optimize queries and add annotations
        recipes = recipes.annotate(
            total_likes=Count(
                'familypreference',
                filter=Q(familypreference__preference=3, familypreference__user=user),
                distinct=True
            )
        ).distinct().select_related(
            'user'
        ).prefetch_related(
            'tags',
            'favourited_by'
        ).order_by('-created_at')

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
        tags = recipe_data.pop('tags', [])
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
        tags = recipe_data.pop('tags', None)
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
    def add_or_update_preference(
        user: User,
        recipe: Recipe,
        family_member: str,
        preference: int
    ) -> FamilyPreference:
        """
        Add or update a family member's preference for a recipe.

        Args:
            user: The user adding the preference
            recipe: The recipe
            family_member: Name of the family member
            preference: Preference value (1=dislike, 2=neutral, 3=like)

        Returns:
            The FamilyPreference instance
        """
        pref, created = FamilyPreference.objects.update_or_create(
            recipe=recipe,
            family_member=family_member,
            user=user,
            defaults={'preference': preference}
        )
        return pref

    @staticmethod
    def get_family_members(user: User) -> QuerySet:
        """
        Get all family members for a user.

        Args:
            user: The user

        Returns:
            QuerySet of family member names
        """
        return FamilyPreference.objects.filter(
            user=user
        ).values_list('family_member', flat=True).distinct()

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
            if recipe.ingredients:
                for line in recipe.ingredients.splitlines():
                    line = line.strip()
                    if line:
                        ingredient_set.add(line)

        return sorted(ingredient_set)

    @staticmethod
    def get_all_tags() -> QuerySet:
        """Get all available tags."""
        return Tag.objects.all()
