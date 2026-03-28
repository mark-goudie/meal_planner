from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from ..models import MealPlan, Recipe


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
    """Placeholder for AI meal suggestions -- returns empty response."""
    return HttpResponse("")
