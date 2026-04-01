import json
import logging
import re
from decimal import Decimal, InvalidOperation

import requests as http_requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.db.models import F, Max, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from ..models import (
    UNIT_CHOICES,
    Ingredient,
    Recipe,
    RecipeIngredient,
    Tag,
)
from ..models.household import get_household
from ..services.ai_service import AIService, AIServiceException
from ..utils.units import normalize_unit

logger = logging.getLogger(__name__)


def _get_sorted_recipes(queryset, sort, user):
    """Apply sort ordering to a recipe queryset.

    Expects queryset to already have avg_rating and note_count annotations
    from with_stats().
    """
    if sort == "rating":
        return queryset.order_by(F("avg_rating").desc(nulls_last=True), "-created_at")
    elif sort == "times_cooked":
        return queryset.order_by(F("note_count").desc(), "-created_at")
    elif sort == "recently_cooked":
        return queryset.annotate(last_cooked=Max("cooking_notes__cooked_date")).order_by(
            F("last_cooked").desc(nulls_last=True), "-created_at"
        )
    else:  # 'newest' or default
        return queryset.order_by("-created_at")


@login_required
def recipe_list_view(request):
    """Recipe Collection -- full page view with search, filter, sort."""
    household = get_household(request.user)
    recipes = (
        Recipe.objects.filter(Q(user=request.user) | Q(shared=True, user__household_membership__household=household))
        .distinct()
        .with_related()
        .with_stats()
    )

    query = request.GET.get("q", "").strip()
    tag_id = request.GET.get("tag", "")
    sort = request.GET.get("sort", "newest")
    favourites_only = request.GET.get("favourites") == "1"

    if query:
        recipes = recipes.search(query)

    if tag_id:
        recipes = recipes.with_tag(tag_id)

    if favourites_only:
        recipes = recipes.favourited_by_user(request.user)

    recipes = _get_sorted_recipes(recipes, sort, request.user)

    paginator = Paginator(recipes, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    tags = Tag.objects.all()

    return render(
        request,
        "recipes/list.html",
        {
            "page_obj": page_obj,
            "recipes": page_obj.object_list,
            "tags": tags,
            "query": query,
            "selected_tag": int(tag_id) if tag_id else None,
            "sort": sort,
            "favourites_only": favourites_only,
        },
    )


@login_required
def recipe_search(request):
    """HTMX partial -- returns filtered recipe cards without page wrapper."""
    household = get_household(request.user)
    recipes = (
        Recipe.objects.filter(Q(user=request.user) | Q(shared=True, user__household_membership__household=household))
        .distinct()
        .with_related()
        .with_stats()
    )

    query = request.GET.get("q", "").strip()
    tag_id = request.GET.get("tag", "")
    sort = request.GET.get("sort", "newest")
    favourites_only = request.GET.get("favourites") == "1"

    if query:
        recipes = recipes.search(query)

    if tag_id:
        recipes = recipes.with_tag(tag_id)

    if favourites_only:
        recipes = recipes.favourited_by_user(request.user)

    recipes = _get_sorted_recipes(recipes, sort, request.user)

    paginator = Paginator(recipes, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "recipes/partials/search_results.html",
        {
            "page_obj": page_obj,
            "recipes": page_obj.object_list,
            "query": query,
            "selected_tag": int(tag_id) if tag_id else None,
            "sort": sort,
            "favourites_only": favourites_only,
        },
    )


@login_required
def recipe_detail_view(request, pk):
    """Recipe Detail -- full page view with ingredients, steps, notes.

    Accessible if:
    - User owns the recipe, OR
    - Recipe is shared and user is in the same household, OR
    - Recipe is assigned to the user's household meal plan
    """
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
            "tags",
            "favourited_by",
            "recipe_ingredients__ingredient",
            "cooking_notes",
        ),
        pk=pk,
    )
    structured_ingredients = recipe.recipe_ingredients.all()
    cooking_notes = recipe.cooking_notes.all()
    is_favourited = request.user in recipe.favourited_by.all()

    return render(
        request,
        "recipes/detail.html",
        {
            "recipe": recipe,
            "structured_ingredients": structured_ingredients,
            "cooking_notes": cooking_notes,
            "is_favourited": is_favourited,
        },
    )


def _process_structured_ingredients(request, recipe):
    """Process dynamically named ingredient fields from the form POST."""
    # Clear existing structured ingredients
    recipe.recipe_ingredients.all().delete()

    count = int(request.POST.get("ingredient_count", 0))
    for i in range(count):
        name = request.POST.get(f"ing_name_{i}", "").strip()
        if not name:
            continue
        ingredient, _ = Ingredient.objects.get_or_create(
            name=name.lower(),
            defaults={"category": "other"},
        )
        qty = request.POST.get(f"ing_qty_{i}", "").strip()
        try:
            quantity = Decimal(qty) if qty else None
        except (InvalidOperation, ValueError):
            quantity = None
        RecipeIngredient.objects.create(
            recipe=recipe,
            ingredient=ingredient,
            quantity=quantity,
            unit=normalize_unit(request.POST.get(f"ing_unit_{i}", "")),
            preparation_notes=request.POST.get(f"ing_notes_{i}", "").strip(),
            order=i,
        )


@login_required
def recipe_create_view(request):
    """Create a new recipe with structured ingredient entry."""
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        if not title:
            return render(
                request,
                "recipes/form.html",
                {
                    "error": "Title is required.",
                    "unit_choices": UNIT_CHOICES,
                },
            )

        recipe = Recipe.objects.create(
            user=request.user,
            title=title,
            description=request.POST.get("description", "").strip(),
            prep_time=int(request.POST["prep_time"]) if request.POST.get("prep_time") else None,
            cook_time=int(request.POST["cook_time"]) if request.POST.get("cook_time") else None,
            servings=int(request.POST.get("servings", 4)),
            difficulty=request.POST.get("difficulty", "medium"),
            source=request.POST.get("source", "manual"),
            steps=request.POST.get("steps", ""),
            notes=request.POST.get("notes", ""),
            ingredients_text=request.POST.get("ingredients_text", ""),
            shared=request.POST.get("shared") == "1",
        )
        # Tags
        tag_ids = request.POST.getlist("tags")
        if tag_ids:
            recipe.tags.set(tag_ids)

        _process_structured_ingredients(request, recipe)

        return redirect("recipe_detail", pk=recipe.pk)

    tags = Tag.objects.all()
    return render(
        request,
        "recipes/form.html",
        {
            "tags": tags,
            "unit_choices": UNIT_CHOICES,
        },
    )


@login_required
def recipe_update_view(request, pk):
    """Edit an existing recipe."""
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        if not title:
            existing_ingredients_data = []
            for ri in recipe.recipe_ingredients.select_related("ingredient").all():
                existing_ingredients_data.append(
                    {
                        "name": ri.ingredient.name,
                        "quantity": str(ri.quantity) if ri.quantity else "",
                        "unit": ri.unit,
                        "notes": ri.preparation_notes,
                    }
                )
            return render(
                request,
                "recipes/form.html",
                {
                    "recipe": recipe,
                    "error": "Title is required.",
                    "tags": Tag.objects.all(),
                    "unit_choices": UNIT_CHOICES,
                    "update": True,
                    "existing_ingredients": json.dumps(existing_ingredients_data),
                },
            )

        recipe.title = title
        recipe.description = request.POST.get("description", "").strip()
        recipe.prep_time = int(request.POST["prep_time"]) if request.POST.get("prep_time") else None
        recipe.cook_time = int(request.POST["cook_time"]) if request.POST.get("cook_time") else None
        recipe.servings = int(request.POST.get("servings", 4))
        recipe.difficulty = request.POST.get("difficulty", "medium")
        recipe.source = request.POST.get("source", "manual")
        recipe.steps = request.POST.get("steps", "")
        recipe.notes = request.POST.get("notes", "")
        recipe.ingredients_text = request.POST.get("ingredients_text", "")
        recipe.shared = request.POST.get("shared") == "1"
        recipe.save()

        tag_ids = request.POST.getlist("tags")
        recipe.tags.set(tag_ids)

        _process_structured_ingredients(request, recipe)

        return redirect("recipe_detail", pk=recipe.pk)

    tags = Tag.objects.all()
    existing_ingredients = []
    for ri in recipe.recipe_ingredients.select_related("ingredient").all():
        existing_ingredients.append(
            {
                "name": ri.ingredient.name,
                "quantity": str(ri.quantity) if ri.quantity else "",
                "unit": ri.unit,
                "notes": ri.preparation_notes,
            }
        )

    return render(
        request,
        "recipes/form.html",
        {
            "recipe": recipe,
            "tags": tags,
            "unit_choices": UNIT_CHOICES,
            "update": True,
            "existing_ingredients": json.dumps(existing_ingredients),
        },
    )


@login_required
def recipe_delete_view(request, pk):
    """Delete confirmation and deletion."""
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
    if request.method == "POST":
        recipe.delete()
        return redirect("recipe_list")
    return render(request, "recipes/confirm_delete.html", {"recipe": recipe})


@login_required
def toggle_favourite_view(request, pk):
    """HTMX endpoint to toggle favourite status. Returns heart partial."""
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
    if request.user in recipe.favourited_by.all():
        recipe.favourited_by.remove(request.user)
        is_favourited = False
    else:
        recipe.favourited_by.add(request.user)
        is_favourited = True

    return render(
        request,
        "recipes/partials/favourite_button.html",
        {
            "recipe": recipe,
            "is_favourited": is_favourited,
        },
    )


@login_required
def ai_generate_recipe_api(request):
    """HTMX/JSON endpoint: generate a recipe from a prompt using AI."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    prompt = request.POST.get("ai_prompt", "").strip()
    if not prompt:
        return JsonResponse({"error": "Please describe what you'd like to cook."}, status=400)

    try:
        result = AIService.generate_structured_recipe(prompt)
        return JsonResponse(result)
    except AIServiceException as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def import_recipe_url(request):
    """HTMX/JSON endpoint: import a recipe from a URL using AI."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    url = request.POST.get("url", "").strip()
    if not url:
        return JsonResponse({"error": "Please provide a URL."}, status=400)

    try:
        result = AIService.import_recipe_from_url(url)
        return JsonResponse(result)
    except AIServiceException as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def image_search(request, pk):
    """HTMX: Search Unsplash for recipe images and display results."""
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)

    query = request.GET.get("q", recipe.title)
    access_key = settings.UNSPLASH_ACCESS_KEY

    if not access_key:
        return render(
            request,
            "recipes/partials/image_search.html",
            {
                "recipe": recipe,
                "error": "Unsplash API key not configured.",
            },
        )

    try:
        resp = http_requests.get(
            "https://api.unsplash.com/search/photos",
            params={
                "query": f"{query} food",
                "per_page": 8,
                "orientation": "landscape",
            },
            headers={"Authorization": f"Client-ID {access_key}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        photos = [
            {
                "id": p["id"],
                "thumb": p["urls"]["small"],
                "regular": p["urls"]["regular"],
                "alt": p.get("alt_description", query),
                "credit": p["user"]["name"],
                "credit_link": p["user"]["links"]["html"],
            }
            for p in data.get("results", [])
        ]
    except Exception:
        photos = []

    return render(
        request,
        "recipes/partials/image_search.html",
        {
            "recipe": recipe,
            "photos": photos,
            "query": query,
        },
    )


@login_required
def image_select(request, pk):
    """Save an Unsplash image URL to the recipe."""
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
    image_url = request.POST.get("image_url", "").strip()

    if image_url:
        recipe.image_url = image_url
        recipe.save(update_fields=["image_url"])

    return redirect("recipe_detail", pk=recipe.pk)
