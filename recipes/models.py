from django.db import models

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
