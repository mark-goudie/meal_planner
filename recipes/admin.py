from django.contrib import admin

from .models import (
    CookingNote,
    Ingredient,
    MealPlan,
    MealPlannerPreferences,
    Recipe,
    RecipeIngredient,
    ShoppingListItem,
    Tag,
)

# Inlines


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    autocomplete_fields = ["ingredient"]


# Model admin classes


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "tag_type")
    list_filter = ("tag_type",)
    search_fields = ("name",)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    list_filter = ("category",)
    search_fields = ("name",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "source", "difficulty", "created_at")
    list_filter = ("source", "difficulty", "is_ai_generated")
    search_fields = ("title", "description")
    inlines = [RecipeIngredientInline]


@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "meal_type", "recipe")
    list_filter = ("meal_type", "date")
    search_fields = ("user__username", "recipe__title")


@admin.register(MealPlannerPreferences)
class MealPlannerPreferencesAdmin(admin.ModelAdmin):
    list_display = ("user", "max_weeknight_time", "max_weekend_time", "avoid_repeat_days")


@admin.register(CookingNote)
class CookingNoteAdmin(admin.ModelAdmin):
    list_display = ("recipe", "user", "cooked_date", "rating", "would_make_again")
    list_filter = ("rating", "would_make_again", "cooked_date")
    search_fields = ("recipe__title", "user__username", "note")


@admin.register(ShoppingListItem)
class ShoppingListItemAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "checked", "created_at")
    list_filter = ("checked",)
    search_fields = ("name", "user__username")
