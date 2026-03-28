from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..forms import MealPlannerPreferencesForm
from ..models import MealPlannerPreferences


@login_required
def settings_view(request):
    """User settings and preferences."""
    prefs, _ = MealPlannerPreferences.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = MealPlannerPreferencesForm(request.POST, instance=prefs)
        if form.is_valid():
            form.save()
            django_messages.success(request, "Settings saved!")
            return redirect("settings")
    else:
        form = MealPlannerPreferencesForm(instance=prefs)

    return render(
        request,
        "settings/settings.html",
        {
            "form": form,
            "preferences": prefs,
        },
    )
