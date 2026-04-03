import logging
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..models import Ingredient, Recipe, RecipeIngredient, Tag
from ..models.recipe import normalize_category
from ..services.ai_service import AIService, AIServiceException
from ..utils.units import normalize_unit

logger = logging.getLogger(__name__)

CUISINE_OPTIONS = [
    "Italian",
    "Asian",
    "Mexican",
    "Mediterranean",
    "Indian",
    "Japanese",
    "Middle Eastern",
    "French",
    "Korean",
    "American",
    "Thai",
    "Greek",
]
PROTEIN_OPTIONS = ["Chicken", "Beef", "Pork", "Seafood", "Lamb", "Tofu", "Eggs"]
DIETARY_OPTIONS = ["Vegetarian", "Vegan", "Gluten-free", "Dairy-free", "Low-carb"]
STYLE_OPTIONS = [
    "Quick weeknight",
    "Slow cook",
    "One-pot",
    "BBQ / Grill",
    "Meal prep",
    "Comfort food",
    "Healthy / Light",
]
AVOID_OPTIONS = [
    "Spicy",
    "Mushrooms",
    "Olives",
    "Shellfish",
    "Offal",
    "Raw fish",
    "Nuts",
]
COUNT_OPTIONS = [5, 10, 15, 20]


@login_required
def generate_preferences(request):
    """GET: show preference selection page. POST: store preferences, redirect to progress."""
    if request.method == "POST":
        request.session["gen_cuisines"] = request.POST.getlist("cuisines")
        request.session["gen_proteins"] = request.POST.getlist("proteins")
        request.session["gen_dietary"] = request.POST.getlist("dietary")
        request.session["gen_styles"] = request.POST.getlist("styles")
        request.session["gen_avoid"] = request.POST.getlist("avoid")
        count = int(request.POST.get("count", 10))
        request.session["gen_count"] = min(count, 20)
        request.session["gen_completed"] = 0
        request.session["gen_titles"] = []
        return redirect("generate_progress")

    return render(
        request,
        "recipes/generate.html",
        {
            "cuisines": CUISINE_OPTIONS,
            "proteins": PROTEIN_OPTIONS,
            "dietary": DIETARY_OPTIONS,
            "styles": STYLE_OPTIONS,
            "avoid": AVOID_OPTIONS,
            "counts": COUNT_OPTIONS,
        },
    )


@login_required
def generate_progress(request):
    """Show the progress page that polls for recipe generation."""
    count = request.session.get("gen_count", 0)
    completed = request.session.get("gen_completed", 0)
    if not count:
        return redirect("generate_preferences")
    return render(
        request,
        "recipes/generate_progress.html",
        {
            "total": count,
            "completed": completed,
        },
    )


@login_required
def generate_next(request):
    """HTMX endpoint: generate one recipe, return card + trigger next poll."""
    count = request.session.get("gen_count", 0)
    completed = request.session.get("gen_completed", 0)
    titles = request.session.get("gen_titles", [])

    if completed >= count:
        # Clean up session keys
        for key in [
            "gen_count",
            "gen_completed",
            "gen_titles",
            "gen_cuisines",
            "gen_proteins",
            "gen_dietary",
            "gen_styles",
            "gen_avoid",
        ]:
            request.session.pop(key, None)
        return render(
            request,
            "recipes/partials/generate_complete.html",
            {
                "total": count,
            },
        )

    # Build prompt from preferences
    cuisines = request.session.get("gen_cuisines", [])
    proteins = request.session.get("gen_proteins", [])
    dietary = request.session.get("gen_dietary", [])
    styles = request.session.get("gen_styles", [])
    avoid = request.session.get("gen_avoid", [])

    # Also get existing recipe titles to avoid duplicates
    existing_titles = list(
        Recipe.objects.filter(user=request.user).values_list("title", flat=True)
    )
    all_titles = existing_titles + titles

    prompt_parts = [
        "Generate a unique family-friendly dinner recipe.",
        "IMPORTANT: Pick ONE cuisine and ONE cooking style from the options below. "
        "Do NOT combine all of them into one recipe.",
        f"This is recipe {completed + 1} of {count} — vary the cuisine and style across the batch.",
    ]
    if cuisines:
        prompt_parts.append(f"Choose ONE cuisine from: {', '.join(cuisines)}")
    if proteins:
        prompt_parts.append(f"Choose ONE protein from: {', '.join(proteins)}")
    if dietary:
        prompt_parts.append(
            f"Dietary requirements (must follow all): {', '.join(dietary)}"
        )
    if styles:
        prompt_parts.append(f"Choose ONE cooking style from: {', '.join(styles)}")
    if avoid:
        prompt_parts.append(f"Must NOT contain: {', '.join(avoid)}")
    if all_titles:
        prompt_parts.append(f"Must be different from: {', '.join(all_titles[-20:])}")

    prompt = "\n".join(prompt_parts)

    try:
        data = AIService.generate_structured_recipe(prompt, max_prompt_length=2000)

        # Save recipe
        recipe = Recipe.objects.create(
            user=request.user,
            title=data.get("title", f"Recipe {completed + 1}"),
            description=data.get("description", ""),
            prep_time=data.get("prep_time"),
            cook_time=data.get("cook_time"),
            servings=data.get("servings", 4),
            difficulty=data.get("difficulty", "medium"),
            source="ai",
            is_ai_generated=True,
            steps="\n".join(data.get("steps", [])),
        )

        # Save structured ingredients
        for i, ing_data in enumerate(data.get("ingredients", [])):
            name = ing_data.get("name", "").lower().strip()
            if not name:
                continue  # Skip empty ingredient names
            category = normalize_category(ing_data.get("category", "other"))
            ingredient, _ = Ingredient.objects.get_or_create(
                name=name,
                defaults={"category": category},
            )
            qty = ing_data.get("quantity")
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                quantity=Decimal(str(qty)) if qty else None,
                unit=normalize_unit(ing_data.get("unit", "")),
                preparation_notes=ing_data.get("preparation_notes", ""),
                order=i,
            )

        # Auto-tag based on cuisine preferences
        for cuisine in cuisines:
            tag, _ = Tag.objects.get_or_create(
                name=cuisine, defaults={"tag_type": "cuisine"}
            )
            recipe.tags.add(tag)

        # Update session progress
        titles.append(recipe.title)
        request.session["gen_completed"] = completed + 1
        request.session["gen_titles"] = titles

        return render(
            request,
            "recipes/partials/generate_item.html",
            {
                "recipe": recipe,
                "completed": completed + 1,
                "total": count,
                "done": (completed + 1) >= count,
            },
        )

    except AIServiceException as e:
        logger.error(f"Recipe generation failed: {e}")
        # Skip this one, increment counter, try next
        request.session["gen_completed"] = completed + 1
        return render(
            request,
            "recipes/partials/generate_item.html",
            {
                "error": str(e),
                "completed": completed + 1,
                "total": count,
                "done": (completed + 1) >= count,
            },
        )
