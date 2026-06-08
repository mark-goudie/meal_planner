from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..models import MealPlan, Recipe
from ..models.household import get_household
from ..services.suggestions import SuggestionService
from .week import _build_week_context


def _today_day(ctx):
    return next((d for d in ctx["days"] if d["is_today"]), None)


@login_required
def tonight_view(request):
    """Home: tonight's dinner (planned or confirm-or-swap) + week strip."""
    household = get_household(request.user)
    today = timezone.localdate()
    if not household:
        return render(
            request, "tonight/tonight.html", {"days": [], "no_household": True}
        )

    ctx = _build_week_context(request.user, household, offset=0)
    today_day = _today_day(ctx)
    suggestion = None
    memory = None
    if today_day and today_day["meal"]:
        memory = SuggestionService.latest_household_note(
            today_day["meal"].recipe, request.user
        )
    else:
        ranked = SuggestionService.rank_for_slot(household, request.user, today)
        suggestion = ranked[0] if ranked else None

    return render(
        request,
        "tonight/tonight.html",
        {
            **ctx,
            "today": today,
            "today_day": today_day,
            "suggestion": suggestion,
            "memory": memory,
            "exclude_for_swap": [suggestion["recipe"].pk] if suggestion else [],
        },
    )


@login_required
def tonight_swap(request):
    """HTMX GET: return the empty hero with the next-best suggestion."""
    household = get_household(request.user)
    today = timezone.localdate()
    exclude_ids = [int(i) for i in request.GET.getlist("exclude") if i.isdigit()]
    ranked = (
        SuggestionService.rank_for_slot(
            household, request.user, today, exclude_ids=exclude_ids
        )
        if household
        else []
    )
    suggestion = ranked[0] if ranked else None
    exclude_for_swap = exclude_ids + ([suggestion["recipe"].pk] if suggestion else [])
    return render(
        request,
        "tonight/partials/hero_empty.html",
        {
            "suggestion": suggestion,
            "today": today,
            "exclude_for_swap": exclude_for_swap,
        },
    )


@login_required
@require_POST
def tonight_accept(request):
    """HTMX POST: assign the suggested recipe to tonight, return planned hero."""
    household = get_household(request.user)
    today = timezone.localdate()
    access = Q(user=request.user) | Q(
        shared=True, user__household_membership__household=household
    )
    recipe = get_object_or_404(
        Recipe.objects.filter(access).distinct(), pk=request.POST.get("recipe_id")
    )
    MealPlan.objects.update_or_create(
        household=household,
        date=today,
        meal_type="dinner",
        defaults={"recipe": recipe, "added_by": request.user},
    )
    meal = (
        MealPlan.objects.with_related()
        .for_household(household)
        .filter(date=today, meal_type="dinner")
        .first()
    )
    today_day = {"date": today, "is_today": True, "meal": meal}
    memory = SuggestionService.latest_household_note(recipe, request.user)
    return render(
        request,
        "tonight/partials/hero_planned.html",
        {"today_day": today_day, "memory": memory},
    )
