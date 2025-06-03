from django.db import models
from datetime import date

# Create your models here.

class Recipe(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    ingredients = models.TextField()
    steps = models.TextField()
    notes = models.TextField(blank=True)
    is_ai_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

from django.db import models
from datetime import date

MEAL_CHOICES = [
    ('breakfast', 'Breakfast'),
    ('lunch', 'Lunch'),
    ('dinner', 'Dinner'),
]

class MealPlan(models.Model):
    date = models.DateField(default=date.today)
    meal_type = models.CharField(max_length=10, choices=MEAL_CHOICES)
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE)

    def __str__(self):
        meal_type_display = dict(MEAL_CHOICES).get(self.meal_type, self.meal_type)
        return f"{meal_type_display} on {self.date}: {self.recipe.title}"
