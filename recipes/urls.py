from django.urls import path
from .views import recipe_list, recipe_create, recipe_detail, recipe_update, recipe_delete, ai_generate_recipe, recipe_create_from_ai, meal_plan_list, meal_plan_create, add_preference, register, toggle_favourite

urlpatterns = [
    path('', recipe_list, name='recipe_list'),
    path('new/', recipe_create, name='recipe_create'),
    path('<int:pk>/', recipe_detail, name='recipe_detail'),
    path('<int:pk>/update/', recipe_update, name='recipe_update'),
    path('<int:pk>/delete/', recipe_delete, name='recipe_delete'),
    path('ai/generate/', ai_generate_recipe, name='ai_generate_recipe'),
    path('ai-generate/', ai_generate_recipe, name='ai_generate_recipe'),
    path('ai-create/', recipe_create_from_ai, name='recipe_create_from_ai'),
    path('meal-plan/', meal_plan_list, name='meal_plan_list'),
    path('meal-plan/new/', meal_plan_create, name='meal_plan_create'),
    path('<int:recipe_id>/rate/', add_preference, name='add_preference'),
    path('register/', register, name='register'),
    path('<int:recipe_id>/favourite/', toggle_favourite, name='toggle_favourite')
    


]
