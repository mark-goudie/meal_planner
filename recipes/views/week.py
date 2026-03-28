import random
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from ..models import MealPlan, Recipe
from ..services.meal_planning_assistant import MealPlanningAssistantService


def _get_week_dates(offset=0):
    """Get Monday-Sunday dates for a given week offset."""
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return [monday + timedelta(days=i) for i in range(7)]


def _build_week_context(user, offset=0):
    """Build template context for the weekly view."""
    dates = _get_week_dates(offset)
    start, end = dates[0], dates[-1]
    meals = MealPlan.objects.with_related().for_user(user).in_date_range(start, end)
    meal_lookup = {(m.date, m.meal_type): m for m in meals}

    days = []
    for d in dates:
        meal = meal_lookup.get((d, "dinner"))
        days.append(
            {
                "date": d,
                "day_name": d.strftime("%a"),
                "day_num": d.day,
                "is_today": d == date.today(),
                "meal": meal,
            }
        )

    return {
        "days": days,
        "week_start": start,
        "week_end": end,
        "offset": offset,
    }


@login_required
def week_view(request):
    """This Week -- full page weekly meal plan view."""
    offset = int(request.GET.get("offset", 0))
    context = _build_week_context(request.user, offset)
    return render(request, "week/week.html", context)


@login_required
def week_slot(request, date_str, meal_type):
    """HTMX partial: return a single day card."""
    from datetime import datetime as dt

    slot_date = dt.strptime(date_str, "%Y-%m-%d").date()

    meal = MealPlan.objects.with_related().for_user(request.user).filter(date=slot_date, meal_type=meal_type).first()

    day = {
        "date": slot_date,
        "day_name": slot_date.strftime("%a"),
        "day_num": slot_date.day,
        "is_today": slot_date == date.today(),
        "meal": meal,
    }
    return render(request, "week/partials/meal_card.html", {"day": day})


@login_required
def week_assign(request, date_str, meal_type):
    """HTMX partial: recipe picker (GET) or assign a recipe (POST)."""
    from datetime import datetime as dt

    slot_date = dt.strptime(date_str, "%Y-%m-%d").date()

    if request.method == "POST":
        recipe_id = request.POST.get("recipe_id")
        recipe = get_object_or_404(Recipe, pk=recipe_id, user=request.user)

        MealPlan.objects.update_or_create(
            user=request.user,
            date=slot_date,
            meal_type=meal_type,
            defaults={"recipe": recipe},
        )

        meal = (
            MealPlan.objects.with_related().for_user(request.user).filter(date=slot_date, meal_type=meal_type).first()
        )

        day = {
            "date": slot_date,
            "day_name": slot_date.strftime("%a"),
            "day_num": slot_date.day,
            "is_today": slot_date == date.today(),
            "meal": meal,
        }
        return render(request, "week/partials/meal_card.html", {"day": day})

    # GET -- show recipe picker
    search_query = request.GET.get("q", "").strip()
    recipes = Recipe.objects.for_user(request.user)
    if search_query:
        recipes = recipes.search(search_query)
    recipes = recipes.order_by("title")

    return render(
        request,
        "week/partials/recipe_picker.html",
        {
            "recipes": recipes,
            "date_str": date_str,
            "meal_type": meal_type,
            "day_label": f"{slot_date.strftime('%A %d %b')}",
            "search_query": search_query,
        },
    )


@login_required
def week_suggest(request):
    """Suggest recipes for empty dinner slots in the current week."""
    offset = int(request.GET.get("offset", 0))
    dates = _get_week_dates(offset)
    start, end = dates[0], dates[-1]

    # Find empty dinner slots
    existing_meals = set(
        MealPlan.objects.filter(user=request.user, date__range=[start, end], meal_type="dinner").values_list(
            "date", flat=True
        )
    )
    empty_dates = [d for d in dates if d not in existing_meals]

    if not empty_dates:
        return render(request, "week/partials/no_suggestions.html")

    # Get candidate recipes
    all_recipes = list(Recipe.objects.filter(user=request.user).prefetch_related("tags"))
    if not all_recipes:
        return render(request, "week/partials/no_suggestions.html", {"reason": "no_recipes"})

    prefs = MealPlanningAssistantService.get_or_create_preferences(request.user)
    recently_cooked_ids = set(
        MealPlanningAssistantService.get_recently_cooked_recipes(request.user, prefs.avoid_repeat_days)
    )

    # Also exclude recipes already planned this week
    planned_recipe_ids = set(
        MealPlan.objects.filter(user=request.user, date__range=[start, end]).values_list("recipe_id", flat=True)
    )

    candidates = [r for r in all_recipes if r.id not in recently_cooked_ids and r.id not in planned_recipe_ids]
    if not candidates:
        candidates = [r for r in all_recipes if r.id not in planned_recipe_ids]
    if not candidates:
        candidates = all_recipes

    # Score and rank candidates
    scored = []
    for recipe in candidates:
        score = float(MealPlanningAssistantService.calculate_recipe_happiness_score(recipe, request.user))
        scored.append((recipe, score))
    scored.sort(key=lambda x: x[1], reverse=True)

    # Pick suggestions for each empty slot
    suggestions = []
    used_ids = set()
    for slot_date in empty_dates:
        is_weekend = slot_date.weekday() in MealPlanningAssistantService.WEEKENDS
        max_time = prefs.max_weekend_time if is_weekend else prefs.max_weeknight_time

        # Filter by time, then pick from top scorers with some randomness
        time_ok = [(r, s) for r, s in scored if r.id not in used_ids and (r.total_time is None or r.total_time <= max_time)]
        if not time_ok:
            time_ok = [(r, s) for r, s in scored if r.id not in used_ids]
        if not time_ok:
            continue

        # Weighted random from top half
        pool = time_ok[: max(len(time_ok) // 2, 1)]
        recipe, score = random.choice(pool)
        used_ids.add(recipe.id)

        suggestions.append(
            {
                "date": slot_date,
                "date_str": slot_date.strftime("%Y-%m-%d"),
                "day_name": slot_date.strftime("%a"),
                "day_num": slot_date.day,
                "recipe": recipe,
                "score": round(score),
            }
        )

    return render(request, "week/partials/suggestions.html", {"suggestions": suggestions})


@login_required
def week_accept_suggestion(request, date_str):
    """HTMX POST: accept a suggestion and assign the recipe to the slot."""
    slot_date = date.fromisoformat(date_str)
    recipe_id = request.POST.get("recipe_id")
    recipe = get_object_or_404(Recipe, pk=recipe_id, user=request.user)

    MealPlan.objects.update_or_create(
        user=request.user,
        date=slot_date,
        meal_type="dinner",
        defaults={"recipe": recipe},
    )

    meal = MealPlan.objects.with_related().for_user(request.user).filter(date=slot_date, meal_type="dinner").first()
    day = {
        "date": slot_date,
        "day_name": slot_date.strftime("%a"),
        "day_num": slot_date.day,
        "is_today": slot_date == date.today(),
        "meal": meal,
    }
    return render(request, "week/partials/meal_card.html", {"day": day})


@login_required
def week_skip_suggestion(request, date_str):
    """HTMX POST: skip a suggestion — remove the suggestion card."""
    return HttpResponse("")
