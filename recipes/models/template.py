from django.contrib.auth.models import User
from django.db import models


class MealPlanTemplate(models.Model):
    household = models.ForeignKey("Household", on_delete=models.CASCADE, related_name="meal_templates")
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class MealPlanTemplateEntry(models.Model):
    template = models.ForeignKey(MealPlanTemplate, on_delete=models.CASCADE, related_name="entries")
    day_of_week = models.IntegerField(help_text="0=Monday, 6=Sunday")
    meal_type = models.CharField(max_length=10, default="dinner")
    recipe = models.ForeignKey("Recipe", on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["template", "day_of_week", "meal_type"],
                name="unique_template_day_meal",
            ),
        ]
        ordering = ["day_of_week"]

    def __str__(self):
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        return f"{days[self.day_of_week]}: {self.recipe.title}"
