from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..forms import MealPlannerPreferencesForm
from ..models import MealPlannerPreferences
from ..models.household import generate_household_code, get_household
from ..models.template import MealPlanTemplate


@login_required
def settings_view(request):
    """User settings and preferences."""
    prefs, _ = MealPlannerPreferences.objects.get_or_create(user=request.user)
    household = get_household(request.user)

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "update_household" and household:
            new_name = request.POST.get("household_name", "").strip()
            if new_name:
                household.name = new_name
                household.save()
                django_messages.success(request, "Household name updated!")
            return redirect("settings")

        if action == "regenerate_code" and household:
            household.code = generate_household_code()
            household.save()
            django_messages.success(request, "Household code regenerated!")
            return redirect("settings")

        # Default: save preferences form
        form = MealPlannerPreferencesForm(request.POST, instance=prefs)
        if form.is_valid():
            form.save()
            django_messages.success(request, "Settings saved!")
            return redirect("settings")
    else:
        form = MealPlannerPreferencesForm(instance=prefs)

    # Build household context
    household_members = []
    templates = []
    if household:
        household_members = [m.user for m in household.members.select_related("user").all()]
        templates = MealPlanTemplate.objects.filter(
            household=household
        ).prefetch_related("entries__recipe")

    return render(
        request,
        "settings/settings.html",
        {
            "form": form,
            "preferences": prefs,
            "household": household,
            "household_members": household_members,
            "templates": templates,
        },
    )
