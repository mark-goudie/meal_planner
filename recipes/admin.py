from django.contrib import admin
from .models import (
    Recipe, Tag, MealPlan, FamilyPreference,
    DietaryRestriction, MealPlannerPreferences,
    RecipeCookingHistory, GeneratedMealPlan, GeneratedMealPlanEntry
)

# Basic registrations
admin.site.register(Recipe)
admin.site.register(Tag)
admin.site.register(MealPlan)
admin.site.register(FamilyPreference)
admin.site.register(DietaryRestriction)
admin.site.register(MealPlannerPreferences)
admin.site.register(RecipeCookingHistory)


# Custom admin for Generated Meal Plans
class GeneratedMealPlanEntryInline(admin.TabularInline):
    model = GeneratedMealPlanEntry
    extra = 0
    readonly_fields = ('recipe', 'date', 'meal_type', 'happiness_score')


@admin.register(GeneratedMealPlan)
class GeneratedMealPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'week_start', 'week_end', 'approved', 'overall_happiness_score', 'variety_score')
    list_filter = ('approved', 'generated_at')
    search_fields = ('user__username',)
    readonly_fields = ('generated_at', 'approved_at')
    inlines = [GeneratedMealPlanEntryInline]
