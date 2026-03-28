from datetime import date

from django.contrib.auth.models import User
from django.db import models

from .managers import MealPlanManager

MEAL_CHOICES = [
    ("breakfast", "Breakfast"),
    ("lunch", "Lunch"),
    ("dinner", "Dinner"),
]


class MealPlan(models.Model):
    household = models.ForeignKey(
        "Household", on_delete=models.CASCADE, related_name="meal_plans",
    )
    added_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="+",
    )
    date = models.DateField(default=date.today)
    meal_type = models.CharField(max_length=10, choices=MEAL_CHOICES)
    recipe = models.ForeignKey("Recipe", on_delete=models.CASCADE)
    notes = models.TextField(blank=True)

    # Custom manager
    objects = MealPlanManager()

    class Meta:
        ordering = ["date", "meal_type"]
        unique_together = ("household", "date", "meal_type")
        indexes = [
            models.Index(fields=["household", "date"]),
            models.Index(fields=["household", "date", "meal_type"]),
        ]

    def __str__(self):
        meal_type_display = dict(MEAL_CHOICES).get(self.meal_type, self.meal_type)
        return f"{meal_type_display} on {self.date}: {self.recipe.title}"


class MealPlannerPreferences(models.Model):
    """User preferences for the smart meal planner."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="planner_preferences")

    # Time constraints
    max_weeknight_time = models.IntegerField(
        default=45,
        help_text="Maximum cooking time for weeknights (minutes)",
    )
    max_weekend_time = models.IntegerField(
        default=90,
        help_text="Maximum cooking time for weekends (minutes)",
    )

    # Variety preferences
    avoid_repeat_days = models.IntegerField(
        default=14,
        help_text="Don't repeat recipes within this many days",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Meal planner preferences"

    def __str__(self):
        return f"Preferences for {self.user.username}"
