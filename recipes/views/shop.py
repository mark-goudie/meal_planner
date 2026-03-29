from datetime import date, timedelta

from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..models import INGREDIENT_CATEGORY_CHOICES, MealPlan, ShoppingListItem
from ..models.household import get_household
from ..services import RecipeService

CATEGORY_ICONS = {
    "meat": "basket2-fill",
    "dairy": "cup-straw",
    "produce": "flower2",
    "pantry": "archive",
    "spices": "fire",
    "frozen": "snow2",
    "bakery": "bag",
    "other": "box",
}


def _get_week_range():
    """Get Monday-Sunday for the current week."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _generate_shopping_items(household, user, meal_ids=None):
    """Generate ShoppingListItem records from selected meals.

    Args:
        household: The household to generate for
        user: The user triggering the generation
        meal_ids: List of MealPlan IDs to include. If None, includes today and future meals this week.
    """
    monday, sunday = _get_week_range()

    if meal_ids is not None:
        meals = MealPlan.objects.filter(
            household=household,
            pk__in=meal_ids,
        ).select_related("recipe")
    else:
        # Default: today and future meals only
        meals = MealPlan.objects.filter(
            household=household,
            date__range=[date.today(), sunday],
        ).select_related("recipe")

    recipes = [m.recipe for m in meals]
    if not recipes:
        ShoppingListItem.objects.filter(household=household, is_generated=True).delete()
        return

    generated_items = RecipeService.generate_structured_shopping_list(recipes)

    # Clear old generated items (keep manual ones)
    ShoppingListItem.objects.filter(household=household, is_generated=True).delete()

    for item in generated_items:
        qty_parts = []
        if item["total_quantity"]:
            qty_parts.append(f"{float(item['total_quantity']):g}")
        if item["unit"]:
            qty_parts.append(item["unit"])
        quantity_str = " ".join(qty_parts)

        ShoppingListItem.objects.create(
            household=household,
            added_by=user,
            name=item["ingredient"].name,
            quantity=quantity_str,
            category=item["category"] or "other",
            recipe_sources=", ".join(sorted(item["recipes"])),
            is_generated=True,
        )


@login_required
def shop_view(request):
    """Full shopping list page."""
    household = get_household(request.user)
    if not household:
        return render(request, "shop/shop.html", {"categories": [], "items": []})

    monday, sunday = _get_week_range()
    today = date.today()

    # Auto-generate if no generated items exist yet
    has_generated = ShoppingListItem.objects.filter(household=household, is_generated=True).exists()
    if not has_generated:
        _generate_shopping_items(household, request.user)

    # Get all items
    all_items = (
        ShoppingListItem.objects.filter(household=household)
        .select_related("added_by")
        .order_by("checked", "category", "name")
    )

    # Group generated items by category
    from collections import defaultdict

    categories_map = defaultdict(list)
    manual_items = []
    for item in all_items:
        if item.is_generated:
            categories_map[item.category].append(item)
        else:
            manual_items.append(item)

    category_list = []
    for cat_key, cat_label in INGREDIENT_CATEGORY_CHOICES:
        if cat_key in categories_map:
            category_list.append(
                {
                    "key": cat_key,
                    "label": cat_label,
                    "icon": CATEGORY_ICONS.get(cat_key, "box"),
                    "items": categories_map[cat_key],
                }
            )

    # Build meal selector: all meals this week with past/future indicator
    week_meals = (
        MealPlan.objects.filter(household=household, date__range=[monday, sunday])
        .select_related("recipe")
        .order_by("date")
    )
    meal_selector = []
    for meal in week_meals:
        meal_selector.append(
            {
                "id": meal.pk,
                "date": meal.date,
                "day_name": meal.date.strftime("%a"),
                "day_num": meal.date.day,
                "recipe_title": meal.recipe.title,
                "is_past": meal.date < today,
                "is_today": meal.date == today,
            }
        )

    meal_count = len([m for m in meal_selector if not m["is_past"]])
    total_items = all_items.count()
    checked_items = all_items.filter(checked=True).count()

    return render(
        request,
        "shop/shop.html",
        {
            "categories": category_list,
            "manual_items": manual_items,
            "meal_selector": meal_selector,
            "week_start": monday,
            "week_end": sunday,
            "meal_count": meal_count,
            "total_items": total_items,
            "checked_items": checked_items,
        },
    )


@login_required
@require_POST
def shop_generate(request):
    """Regenerate the shopping list from selected meals."""
    household = get_household(request.user)
    if not household:
        return redirect("shop")

    meal_ids = request.POST.getlist("meals")
    if meal_ids:
        _generate_shopping_items(household, request.user, meal_ids=[int(m) for m in meal_ids])
    else:
        # No meals selected — clear generated items
        ShoppingListItem.objects.filter(household=household, is_generated=True).delete()

    django_messages.success(request, "Shopping list updated!")
    return redirect("shop")


@login_required
@require_POST
def shop_toggle(request, pk):
    """Toggle a ShoppingListItem's checked state."""
    household = get_household(request.user)
    item = get_object_or_404(ShoppingListItem, pk=pk, household=household)
    item.checked = not item.checked
    item.save()
    return render(request, "shop/partials/item.html", {"item": item})


@login_required
@require_POST
def shop_update_qty(request, pk):
    """Update a ShoppingListItem's quantity."""
    household = get_household(request.user)
    item = get_object_or_404(ShoppingListItem, pk=pk, household=household)
    quantity = request.POST.get("quantity", "").strip()
    item.quantity = quantity
    item.save()
    return render(request, "shop/partials/item.html", {"item": item})


@login_required
@require_POST
def shop_add(request):
    """Add a manual shopping list item."""
    household = get_household(request.user)
    name = request.POST.get("name", "").strip()
    if name and household:
        item = ShoppingListItem.objects.create(
            household=household,
            added_by=request.user,
            name=name,
        )
        return render(request, "shop/partials/item.html", {"item": item})
    return HttpResponse("")
