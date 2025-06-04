from django.db import models
from datetime import date
from django.conf import settings
from django.contrib.auth.models import User

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
    tags = models.ManyToManyField('Tag', blank=True)
    favourited_by = models.ManyToManyField(User, related_name='favourites', blank=True)

    def __str__(self):
        return self.title

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

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

PREFERENCE_CHOICES = [
    (1, "Dislike"),
    (2, "Neutral"),
    (3, "Like"),
]

class FamilyPreference(models.Model):
    family_member = models.CharField(max_length=50)
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE)
    preference = models.IntegerField(choices=PREFERENCE_CHOICES)

    class Meta:
        unique_together = ('family_member', 'recipe')

    def __str__(self):
        preference_display = dict(PREFERENCE_CHOICES).get(self.preference, self.preference)
        return f"{self.family_member} - {self.recipe.title}: {preference_display}"
