"""
Meal Plan Service - Business logic for meal planning.

This service encapsulates all meal plan-related operations including:
- Creating and updating meal plans
- Weekly meal plan generation
- Meal plan retrieval and filtering
"""

from datetime import date, timedelta
from typing import Dict, List, Optional
from django.db.models import QuerySet
from django.contrib.auth.models import User

from ..models import MealPlan, Recipe


class MealPlanService:
    """Service for managing meal plan operations."""

    MEAL_TYPES = ['breakfast', 'lunch', 'dinner']

    @staticmethod
    def get_meal_plans_for_user(
        user: User,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        upcoming_only: bool = False
    ) -> QuerySet:
        """
        Get meal plans for a user with optional date filtering.

        Args:
            user: The user whose meal plans to retrieve
            start_date: Filter for plans on or after this date
            end_date: Filter for plans on or before this date
            upcoming_only: Only show today and future meal plans

        Returns:
            QuerySet of MealPlan objects with optimized queries
        """
        plans = MealPlan.objects.filter(user=user)

        if upcoming_only:
            today = date.today()
            plans = plans.filter(date__gte=today)

        if start_date:
            plans = plans.filter(date__gte=start_date)

        if end_date:
            plans = plans.filter(date__lte=end_date)

        # Optimize queries
        plans = plans.select_related(
            'recipe',
            'recipe__user'
        ).prefetch_related(
            'recipe__tags'
        ).order_by('date', 'meal_type')

        return plans

    @staticmethod
    def create_or_update_meal_plan(
        user: User,
        recipe: Recipe,
        plan_date: date,
        meal_type: str
    ) -> tuple[MealPlan, bool]:
        """
        Create or update a meal plan.

        Args:
            user: The user creating the meal plan
            recipe: The recipe to plan
            plan_date: Date of the meal
            meal_type: Type of meal (breakfast, lunch, dinner)

        Returns:
            Tuple of (MealPlan instance, created boolean)
        """
        meal_plan, created = MealPlan.objects.update_or_create(
            user=user,
            date=plan_date,
            meal_type=meal_type,
            defaults={'recipe': recipe}
        )
        return meal_plan, created

    @staticmethod
    def get_weekly_meal_plan(
        user: User,
        week_offset: int = 0
    ) -> Dict:
        """
        Get a structured weekly meal plan.

        Args:
            user: The user
            week_offset: Number of weeks from current (0=this week, -1=last week, 1=next week)

        Returns:
            Dictionary containing:
            - week_days: List of day dictionaries with meal plans
            - week_start: Start date of the week
            - week_end: End date of the week
            - prev_week: Previous week offset
            - next_week: Next week offset
        """
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
        end_of_week = start_of_week + timedelta(days=6)

        # Fetch meal plans for the week
        plans = MealPlanService.get_meal_plans_for_user(
            user=user,
            start_date=start_of_week,
            end_date=end_of_week
        )

        # Build efficient lookup structure
        plans_by_date: Dict[date, Dict[str, Recipe]] = {}
        for plan in plans:
            if plan.date not in plans_by_date:
                plans_by_date[plan.date] = {}
            plans_by_date[plan.date][plan.meal_type] = plan.recipe

        # Build week structure
        week_days = []
        for i in range(7):
            day_date = start_of_week + timedelta(days=i)
            day_plan = plans_by_date.get(day_date, {})
            week_days.append({
                'date': day_date,
                'name': day_date.strftime('%A'),
                'is_today': (day_date == today),
                'breakfast': day_plan.get('breakfast'),
                'lunch': day_plan.get('lunch'),
                'dinner': day_plan.get('dinner'),
            })

        return {
            'week_days': week_days,
            'week_start': start_of_week,
            'week_end': end_of_week,
            'prev_week': week_offset - 1,
            'next_week': week_offset + 1,
            'this_week': 0,
            'meal_types': MealPlanService.MEAL_TYPES,
        }

    @staticmethod
    def delete_meal_plan(meal_plan: MealPlan) -> None:
        """Delete a meal plan."""
        meal_plan.delete()

    @staticmethod
    def get_recipes_in_meal_plans(
        user: User,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Recipe]:
        """
        Get all recipes that are in meal plans for a given period.

        Args:
            user: The user
            start_date: Start of the period
            end_date: End of the period

        Returns:
            List of Recipe objects
        """
        plans = MealPlanService.get_meal_plans_for_user(
            user=user,
            start_date=start_date,
            end_date=end_date
        )
        return [plan.recipe for plan in plans if plan.recipe]
