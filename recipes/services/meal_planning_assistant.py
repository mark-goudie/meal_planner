"""
Meal Planning Assistant Service - Smart meal plan generation.

This service generates intelligent weekly meal plans based on:
- Cooking history (via CookingNote)
- Time constraints (weeknight vs weekend)
- Recipe variety optimization
"""

import random
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from django.contrib.auth.models import User
from django.db.models import Avg

from ..models import (
    CookingNote,
    MealPlan,
    MealPlannerPreferences,
    Recipe,
)
from ..models.household import get_household


class MealPlanningAssistantService:
    """Service for generating intelligent meal plans."""

    # Constants
    WEEKDAYS = [0, 1, 2, 3, 4]  # Monday-Friday
    WEEKENDS = [5, 6]  # Saturday-Sunday

    @staticmethod
    def get_or_create_preferences(user: User) -> MealPlannerPreferences:
        """Get or create user preferences with defaults."""
        preferences, created = MealPlannerPreferences.objects.get_or_create(user=user)
        return preferences

    @staticmethod
    def calculate_recipe_score(
        recipe: Recipe,
        user: User,
    ) -> Decimal:
        """
        Calculate how suitable this recipe is based on cooking history.

        Returns: Score from 0-100
        """
        notes = CookingNote.objects.filter(
            recipe=recipe,
            user=user,
            rating__isnull=False,
        )

        if not notes.exists():
            return Decimal("50.0")

        avg_rating = notes.aggregate(Avg("rating"))["rating__avg"] or 3.0
        # Convert 1-5 scale to 0-100
        score = ((avg_rating - 1) / 4) * 100
        return Decimal(str(min(score, 100)))

    @staticmethod
    def calculate_recipe_happiness_score(
        recipe: Recipe,
        user: User,
    ) -> Decimal:
        """
        Calculate happiness score for a recipe based on CookingNote ratings.

        Returns: Score from 0-100.  Neutral 50 if no notes exist.
        Penalised if the latest note has would_make_again=False.
        """
        notes = CookingNote.objects.filter(
            recipe=recipe,
            user=user,
            rating__isnull=False,
        )

        if not notes.exists():
            return Decimal("50.0")

        avg_rating = notes.aggregate(Avg("rating"))["rating__avg"] or 3.0
        # Convert 1-5 scale to 0-100
        score = ((avg_rating - 1) / 4) * 100

        # Penalise if the latest note says would_make_again=False
        latest_note = (
            CookingNote.objects.filter(
                recipe=recipe,
                user=user,
            )
            .order_by("-cooked_date")
            .first()
        )
        if latest_note and not latest_note.would_make_again:
            score = max(score - 20, 0)

        return Decimal(str(min(score, 100)))

    @staticmethod
    def get_recently_cooked_recipes(
        user: User,
        days: int = 14,
    ) -> List[int]:
        """Get recipe IDs cooked within the last N days."""
        cutoff_date = date.today() - timedelta(days=days)
        return list(
            CookingNote.objects.filter(
                user=user,
                cooked_date__gte=cutoff_date,
            )
            .order_by()
            .values_list("recipe_id", flat=True)
            .distinct()
        )

    @staticmethod
    def filter_recipes_by_time_constraint(
        recipes: List[Recipe],
        max_time: int,
    ) -> List[Recipe]:
        """Filter recipes that can be cooked within time limit."""
        return [r for r in recipes if r.total_time is None or r.total_time <= max_time]

    @staticmethod
    def generate_weekly_plan(
        user: User,
        week_start: Optional[date] = None,
        meals_per_day: Optional[List[str]] = None,
    ) -> None:
        """
        Generate an intelligent weekly meal plan and create MealPlan entries.

        Args:
            user: The user to generate plan for
            week_start: Start date (defaults to next Monday)
            meals_per_day: Which meals to plan (defaults to ['dinner'])
        """
        if week_start is None:
            today = date.today()
            days_ahead = 0 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            week_start = today + timedelta(days=days_ahead)

        if meals_per_day is None:
            meals_per_day = ["dinner"]

        prefs = MealPlanningAssistantService.get_or_create_preferences(user)
        household = get_household(user)

        available_recipes = list(Recipe.objects.filter(user=user).prefetch_related("tags"))

        if not available_recipes:
            raise ValueError("No recipes available. Please add some recipes first.")

        recently_cooked_ids = MealPlanningAssistantService.get_recently_cooked_recipes(user, prefs.avoid_repeat_days)

        candidate_recipes = [r for r in available_recipes if r.id not in recently_cooked_ids]

        if not candidate_recipes:
            candidate_recipes = available_recipes

        for day_offset in range(7):
            current_date = week_start + timedelta(days=day_offset)
            is_weekend = current_date.weekday() in MealPlanningAssistantService.WEEKENDS
            max_time = prefs.max_weekend_time if is_weekend else prefs.max_weeknight_time

            time_appropriate = MealPlanningAssistantService.filter_recipes_by_time_constraint(
                candidate_recipes, max_time
            )
            if not time_appropriate:
                time_appropriate = candidate_recipes

            for meal_type in meals_per_day:
                if time_appropriate:
                    recipe = random.choice(time_appropriate)
                else:
                    recipe = random.choice(candidate_recipes)

                MealPlan.objects.update_or_create(
                    household=household,
                    date=current_date,
                    meal_type=meal_type,
                    defaults={"recipe": recipe, "added_by": user},
                )

                if recipe in time_appropriate:
                    time_appropriate.remove(recipe)
