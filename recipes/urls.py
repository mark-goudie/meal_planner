from django.urls import path
from .views import (
    recipe_list, recipe_create, recipe_detail, recipe_update,
    recipe_delete, ai_generate_recipe, recipe_create_from_ai,
    meal_plan_list, meal_plan_create, register, toggle_favourite,
    generate_shopping_list,
    # Redesign views
    week_view, week_slot, week_assign, week_suggest,
    register_view, shop_placeholder, settings_placeholder,
)
from . import views

urlpatterns = [
    # --- Redesign: This Week (home) ---
    path('', week_view, name='home'),
    path('week/', week_view, name='week'),
    path('week/slot/<str:date_str>/<str:meal_type>/', week_slot, name='week_slot'),
    path('week/assign/<str:date_str>/<str:meal_type>/', week_assign, name='week_assign'),
    path('week/suggest/', week_suggest, name='week_suggest'),

    # --- Redesign: Auth ---
    path('register/', register_view, name='register'),

    # --- Redesign: Placeholder pages ---
    path('shop/', shop_placeholder, name='shop'),
    path('settings/', settings_placeholder, name='settings'),

    # --- Legacy recipe views (still in use) ---
    path('recipes/', recipe_list, name='recipe_list'),
    path('recipes/new/', recipe_create, name='recipe_create'),
    path('recipes/<int:pk>/', recipe_detail, name='recipe_detail'),
    path('recipes/<int:pk>/update/', recipe_update, name='recipe_update'),
    path('recipes/<int:pk>/delete/', recipe_delete, name='recipe_delete'),
    path('recipes/ai/generate/', ai_generate_recipe, name='ai_generate_recipe'),
    path('recipes/ai-create/', recipe_create_from_ai, name='recipe_create_from_ai'),
    path('recipes/<int:recipe_id>/favourite/', toggle_favourite, name='toggle_favourite'),

    # --- Legacy meal plan views ---
    path('meal-plan/', meal_plan_list, name='meal_plan_list'),
    path('meal-plan/new/', meal_plan_create, name='meal_plan_create'),
    path('meal-plan/week/', views.meal_plan_week, name='meal_plan_week'),

    # --- Legacy other views ---
    path('shopping-list/', views.generate_shopping_list, name='generate_shopping_list'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('disclaimer/', views.disclaimer, name='disclaimer'),
    path('getting-started/', views.getting_started, name='getting_started'),
    path('ai-surprise-me/', views.ai_surprise_me, name='ai_surprise_me'),

    # --- Smart Meal Planner ---
    path('smart-planner/', views.smart_meal_planner, name='smart_meal_planner'),
    path('smart-planner/preferences/', views.meal_planner_preferences, name='meal_planner_preferences'),
]
