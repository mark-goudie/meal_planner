from datetime import date

from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..models import CookingNote, Recipe
from ..models.household import get_household


def _parse_cooking_steps(recipe):
    """Parse recipe into cooking mode steps.

    Returns a list of dicts: [{'text': str, 'ingredients': queryset_or_list}, ...]
    """
    if recipe.cooking_mode_steps:
        # Structured JSON steps
        steps = []
        all_ingredients = {ri.pk: ri for ri in recipe.recipe_ingredients.select_related("ingredient").all()}
        for step_data in recipe.cooking_mode_steps:
            ingredient_ids = step_data.get("ingredient_ids", [])
            step_ingredients = [all_ingredients[pk] for pk in ingredient_ids if pk in all_ingredients]
            steps.append(
                {
                    "text": step_data.get("text", ""),
                    "ingredients": step_ingredients,
                }
            )
        return steps

    # Fallback: split steps text by newlines
    lines = [line.strip() for line in recipe.steps.splitlines() if line.strip()]
    all_ingredients = list(recipe.recipe_ingredients.select_related("ingredient").all())
    steps = []
    for i, line in enumerate(lines):
        steps.append(
            {
                "text": line,
                "ingredients": all_ingredients if i == 0 else [],
            }
        )
    return steps


@login_required
def cook_view(request, pk):
    """Full-page cooking mode for a recipe."""
    household = get_household(request.user)
    access_filter = Q(user=request.user)
    if household:
        access_filter |= Q(shared=True, user__household_membership__household=household)
        access_filter |= Q(mealplan__household=household)
    recipe = get_object_or_404(
        Recipe.objects.filter(access_filter)
        .distinct()
        .select_related("user")
        .prefetch_related(
            "recipe_ingredients__ingredient",
            "cooking_notes",
        ),
        pk=pk,
    )
    steps = _parse_cooking_steps(recipe)
    if not steps:
        return redirect("recipe_detail", pk=recipe.pk)

    total_steps = len(steps)
    first_step = steps[0]
    cooking_notes = list(recipe.cooking_notes.exclude(note="")[:3])

    return render(
        request,
        "cook/cook.html",
        {
            "recipe": recipe,
            "step_num": 1,
            "step_text": first_step["text"],
            "step_ingredients": first_step["ingredients"],
            "total_steps": total_steps,
            "cooking_notes": cooking_notes,
        },
    )


@login_required
def cook_step(request, pk, step):
    """HTMX partial for a single cooking step."""
    recipe = get_object_or_404(
        Recipe.objects.select_related("user").prefetch_related(
            "recipe_ingredients__ingredient",
            "cooking_notes",
        ),
        pk=pk,
        user=request.user,
    )
    steps = _parse_cooking_steps(recipe)
    total_steps = len(steps)

    if step < 1 or step > total_steps:
        raise Http404("Step not found")

    current = steps[step - 1]
    cooking_notes = list(recipe.cooking_notes.exclude(note="")[:3])

    return render(
        request,
        "cook/partials/step.html",
        {
            "recipe": recipe,
            "step_num": step,
            "step_text": current["text"],
            "step_ingredients": current["ingredients"],
            "total_steps": total_steps,
            "cooking_notes": cooking_notes,
        },
    )


@login_required
def cook_done(request, pk):
    """Completion screen with rating form (GET) or save note (POST)."""
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
    steps = _parse_cooking_steps(recipe)
    total_steps = len(steps) if steps else 1

    if request.method == "POST":
        rating = request.POST.get("rating")
        note_text = request.POST.get("note", "").strip()
        would_make_again = "would_make_again" in request.POST

        CookingNote.objects.create(
            recipe=recipe,
            user=request.user,
            cooked_date=timezone.localdate(),
            rating=int(rating) if rating else None,
            note=note_text,
            would_make_again=would_make_again,
        )
        django_messages.success(request, f"Cooking note saved for {recipe.title}!")
        return redirect("recipe_detail", pk=recipe.pk)

    return render(
        request,
        "cook/partials/done.html",
        {
            "recipe": recipe,
            "total_steps": total_steps,
        },
    )
