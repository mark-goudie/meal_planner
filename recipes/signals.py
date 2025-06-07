from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Recipe

@receiver(post_save, sender=User)
def create_demo_recipes(sender, instance, created, **kwargs):
    if created:
        # Only add if user has no recipes
        if not Recipe.objects.filter(user=instance).exists():
            Recipe.objects.create(
                user=instance,
                title="Classic Omelette",
                description="A simple and quick omelette recipe.",
                ingredients="2 eggs\nSalt\nPepper\nButter",
                steps="1. Beat eggs with salt and pepper.\n2. Melt butter in a pan.\n3. Pour eggs and cook until set.",
                notes="Try adding cheese or herbs for extra flavour.",
            )
            Recipe.objects.create(
                user=instance,
                title="Fresh Garden Salad",
                description="A healthy salad with fresh vegetables.",
                ingredients="Lettuce\nTomato\nCucumber\nOlive oil\nLemon juice\nSalt\nPepper",
                steps="1. Chop vegetables.\n2. Toss with olive oil, lemon juice, salt, and pepper.",
                notes="Add feta cheese or olives for variety.",
            )