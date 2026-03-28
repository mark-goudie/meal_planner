from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date
from django_ratelimit.decorators import ratelimit

from ..forms import MealPlanForm, MealPlannerPreferencesForm, RecipeForm, WeeklyPlanGeneratorForm
from ..models import MealPlan, Recipe
from ..models.household import get_household
from ..services import (
    AIAPIError,
    AIConfigurationError,
    AIService,
    AIValidationError,
    MealPlanningAssistantService,
)


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
    return render(request, "recipes/getting_started.html")


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
@ratelimit(key="user", rate="5/h", method="POST", block=True)
def ai_generate_recipe(request):
    generated_recipe = None
    error = None

    if request.method == "POST":
        if "prompt" in request.POST:
            prompt = request.POST.get("prompt")

            try:
                # Use AIService for generation
                generated_recipe = AIService.generate_recipe_from_prompt(prompt)

            except (AIConfigurationError, AIValidationError, AIAPIError) as e:
                error = str(e)

        elif "use_recipe" in request.POST:
            raw = request.POST.get("generated_recipe", "")
            title, ingredients, steps = AIService.parse_generated_recipe(raw)

            request.session["ai_recipe_data"] = {
                "title": title,
                "ingredients": ingredients,
                "steps": steps,
                "is_ai_generated": True,
            }
            return redirect("recipe_create_from_ai")

    return render(request, "recipes/ai_generate.html", {"generated_recipe": generated_recipe, "error": error})


@login_required
@ratelimit(key="user", rate="3/h", method="POST", block=True)
def ai_surprise_me(request):
    if request.method == "POST":
        try:
            # Use AIService for surprise recipe generation
            ai_recipe_raw = AIService.generate_surprise_recipe()
            # Parse the AI response into title, ingredients, steps
            title, ingredients, steps = AIService.parse_generated_recipe(ai_recipe_raw)
            request.session["ai_recipe_data"] = {
                "title": title,
                "ingredients": ingredients,
                "steps": steps,
                "is_ai_generated": True,
            }
            return redirect("recipe_create_from_ai")
        except (AIConfigurationError, AIAPIError):
            # On error, redirect to recipe list
            return redirect("recipe_list")
    return redirect("recipe_list")


# --------------------------
# Legacy Meal Plan Views
# --------------------------


@login_required
def meal_plan_list(request):
    household = get_household(request.user)
    plans = (
        MealPlan.objects.filter(household=household)
        .select_related("recipe", "recipe__user")
        .prefetch_related("recipe__tags")
        .order_by("date", "meal_type")
    )
    return render(request, "recipes/meal_plan_list.html", {"plans": plans})


@login_required
def meal_plan_create(request):
    initial = {}
    # Pre-populate date and meal_type from query params if present
    if "date" in request.GET:
        initial["date"] = request.GET["date"]
    if "meal_type" in request.GET:
        initial["meal_type"] = request.GET["meal_type"]

    # Determine the week offset for redirect
    selected_date = parse_date(request.GET.get("date", str(date.today())))
    if selected_date is None:
        selected_date = date.today()
    week_offset = (selected_date - date.today()).days // 7

    household = get_household(request.user)
    if request.method == "POST":
        form = MealPlanForm(request.POST, user=request.user)
        if form.is_valid():
            meal_plan, created = MealPlan.objects.update_or_create(
                household=household,
                date=form.cleaned_data["date"],
                meal_type=form.cleaned_data["meal_type"],
                defaults={"recipe": form.cleaned_data["recipe"], "added_by": request.user},
            )
            # Redirect back to the weekly meal plan with the correct week offset
            return redirect(f"{reverse('meal_plan_week')}?week={week_offset}")
    else:
        form = MealPlanForm(initial=initial, user=request.user)
    return render(request, "recipes/meal_plan_form.html", {"form": form})


@login_required
def meal_plan_week(request):
    # Get week offset from query param (?week=0 for current, -1 for prev, 1 for next)
    week_offset = int(request.GET.get("week", 0))
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)

    # Fetch meal plans for this week
    household = get_household(request.user)
    plans = (
        MealPlan.objects.filter(household=household, date__range=[start_of_week, end_of_week])
        .select_related("recipe", "recipe__user")
        .prefetch_related("recipe__tags")
        .order_by("date", "meal_type")
    )

    # Build a structure: {date: {breakfast: ..., lunch: ..., dinner: ...}}
    # Convert to dict for efficient lookup
    plans_by_date = {}
    for plan in plans:
        if plan.date not in plans_by_date:
            plans_by_date[plan.date] = {}
        plans_by_date[plan.date][plan.meal_type] = plan.recipe

    week_days = []
    meal_types = ["breakfast", "lunch", "dinner"]
    for i in range(7):
        day_date = start_of_week + timedelta(days=i)
        day_plan = plans_by_date.get(day_date, {})
        week_days.append(
            {
                "date": day_date,
                "name": day_date.strftime("%A"),
                "is_today": (day_date == today),
                "breakfast": day_plan.get("breakfast"),
                "lunch": day_plan.get("lunch"),
                "dinner": day_plan.get("dinner"),
            }
        )

    context = {
        "week_days": week_days,
        "week_start": start_of_week,
        "week_end": end_of_week,
        "prev_week": week_offset - 1,
        "next_week": week_offset + 1,
        "this_week": 0,
        "meal_types": meal_types,
    }
    return render(request, "recipes/meal_plan_week.html", context)


@login_required
def generate_shopping_list(request):
    if request.method == "POST":
        recipe_ids = request.POST.getlist("recipe_ids")
        recipes = Recipe.objects.filter(id__in=recipe_ids, user=request.user)
        # Combine ingredients (assuming ingredients are stored as text, one per line)
        ingredient_set = set()
        for recipe in recipes:
            if recipe.ingredients_text:
                for line in recipe.ingredients_text.splitlines():
                    line = line.strip()
                    if line:
                        ingredient_set.add(line)
        shopping_list = sorted(ingredient_set)
        return render(
            request,
            "recipes/shopping_list.html",
            {
                "shopping_list": shopping_list,
                "recipes": recipes,
            },
        )
    # If GET or no recipes selected, redirect or show empty
    return render(request, "recipes/shopping_list.html", {"shopping_list": [], "recipes": []})


# --------------------------
# Smart Meal Planner Views
# --------------------------


@login_required
def meal_planner_preferences(request):
    """Configure smart meal planner preferences"""
    preferences = MealPlanningAssistantService.get_or_create_preferences(request.user)

    if request.method == "POST":
        form = MealPlannerPreferencesForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            return redirect("smart_meal_planner")
    else:
        form = MealPlannerPreferencesForm(instance=preferences)

    return render(
        request,
        "recipes/meal_planner_preferences.html",
        {
            "form": form,
            "preferences": preferences,
        },
    )


@login_required
def smart_meal_planner(request):
    """Smart weekly meal plan generator"""
    preferences = MealPlanningAssistantService.get_or_create_preferences(request.user)

    if request.method == "POST":
        form = WeeklyPlanGeneratorForm(request.POST)
        if form.is_valid():
            week_start = form.cleaned_data.get("week_start")
            meals_to_plan = form.cleaned_data.get("meals_to_plan")

            try:
                # Generate the plan
                MealPlanningAssistantService.generate_weekly_plan(
                    user=request.user, week_start=week_start, meals_per_day=meals_to_plan
                )

                return redirect("meal_plan_week")

            except ValueError as e:
                form.add_error(None, str(e))
    else:
        form = WeeklyPlanGeneratorForm()

    return render(
        request,
        "recipes/smart_meal_planner.html",
        {
            "form": form,
            "preferences": preferences,
        },
    )
