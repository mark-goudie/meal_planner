from django.urls import path

from . import views
from .views import (
    ai_generate_recipe,
    cook_done,
    cook_step,
    cook_view,
    meal_plan_create,
    meal_plan_list,
    recipe_create_from_ai,
    recipe_create_view,
    recipe_delete_view,
    recipe_detail_view,
    recipe_list_view,
    recipe_search,
    recipe_update_view,
    register_view,
    settings_view,
    shop_add,
    shop_generate,
    shop_toggle,
    shop_view,
    toggle_favourite_view,
    week_assign,
    week_slot,
    week_suggest,
    week_view,
)

urlpatterns = [
    # --- Redesign: This Week (home) ---
    path("", week_view, name="home"),
    path("week/", week_view, name="week"),
    path("week/slot/<str:date_str>/<str:meal_type>/", week_slot, name="week_slot"),
    path("week/assign/<str:date_str>/<str:meal_type>/", week_assign, name="week_assign"),
    path("week/suggest/", week_suggest, name="week_suggest"),
    # --- Redesign: Auth ---
    path("register/", register_view, name="register"),
    # --- Redesign: Cooking mode ---
    path("cook/<int:pk>/", cook_view, name="cook"),
    path("cook/<int:pk>/step/<int:step>/", cook_step, name="cook_step"),
    path("cook/<int:pk>/done/", cook_done, name="cook_done"),
    # --- Redesign: Shopping list ---
    path("shop/", shop_view, name="shop"),
    path("shop/generate/", shop_generate, name="shop_generate"),
    path("shop/toggle/<int:pk>/", shop_toggle, name="shop_toggle"),
    path("shop/add/", shop_add, name="shop_add"),
    # --- Redesign: Settings ---
    path("settings/", settings_view, name="settings"),
    # --- Redesign: Recipe views ---
    path("recipes/", recipe_list_view, name="recipe_list"),
    path("recipes/search/", recipe_search, name="recipe_search"),
    path("recipes/new/", recipe_create_view, name="recipe_create"),
    path("recipes/<int:pk>/", recipe_detail_view, name="recipe_detail"),
    path("recipes/<int:pk>/edit/", recipe_update_view, name="recipe_update"),
    path("recipes/<int:pk>/delete/", recipe_delete_view, name="recipe_delete"),
    path("recipes/<int:pk>/favourite/", toggle_favourite_view, name="toggle_favourite"),
    # --- Legacy recipe views (AI-related, still in use) ---
    path("recipes/ai/generate/", ai_generate_recipe, name="ai_generate_recipe"),
    path("recipes/ai-create/", recipe_create_from_ai, name="recipe_create_from_ai"),
    # --- Legacy meal plan views ---
    path("meal-plan/", meal_plan_list, name="meal_plan_list"),
    path("meal-plan/new/", meal_plan_create, name="meal_plan_create"),
    path("meal-plan/week/", views.meal_plan_week, name="meal_plan_week"),
    # --- Legacy other views ---
    path("shopping-list/", views.generate_shopping_list, name="generate_shopping_list"),
    path("privacy/", views.privacy, name="privacy"),
    path("terms/", views.terms, name="terms"),
    path("disclaimer/", views.disclaimer, name="disclaimer"),
    path("getting-started/", views.getting_started, name="getting_started"),
    path("ai-surprise-me/", views.ai_surprise_me, name="ai_surprise_me"),
    # --- Smart Meal Planner ---
    path("smart-planner/", views.smart_meal_planner, name="smart_meal_planner"),
    path("smart-planner/preferences/", views.meal_planner_preferences, name="meal_planner_preferences"),
]
