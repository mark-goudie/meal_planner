from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..forms import RecipeForm
from ..services import AIAPIError, AIConfigurationError, AIService

# --------------------------
# Public Views
# --------------------------


def privacy(request):
    return render(request, "legal/privacy.html")


def terms(request):
    return render(request, "legal/terms.html")


def disclaimer(request):
    return render(request, "legal/disclaimer.html")


def getting_started(request):
    return redirect("/week/")


# --------------------------
# AI Views
# --------------------------


@login_required
def recipe_create_from_ai(request):
    data = request.session.get("ai_recipe_data", {})
    form = RecipeForm(initial=data)

    if request.method == "POST":
        form = RecipeForm(request.POST)
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.user = request.user
            recipe.save()
            form.save_m2m()
            request.session.pop("ai_recipe_data", None)
            return redirect("recipe_list")

    return render(request, "recipes/recipe_form.html", {"form": form, "update": False})


@login_required
def ai_generate_recipe(request):
    return redirect("/recipes/new/")


@login_required
def ai_surprise_me(request):
    if request.method == "POST":
        try:
            ai_recipe_raw = AIService.generate_surprise_recipe()
            title, ingredients, steps = AIService.parse_generated_recipe(ai_recipe_raw)
            request.session["ai_recipe_data"] = {
                "title": title,
                "ingredients": ingredients,
                "steps": steps,
                "is_ai_generated": True,
            }
            return redirect("recipe_create_from_ai")
        except (AIConfigurationError, AIAPIError):
            return redirect("recipe_list")
    return redirect("recipe_list")


# --------------------------
# Legacy Meal Plan Views (redirects)
# --------------------------


@login_required
def meal_plan_list(request):
    return redirect("/week/")


@login_required
def meal_plan_create(request):
    return redirect("/week/")


@login_required
def meal_plan_week(request):
    return redirect("/week/")


@login_required
def generate_shopping_list(request):
    return redirect("/shop/")


@login_required
def smart_meal_planner(request):
    return redirect("/week/")


@login_required
def meal_planner_preferences(request):
    return redirect("/settings/")
