from django.db import models
from datetime import date
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q, Count, QuerySet


# Custom Managers

class RecipeQuerySet(models.QuerySet):
    """Custom QuerySet for Recipe model with common query optimizations."""

    def with_related(self):
        """Optimize queries by prefetching related objects."""
        return self.select_related('user').prefetch_related('tags', 'favourited_by')

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
        """Search recipes by title or ingredients."""
        return self.filter(
            Q(title__icontains=query) | Q(ingredients__icontains=query)
        )

    def with_likes_count(self, user):
        """Annotate recipes with total likes count for a user."""
        return self.annotate(
            total_likes=Count(
                'familypreference',
                filter=Q(familypreference__preference=3, familypreference__user=user),
                distinct=True
            )
        )


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

    def with_likes_count(self, user):
        return self.get_queryset().with_likes_count(user)


class MealPlanQuerySet(models.QuerySet):
    """Custom QuerySet for MealPlan model with common query optimizations."""

    def with_related(self):
        """Optimize queries by prefetching related objects."""
        return self.select_related('recipe', 'recipe__user').prefetch_related('recipe__tags')

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


# Models

class Recipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipes')
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    ingredients = models.TextField()
    steps = models.TextField()
    notes = models.TextField(blank=True)
    is_ai_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Recipe details
    prep_time = models.PositiveIntegerField(null=True, blank=True, help_text="Preparation time in minutes")
    cook_time = models.PositiveIntegerField(null=True, blank=True, help_text="Cooking time in minutes")
    servings = models.PositiveIntegerField(default=1, help_text="Number of servings")
    difficulty = models.CharField(
        max_length=10,
        choices=[
            ('easy', 'Easy'),
            ('medium', 'Medium'),
            ('hard', 'Hard')
        ],
        default='medium',
        blank=True
    )
    image = models.ImageField(upload_to='recipes/', null=True, blank=True)

    # Relationships
    tags = models.ManyToManyField('Tag', blank=True)
    favourited_by = models.ManyToManyField(User, related_name='favourites', blank=True)

    # Custom manager
    objects = RecipeManager()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return self.title

    @property
    def total_time(self):
        """Calculate total time (prep + cook)"""
        prep = self.prep_time or 0
        cook = self.cook_time or 0
        return prep + cook if (prep or cook) else None

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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meal_plans')
    date = models.DateField(default=date.today)
    meal_type = models.CharField(max_length=10, choices=MEAL_CHOICES)
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE)

    # Custom manager
    objects = MealPlanManager()

    class Meta:
        ordering = ['date', 'meal_type']
        unique_together = ('user', 'date', 'meal_type')
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'date', 'meal_type']),
        ]

    def __str__(self):
        meal_type_display = dict(MEAL_CHOICES).get(self.meal_type, self.meal_type)
        return f"{meal_type_display} on {self.date}: {self.recipe.title}"

PREFERENCE_CHOICES = [
    (1, "Dislike"),
    (2, "Neutral"),
    (3, "Like"),
]

class FamilyPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='family_preferences')
    family_member = models.CharField(max_length=50)
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE)
    preference = models.IntegerField(choices=PREFERENCE_CHOICES)

    class Meta:
        unique_together = ('user', 'family_member', 'recipe')
        constraints = [
            models.CheckConstraint(
                check=models.Q(preference__in=[1, 2, 3]),
                name='preference_valid_value'
            ),
        ]

    def __str__(self):
        preference_display = dict(PREFERENCE_CHOICES).get(self.preference, self.preference)
        return f"{self.family_member} - {self.recipe.title}: {preference_display}"


# Smart Meal Planner Models

class RecipeCookingHistory(models.Model):
    """Track when recipes were cooked to avoid repetition"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cooking_history')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='cooking_history')
    cooked_date = models.DateField()
    meal_type = models.CharField(max_length=10, choices=MEAL_CHOICES)
    rating = models.IntegerField(
        null=True,
        blank=True,
        choices=[(1, '⭐'), (2, '⭐⭐'), (3, '⭐⭐⭐'), (4, '⭐⭐⭐⭐'), (5, '⭐⭐⭐⭐⭐')]
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-cooked_date']
        verbose_name_plural = 'Recipe cooking histories'
        indexes = [
            models.Index(fields=['user', '-cooked_date']),
        ]

    def __str__(self):
        return f"{self.recipe.title} on {self.cooked_date}"


class DietaryRestriction(models.Model):
    """Dietary tags that can be applied to recipes"""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class MealPlannerPreferences(models.Model):
    """User preferences for the smart meal planner"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='planner_preferences')

    # Time constraints
    max_weeknight_time = models.IntegerField(
        default=45,
        help_text="Maximum cooking time for weeknights (minutes)"
    )
    max_weekend_time = models.IntegerField(
        default=90,
        help_text="Maximum cooking time for weekends (minutes)"
    )

    # Variety preferences
    avoid_repeat_days = models.IntegerField(
        default=14,
        help_text="Don't repeat recipes within this many days"
    )
    variety_score = models.IntegerField(
        default=7,
        help_text="Higher = more variety (1-10)"
    )

    # Dietary restrictions
    dietary_restrictions = models.ManyToManyField(DietaryRestriction, blank=True)

    # Meal frequency preferences
    vegetarian_meals_per_week = models.IntegerField(
        default=0,
        help_text="Minimum vegetarian meals per week"
    )

    # Advanced preferences
    use_leftovers = models.BooleanField(
        default=True,
        help_text="Plan for using leftovers"
    )
    batch_cooking_friendly = models.BooleanField(
        default=False,
        help_text="Prefer recipes that work well for meal prep"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Meal planner preferences'

    def __str__(self):
        return f"Preferences for {self.user.username}"


class GeneratedMealPlan(models.Model):
    """Store AI-generated meal plans for review"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='generated_plans')
    week_start = models.DateField()
    week_end = models.DateField()

    # Metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)

    # Scoring
    overall_happiness_score = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        help_text="Predicted family satisfaction (0-100)"
    )
    variety_score = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        help_text="Recipe variety score (0-100)"
    )

    class Meta:
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['user', '-generated_at']),
        ]

    def __str__(self):
        return f"Plan for week of {self.week_start}"


class GeneratedMealPlanEntry(models.Model):
    """Individual meals in a generated plan"""
    plan = models.ForeignKey(GeneratedMealPlan, on_delete=models.CASCADE, related_name='entries')
    date = models.DateField()
    meal_type = models.CharField(max_length=10, choices=MEAL_CHOICES)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    # Scoring for this specific meal
    happiness_score = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        help_text="Predicted satisfaction for this meal (0-100)"
    )

    # Flags
    is_leftover = models.BooleanField(default=False)
    leftover_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generates_leftovers'
    )

    class Meta:
        ordering = ['date', 'meal_type']
        unique_together = ('plan', 'date', 'meal_type')

    def __str__(self):
        return f"{self.date} {self.meal_type}: {self.recipe.title}"
