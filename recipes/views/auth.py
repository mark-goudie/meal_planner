from django.contrib.auth import login
from django.shortcuts import redirect, render

from ..forms import CustomUserCreationForm
from ..models.household import Household, HouseholdMembership


def offline_view(request):
    """Offline fallback page — no login required so it works when cached."""
    return render(request, "offline.html")


def register_view(request):
    """New-style registration view that redirects to week view."""
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        household_code = request.POST.get("household_code", "").strip().upper()

        if form.is_valid():
            if household_code:
                try:
                    household = Household.objects.get(code=household_code)
                except Household.DoesNotExist:
                    form.add_error(None, "Invalid household code.")
                    return render(
                        request,
                        "auth/register.html",
                        {"form": form, "household_code": household_code},
                    )
            else:
                household = None

            user = form.save()
            if household:
                HouseholdMembership.objects.create(user=user, household=household)
            else:
                new_household = Household.objects.create(
                    name=f"{user.username}'s Kitchen", created_by=user
                )
                HouseholdMembership.objects.create(user=user, household=new_household)

            login(request, user)
            return redirect("week")
    else:
        form = CustomUserCreationForm()
        household_code = ""
    return render(
        request, "auth/register.html", {"form": form, "household_code": household_code}
    )
