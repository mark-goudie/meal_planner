from django.contrib.auth.models import User
from django.db import models

from .managers import RecipeManager

TAG_TYPE_CHOICES = [
    ("dietary", "Dietary"),
    ("cuisine", "Cuisine"),
    ("method", "Method"),
    ("time", "Time"),
]


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    tag_type = models.CharField(
        max_length=10,
        choices=TAG_TYPE_CHOICES,
        default="cuisine",
    )

    def __str__(self):
        return self.name


INGREDIENT_CATEGORY_CHOICES = [
    ("produce", "Produce"),
    ("dairy", "Dairy"),
    ("meat", "Meat"),
    ("pantry", "Pantry"),
    ("spices", "Spices"),
    ("frozen", "Frozen"),
    ("bakery", "Bakery"),
    ("other", "Other"),
]

VALID_CATEGORIES = {key for key, _ in INGREDIENT_CATEGORY_CHOICES}

# Map common AI-returned category names to our valid keys
CATEGORY_ALIASES = {
    "vegetable": "produce",
    "vegetables": "produce",
    "fruit": "produce",
    "fruits": "produce",
    "grain": "pantry",
    "grains": "pantry",
    "pasta": "pantry",
    "noodle": "pantry",
    "noodles": "pantry",
    "rice": "pantry",
    "sauce": "pantry",
    "sauces": "pantry",
    "condiment": "pantry",
    "condiments": "pantry",
    "oil": "pantry",
    "oils": "pantry",
    "seasoning": "spices",
    "seasonings": "spices",
    "spice": "spices",
    "herb": "spices",
    "herbs": "spices",
    "protein": "meat",
    "poultry": "meat",
    "seafood": "meat",
    "fish": "meat",
    "bread": "bakery",
    "cheese": "dairy",
    "milk": "dairy",
    "egg": "dairy",
    "eggs": "dairy",
}


def normalize_category(category):
    """Normalize an AI-returned category to a valid INGREDIENT_CATEGORY_CHOICES key."""
    if not category:
        return "other"
    cat = category.lower().strip()
    if cat in VALID_CATEGORIES:
        return cat
    return CATEGORY_ALIASES.get(cat, "other")


class Ingredient(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(
        max_length=10,
        choices=INGREDIENT_CATEGORY_CHOICES,
        default="other",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


SOURCE_CHOICES = [
    ("manual", "Manual"),
    ("ai", "AI Generated"),
    ("url", "Imported from URL"),
    ("family", "Family Recipe"),
]


class Recipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recipes")
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    ingredients_text = models.TextField(blank=True)
    steps = models.TextField()
    notes = models.TextField(blank=True)
    is_ai_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # New fields
    source = models.CharField(
        max_length=10,
        choices=SOURCE_CHOICES,
        default="manual",
    )
    cooking_mode_steps = models.JSONField(null=True, blank=True)

    # Recipe details
    prep_time = models.PositiveIntegerField(
        null=True, blank=True, help_text="Preparation time in minutes"
    )
    cook_time = models.PositiveIntegerField(
        null=True, blank=True, help_text="Cooking time in minutes"
    )
    servings = models.PositiveIntegerField(default=4, help_text="Number of servings")
    difficulty = models.CharField(
        max_length=10,
        choices=[
            ("easy", "Easy"),
            ("medium", "Medium"),
            ("hard", "Hard"),
        ],
        default="medium",
        blank=True,
    )
    image = models.ImageField(upload_to="recipes/", null=True, blank=True)
    image_url = models.URLField(
        max_length=500, blank=True, help_text="External image URL (e.g. Unsplash)"
    )

    # Sharing
    shared = models.BooleanField(default=False)

    # Relationships
    tags = models.ManyToManyField("Tag", blank=True)
    favourited_by = models.ManyToManyField(User, related_name="favourites", blank=True)

    # Custom manager
    objects = RecipeManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return self.title

    @property
    def display_image_url(self):
        """Return the best available image URL, or None."""
        if self.image_url:
            return self.image_url
        if self.image:
            try:
                return self.image.url
            except ValueError:
                return None
        return None

    @property
    def has_image(self):
        """Check if recipe has any image (URL or file)."""
        return bool(self.image_url or self.image)

    @property
    def total_time(self):
        """Calculate total time (prep + cook)."""
        prep = self.prep_time or 0
        cook = self.cook_time or 0
        return prep + cook if (prep or cook) else None

    @property
    def average_rating(self):
        """Calculate average rating from cooking notes."""
        notes = self.cooking_notes.exclude(rating__isnull=True)
        if not notes.exists():
            return None
        return notes.aggregate(avg=models.Avg("rating"))["avg"]

    @property
    def cook_count(self):
        """Count how many times this recipe has been cooked."""
        return self.cooking_notes.count()

    @property
    def latest_note(self):
        """Get the most recent cooking note."""
        return self.cooking_notes.first()


UNIT_CHOICES = [
    ("", "---"),
    ("tsp", "teaspoon"),
    ("tbsp", "tablespoon"),
    ("cup", "cup"),
    ("ml", "millilitre"),
    ("l", "litre"),
    ("g", "gram"),
    ("kg", "kilogram"),
    ("oz", "ounce"),
    ("lb", "pound"),
    ("piece", "piece"),
    ("slice", "slice"),
    ("pinch", "pinch"),
    ("handful", "handful"),
    ("bunch", "bunch"),
    ("can", "can"),
    ("clove", "clove"),
]


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        "Recipe",
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
    )
    ingredient = models.ForeignKey(
        "Ingredient",
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
    )
    quantity = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, blank=True)
    preparation_notes = models.CharField(max_length=100, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        parts = []
        if self.quantity:
            parts.append(str(self.quantity))
        if self.unit:
            parts.append(self.unit)
        parts.append(self.ingredient.name)
        if self.preparation_notes:
            parts.append(f"({self.preparation_notes})")
        return " ".join(parts)
