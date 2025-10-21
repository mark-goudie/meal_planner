"""
Meal Planning Assistant Service - Smart meal plan generation.

This service generates intelligent weekly meal plans based on:
- Family preferences and cooking history
- Time constraints (weeknight vs weekend)
- Dietary restrictions
- Recipe variety optimization
- Leftover planning
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import random

from django.contrib.auth.models import User
from django.db.models import Q, Avg, Count

from ..models import (
    Recipe,
    FamilyPreference,
    RecipeCookingHistory,
    MealPlannerPreferences,
    GeneratedMealPlan,
    GeneratedMealPlanEntry,
    MEAL_CHOICES
)


class MealPlanningAssistantService:
    """Service for generating intelligent meal plans."""

    # Constants
    WEEKDAYS = [0, 1, 2, 3, 4]  # Monday-Friday
    WEEKENDS = [5, 6]  # Saturday-Sunday

    @staticmethod
    def get_or_create_preferences(user: User) -> MealPlannerPreferences:
        """Get or create user preferences with defaults."""
        preferences, created = MealPlannerPreferences.objects.get_or_create(
            user=user
        )
        return preferences

    @staticmethod
    def calculate_recipe_happiness_score(
        recipe: Recipe,
        user: User,
        preferences: MealPlannerPreferences
    ) -> Decimal:
        """
        Calculate how happy the family will be with this recipe.

        Returns: Score from 0-100
        """
        # Get family preferences for this recipe
        family_prefs = FamilyPreference.objects.filter(
            recipe=recipe,
            user=user
        )

        if not family_prefs.exists():
            # No preferences recorded, neutral score
            return Decimal('50.0')

        # Calculate average preference (1=dislike, 2=neutral, 3=like)
        avg_pref = family_prefs.aggregate(Avg('preference'))['preference__avg'] or 2.0

        # Convert to 0-100 scale
        # 1 (dislike) -> 0
        # 2 (neutral) -> 50
        # 3 (like) -> 100
        score = ((avg_pref - 1) / 2) * 100

        # Bonus for recipes with more family member data
        data_bonus = min(family_prefs.count() * 5, 10)  # Max +10 points
        score += data_bonus

        # Historical rating bonus
        history = RecipeCookingHistory.objects.filter(
            recipe=recipe,
            user=user,
            rating__isnull=False
        )
        if history.exists():
            avg_rating = history.aggregate(Avg('rating'))['rating__avg']
            rating_bonus = ((avg_rating - 1) / 4) * 10  # Max +10 points
            score += rating_bonus

        return Decimal(str(min(score, 100)))

    @staticmethod
    def get_recently_cooked_recipes(
        user: User,
        days: int = 14
    ) -> List[int]:
        """Get recipe IDs cooked within the last N days."""
        cutoff_date = date.today() - timedelta(days=days)
        return list(
            RecipeCookingHistory.objects.filter(
                user=user,
                cooked_date__gte=cutoff_date
            ).values_list('recipe_id', flat=True).distinct()
        )

    @staticmethod
    def calculate_variety_score(
        selected_recipes: List[Recipe],
        preferences: MealPlannerPreferences
    ) -> Decimal:
        """
        Calculate how much variety is in the meal plan.

        Considers:
        - Different protein types
        - Different cuisines
        - Different cooking methods
        Returns: Score from 0-100
        """
        if not selected_recipes:
            return Decimal('0.0')

        # Count unique characteristics (would need recipe metadata)
        # For now, just check for title uniqueness and tag diversity
        unique_recipes = len(set(r.id for r in selected_recipes))
        total_recipes = len(selected_recipes)

        # Get all tags
        all_tags = set()
        for recipe in selected_recipes:
            all_tags.update(recipe.tags.values_list('name', flat=True))

        tag_diversity = len(all_tags)

        # Calculate score
        uniqueness_score = (unique_recipes / total_recipes) * 50
        diversity_score = min(tag_diversity * 5, 50)

        return Decimal(str(uniqueness_score + diversity_score))

    @staticmethod
    def filter_recipes_by_time_constraint(
        recipes: List[Recipe],
        max_time: int
    ) -> List[Recipe]:
        """Filter recipes that can be cooked within time limit."""
        return [
            r for r in recipes
            if r.total_time is None or r.total_time <= max_time
        ]

    @staticmethod
    def generate_weekly_plan(
        user: User,
        week_start: Optional[date] = None,
        meals_per_day: List[str] = None
    ) -> GeneratedMealPlan:
        """
        Generate an intelligent weekly meal plan.

        Args:
            user: The user to generate plan for
            week_start: Start date (defaults to next Monday)
            meals_per_day: Which meals to plan (defaults to ['dinner'])

        Returns:
            GeneratedMealPlan instance with entries
        """
        # Default to next Monday if not specified
        if week_start is None:
            today = date.today()
            days_ahead = 0 - today.weekday()  # 0 = Monday
            if days_ahead <= 0:
                days_ahead += 7
            week_start = today + timedelta(days=days_ahead)

        week_end = week_start + timedelta(days=6)

        # Default to dinner only
        if meals_per_day is None:
            meals_per_day = ['dinner']

        # Get user preferences
        prefs = MealPlanningAssistantService.get_or_create_preferences(user)

        # Get available recipes (user's recipes only)
        available_recipes = list(
            Recipe.objects.filter(user=user).prefetch_related(
                'tags',
                'familypreference_set'
            )
        )

        if not available_recipes:
            raise ValueError("No recipes available. Please add some recipes first.")

        # Get recently cooked recipes to avoid
        recently_cooked_ids = MealPlanningAssistantService.get_recently_cooked_recipes(
            user,
            prefs.avoid_repeat_days
        )

        # Filter out recently cooked recipes
        candidate_recipes = [
            r for r in available_recipes
            if r.id not in recently_cooked_ids
        ]

        # If we filtered out everything, use all recipes
        if not candidate_recipes:
            candidate_recipes = available_recipes

        # Create the meal plan
        plan = GeneratedMealPlan.objects.create(
            user=user,
            week_start=week_start,
            week_end=week_end
        )

        # Generate meals for each day
        selected_recipes = []
        happiness_scores = []

        for day_offset in range(7):
            current_date = week_start + timedelta(days=day_offset)
            is_weekend = current_date.weekday() in MealPlanningAssistantService.WEEKENDS

            # Determine time constraint
            max_time = prefs.max_weekend_time if is_weekend else prefs.max_weeknight_time

            # Filter recipes by time
            time_appropriate = MealPlanningAssistantService.filter_recipes_by_time_constraint(
                candidate_recipes,
                max_time
            )

            if not time_appropriate:
                time_appropriate = candidate_recipes

            for meal_type in meals_per_day:
                # Select recipe
                # Weight by happiness score
                recipe_scores = [
                    (
                        recipe,
                        MealPlanningAssistantService.calculate_recipe_happiness_score(
                            recipe, user, prefs
                        )
                    )
                    for recipe in time_appropriate
                ]

                # Sort by score and add some randomness
                recipe_scores.sort(key=lambda x: x[1], reverse=True)

                # Select from top 50% with weighted random
                top_half = recipe_scores[:len(recipe_scores)//2 + 1]
                if top_half:
                    # Weighted random selection
                    recipes_only = [r for r, s in top_half]
                    weights = [float(s) for r, s in top_half]
                    recipe = random.choices(recipes_only, weights=weights, k=1)[0]
                    happiness_score = next(s for r, s in top_half if r == recipe)
                else:
                    recipe = random.choice(time_appropriate)
                    happiness_score = Decimal('50.0')

                # Create plan entry
                GeneratedMealPlanEntry.objects.create(
                    plan=plan,
                    date=current_date,
                    meal_type=meal_type,
                    recipe=recipe,
                    happiness_score=happiness_score
                )

                selected_recipes.append(recipe)
                happiness_scores.append(happiness_score)

                # Remove from candidates to increase variety
                if recipe in time_appropriate:
                    time_appropriate.remove(recipe)

        # Calculate overall scores
        if happiness_scores:
            plan.overall_happiness_score = sum(happiness_scores) / len(happiness_scores)

        plan.variety_score = MealPlanningAssistantService.calculate_variety_score(
            selected_recipes,
            prefs
        )

        plan.save()

        return plan

    @staticmethod
    def approve_plan(plan: GeneratedMealPlan) -> None:
        """
        Approve a generated plan and create actual meal plans.

        Also creates cooking history entries for tracking.
        """
        from django.utils import timezone
        from ..models import MealPlan

        plan.approved = True
        plan.approved_at = timezone.now()
        plan.save()

        # Create actual meal plans from the generated plan
        for entry in plan.entries.all():
            # Use get_or_create to handle duplicates
            MealPlan.objects.get_or_create(
                user=plan.user,
                date=entry.date,
                meal_type=entry.meal_type,
                defaults={'recipe': entry.recipe}
            )

    @staticmethod
    def regenerate_single_meal(
        plan: GeneratedMealPlan,
        entry: GeneratedMealPlanEntry
    ) -> GeneratedMealPlanEntry:
        """
        Regenerate a single meal in the plan with a different recipe.

        Returns the updated entry.
        """
        user = plan.user
        prefs = MealPlanningAssistantService.get_or_create_preferences(user)

        # Get all recipes except ones already in this plan
        used_recipe_ids = plan.entries.exclude(id=entry.id).values_list('recipe_id', flat=True)

        available_recipes = Recipe.objects.filter(
            user=user
        ).exclude(
            id__in=used_recipe_ids
        ).prefetch_related('tags', 'familypreference_set')

        # Filter by time if it's a weekday
        is_weekend = entry.date.weekday() in MealPlanningAssistantService.WEEKENDS
        max_time = prefs.max_weekend_time if is_weekend else prefs.max_weeknight_time

        time_appropriate = MealPlanningAssistantService.filter_recipes_by_time_constraint(
            list(available_recipes),
            max_time
        )

        if not time_appropriate:
            time_appropriate = list(available_recipes)

        if not time_appropriate:
            raise ValueError("No alternative recipes available")

        # Pick a random recipe from available
        new_recipe = random.choice(time_appropriate)
        new_happiness_score = MealPlanningAssistantService.calculate_recipe_happiness_score(
            new_recipe,
            user,
            prefs
        )

        # Update the entry
        entry.recipe = new_recipe
        entry.happiness_score = new_happiness_score
        entry.save()

        # Recalculate plan scores
        all_entries = plan.entries.all()
        happiness_scores = [e.happiness_score for e in all_entries if e.happiness_score]

        if happiness_scores:
            plan.overall_happiness_score = sum(happiness_scores) / len(happiness_scores)

        plan.variety_score = MealPlanningAssistantService.calculate_variety_score(
            [e.recipe for e in all_entries],
            prefs
        )
        plan.save()

        return entry
