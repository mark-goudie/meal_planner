from datetime import date

from django.db import models
from django.db.models import Q


class RecipeQuerySet(models.QuerySet):
    """Custom QuerySet for Recipe model with common query optimizations."""

    def with_related(self):
        """Optimize queries by prefetching related objects."""
        return self.select_related("user").prefetch_related("tags", "favourited_by", "recipe_ingredients__ingredient")

    def for_user(self, user):
        """Filter recipes for a specific user."""
        return self.filter(user=user)

    def favourited_by_user(self, user):
        """Filter recipes favourited by a specific user."""
        return self.filter(favourited_by=user)

    def with_tag(self, tag_id):
        """Filter recipes with a specific tag."""
        return self.filter(tags__id=tag_id)

    def search(self, query):
        """Search recipes by title, ingredients text, or structured ingredient names."""
        return self.filter(
            Q(title__icontains=query)
            | Q(ingredients_text__icontains=query)
            | Q(recipe_ingredients__ingredient__name__icontains=query)
        ).distinct()


class RecipeManager(models.Manager):
    """Custom manager for Recipe model."""

    def get_queryset(self):
        return RecipeQuerySet(self.model, using=self._db)

    def with_related(self):
        return self.get_queryset().with_related()

    def for_user(self, user):
        return self.get_queryset().for_user(user)

    def favourited_by_user(self, user):
        return self.get_queryset().favourited_by_user(user)

    def with_tag(self, tag_id):
        return self.get_queryset().with_tag(tag_id)

    def search(self, query):
        return self.get_queryset().search(query)


class MealPlanQuerySet(models.QuerySet):
    """Custom QuerySet for MealPlan model with common query optimizations."""

    def with_related(self):
        """Optimize queries by prefetching related objects."""
        return self.select_related("recipe", "recipe__user").prefetch_related("recipe__tags")

    def for_user(self, user):
        """Filter meal plans for a specific user."""
        return self.filter(user=user)

    def upcoming(self):
        """Filter meal plans for today and future dates."""
        today = date.today()
        return self.filter(date__gte=today)

    def in_date_range(self, start_date, end_date):
        """Filter meal plans within a date range."""
        return self.filter(date__range=[start_date, end_date])


class MealPlanManager(models.Manager):
    """Custom manager for MealPlan model."""

    def get_queryset(self):
        return MealPlanQuerySet(self.model, using=self._db)

    def with_related(self):
        return self.get_queryset().with_related()

    def for_user(self, user):
        return self.get_queryset().for_user(user)

    def upcoming(self):
        return self.get_queryset().upcoming()

    def in_date_range(self, start_date, end_date):
        return self.get_queryset().in_date_range(start_date, end_date)
