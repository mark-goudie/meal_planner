from django.contrib.auth import login
from django.shortcuts import redirect, render

from ..forms import CustomUserCreationForm


def register_view(request):
    """New-style registration view that redirects to week view."""
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("week")
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/register.html", {"form": form})
