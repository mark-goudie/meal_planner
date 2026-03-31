import random
from datetime import date, timedelta

from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..models import MealPlan, Recipe
from ..models.household import DayComment, get_household
from ..models.template import MealPlanTemplate, MealPlanTemplateEntry
from ..services.meal_planning_assistant import MealPlanningAssistantService


def _get_week_dates(offset=0):
    """Get Monday-Sunday dates for a given week offset."""
    today = timezone.localdate()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return [monday + timedelta(days=i) for i in range(7)]


def _build_week_context(user, household, offset=0):
    """Build template context for the weekly view."""
    dates = _get_week_dates(offset)
    start, end = dates[0], dates[-1]
    meals = MealPlan.objects.with_related().for_household(household).in_date_range(start, end)
    meal_lookup = {(m.date, m.meal_type): m for m in meals}

    # Load DayComments for the week range
    comments = DayComment.objects.filter(household=household, date__range=[start, end]).select_related("user")
    comment_lookup = {}
    for c in comments:
        comment_lookup.setdefault(c.date, []).append(c)

    days = []
    for d in dates:
        meal = meal_lookup.get((d, "dinner"))
        day_comments = comment_lookup.get(d, [])
        my_comment_obj = next((c for c in day_comments if c.user == user), None)
        days.append(
            {
                "date": d,
                "day_name": d.strftime("%a"),
                "day_num": d.day,
                "is_today": d == timezone.localdate(),
                "meal": meal,
                "comments": day_comments,
                "my_comment": my_comment_obj.text if my_comment_obj else "",
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
    household = get_household(request.user)
    if not household:
        return render(request, "week/week.html", {"days": [], "error": "No household found."})
    offset = int(request.GET.get("offset", 0))
    context = _build_week_context(request.user, household, offset)
    return render(request, "week/week.html", context)


@login_required
def week_slot(request, date_str, meal_type):
    """HTMX partial: return a single day card."""
    from datetime import datetime as dt

    household = get_household(request.user)
    slot_date = dt.strptime(date_str, "%Y-%m-%d").date()

    meal = MealPlan.objects.with_related().for_household(household).filter(date=slot_date, meal_type=meal_type).first()

    day = {
        "date": slot_date,
        "day_name": slot_date.strftime("%a"),
        "day_num": slot_date.day,
        "is_today": slot_date == timezone.localdate(),
        "meal": meal,
    }
    return render(request, "week/partials/meal_card.html", {"day": day})


@login_required
def week_assign(request, date_str, meal_type):
    """HTMX partial: recipe picker (GET) or assign a recipe (POST)."""
    from datetime import datetime as dt

    household = get_household(request.user)
    slot_date = dt.strptime(date_str, "%Y-%m-%d").date()

    if request.method == "POST":
        recipe_id = request.POST.get("recipe_id")
        recipe = get_object_or_404(Recipe, pk=recipe_id)

        MealPlan.objects.update_or_create(
            household=household,
            date=slot_date,
            meal_type=meal_type,
            defaults={"recipe": recipe, "added_by": request.user},
        )

        meal = (
            MealPlan.objects.with_related().for_household(household).filter(date=slot_date, meal_type=meal_type).first()
        )

        day = {
            "date": slot_date,
            "day_name": slot_date.strftime("%a"),
            "day_num": slot_date.day,
            "is_today": slot_date == timezone.localdate(),
            "meal": meal,
        }
        return render(request, "week/partials/meal_card.html", {"day": day})

    # GET -- show recipe picker (own recipes + shared household recipes)
    search_query = request.GET.get("q", "").strip()
    recipes = Recipe.objects.filter(
        Q(user=request.user) | Q(shared=True, user__household_membership__household=household)
    ).distinct()
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
    household = get_household(request.user)
    offset = int(request.GET.get("offset", 0))
    dates = _get_week_dates(offset)
    start, end = dates[0], dates[-1]

    # Find empty dinner slots
    existing_meals = set(
        MealPlan.objects.filter(household=household, date__range=[start, end], meal_type="dinner").values_list(
            "date", flat=True
        )
    )
    empty_dates = [d for d in dates if d not in existing_meals]

    if not empty_dates:
        return render(request, "week/partials/no_suggestions.html")

    # Get candidate recipes (own + shared household recipes)
    all_recipes = list(
        Recipe.objects.filter(Q(user=request.user) | Q(shared=True, user__household_membership__household=household))
        .distinct()
        .prefetch_related("tags")
    )
    if not all_recipes:
        return render(request, "week/partials/no_suggestions.html", {"reason": "no_recipes"})

    prefs = MealPlanningAssistantService.get_or_create_preferences(request.user)
    recently_cooked_ids = set(
        MealPlanningAssistantService.get_recently_cooked_recipes(request.user, prefs.avoid_repeat_days)
    )

    # Also exclude recipes already planned this week
    planned_recipe_ids = set(
        MealPlan.objects.filter(household=household, date__range=[start, end]).values_list("recipe_id", flat=True)
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
        time_ok = [
            (r, s) for r, s in scored if r.id not in used_ids and (r.total_time is None or r.total_time <= max_time)
        ]
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
    household = get_household(request.user)
    slot_date = date.fromisoformat(date_str)
    recipe_id = request.POST.get("recipe_id")
    recipe = get_object_or_404(Recipe, pk=recipe_id)

    MealPlan.objects.update_or_create(
        household=household,
        date=slot_date,
        meal_type="dinner",
        defaults={"recipe": recipe, "added_by": request.user},
    )

    meal = MealPlan.objects.with_related().for_household(household).filter(date=slot_date, meal_type="dinner").first()
    day = {
        "date": slot_date,
        "day_name": slot_date.strftime("%a"),
        "day_num": slot_date.day,
        "is_today": slot_date == timezone.localdate(),
        "meal": meal,
    }
    return render(request, "week/partials/meal_card.html", {"day": day})


@login_required
def week_skip_suggestion(request, date_str):
    """HTMX POST: skip a suggestion — remove the suggestion card."""
    return HttpResponse("")


@login_required
def week_remove(request, date_str, meal_type):
    """HTMX POST: remove a meal from the planner (does not delete the recipe)."""
    household = get_household(request.user)
    slot_date = date.fromisoformat(date_str)
    MealPlan.objects.filter(household=household, date=slot_date, meal_type=meal_type).delete()

    # Load comments for this day
    comments = DayComment.objects.filter(household=household, date=slot_date).select_related("user")
    my_comment = next((c.text for c in comments if c.user == request.user), "")

    day = {
        "date": slot_date,
        "day_name": slot_date.strftime("%a"),
        "day_num": slot_date.day,
        "is_today": slot_date == timezone.localdate(),
        "meal": None,
        "comments": list(comments),
        "my_comment": my_comment,
    }
    return render(request, "week/partials/meal_card.html", {"day": day})


@login_required
def day_comment(request, date_str):
    """HTMX: add or update a day comment."""
    household = get_household(request.user)
    comment_date = date.fromisoformat(date_str)

    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        if text:
            DayComment.objects.update_or_create(
                household=household,
                user=request.user,
                date=comment_date,
                defaults={"text": text},
            )
        else:
            DayComment.objects.filter(
                household=household,
                user=request.user,
                date=comment_date,
            ).delete()

    comments = DayComment.objects.filter(household=household, date=comment_date).select_related("user")
    return render(request, "week/partials/day_comment.html", {"comments": comments, "date_str": date_str})


@login_required
def save_template(request):
    """POST: Save the current week's meals as a reusable template."""
    if request.method != "POST":
        return redirect("week")

    household = get_household(request.user)
    name = request.POST.get("name", "").strip()
    offset = int(request.POST.get("offset", 0))

    if not name:
        django_messages.error(request, "Template name is required.")
        return redirect(f"/week/?offset={offset}")

    dates = _get_week_dates(offset)
    start, end = dates[0], dates[-1]
    meals = MealPlan.objects.filter(household=household, date__range=[start, end]).select_related("recipe")

    if not meals.exists():
        django_messages.error(request, "No meals to save this week.")
        return redirect(f"/week/?offset={offset}")

    template = MealPlanTemplate.objects.create(
        household=household,
        name=name,
        created_by=request.user,
    )

    for meal in meals:
        MealPlanTemplateEntry.objects.create(
            template=template,
            day_of_week=meal.date.weekday(),
            meal_type=meal.meal_type,
            recipe=meal.recipe,
        )

    django_messages.success(request, f'Template "{name}" saved!')
    return redirect(f"/week/?offset={offset}")


@login_required
def list_templates(request):
    """GET: HTMX partial showing template picker overlay."""
    household = get_household(request.user)
    offset = request.GET.get("offset", 0)
    templates = MealPlanTemplate.objects.filter(household=household).prefetch_related("entries__recipe")

    return render(
        request,
        "week/partials/template_picker.html",
        {"templates": templates, "offset": offset},
    )


@login_required
def apply_template(request, pk):
    """POST: Apply a template to the target week, filling only empty slots."""
    if request.method != "POST":
        return redirect("week")

    household = get_household(request.user)
    template = get_object_or_404(MealPlanTemplate, pk=pk, household=household)
    offset = int(request.POST.get("offset", 0))

    dates = _get_week_dates(offset)
    monday = dates[0]

    added = 0
    for entry in template.entries.all():
        target_date = monday + timedelta(days=entry.day_of_week)
        exists = MealPlan.objects.filter(household=household, date=target_date, meal_type=entry.meal_type).exists()
        if not exists:
            MealPlan.objects.create(
                household=household,
                added_by=request.user,
                date=target_date,
                meal_type=entry.meal_type,
                recipe=entry.recipe,
            )
            added += 1

    django_messages.success(request, f"Template applied! {added} meal(s) added.")
    return redirect(f"/week/?offset={offset}")


@login_required
def delete_template(request, pk):
    """POST: Delete a template (verify household ownership)."""
    if request.method != "POST":
        return redirect("settings")

    household = get_household(request.user)
    template = get_object_or_404(MealPlanTemplate, pk=pk, household=household)
    template.delete()
    django_messages.success(request, "Template deleted.")
    return redirect("settings")
