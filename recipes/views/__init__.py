from .auth import register_view
from .cook import cook_done, cook_step, cook_view
from .legacy import (
    ai_generate_recipe,
    ai_surprise_me,
    disclaimer,
    generate_shopping_list,
    getting_started,
    meal_plan_create,
    meal_plan_list,
    meal_plan_week,
    meal_planner_preferences,
    privacy,
    recipe_create_from_ai,
    smart_meal_planner,
    terms,
)
from .recipes import (
    ai_generate_recipe_api,
    image_search,
    image_select,
    import_recipe_url,
    recipe_create_view,
    recipe_delete_view,
    recipe_detail_view,
    recipe_list_view,
    recipe_search,
    recipe_update_view,
    toggle_favourite_view,
)
from .settings import settings_view
from .shop import shop_add, shop_generate, shop_toggle, shop_update_qty, shop_view
from .week import (
    day_comment,
    week_accept_suggestion,
    week_assign,
    week_skip_suggestion,
    week_slot,
    week_suggest,
    week_view,
)

__all__ = [
    # Auth
    "register_view",
    # Cook
    "cook_done",
    "cook_step",
    "cook_view",
    # Legacy
    "ai_generate_recipe",
    "ai_surprise_me",
    "disclaimer",
    "generate_shopping_list",
    "getting_started",
    "meal_plan_create",
    "meal_plan_list",
    "meal_plan_week",
    "meal_planner_preferences",
    "privacy",
    "recipe_create_from_ai",
    "smart_meal_planner",
    "terms",
    # Recipes
    "ai_generate_recipe_api",
    "image_search",
    "image_select",
    "import_recipe_url",
    "recipe_create_view",
    "recipe_delete_view",
    "recipe_detail_view",
    "recipe_list_view",
    "recipe_search",
    "recipe_update_view",
    "toggle_favourite_view",
    # Settings
    "settings_view",
    # Shop
    "shop_add",
    "shop_generate",
    "shop_toggle",
    "shop_update_qty",
    "shop_view",
    # Week
    "day_comment",
    "week_accept_suggestion",
    "week_assign",
    "week_skip_suggestion",
    "week_slot",
    "week_suggest",
    "week_view",
]
