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


def _generate_shopping_items(household, user):
    """Generate ShoppingListItem records from this week's meal plan."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    meals = MealPlan.objects.filter(
        household=household,
        date__range=[monday, sunday],
    ).select_related("recipe")

    recipes = [m.recipe for m in meals]
    if not recipes:
        return

    generated_items = RecipeService.generate_structured_shopping_list(recipes)

    # Clear old generated items (keep manual ones)
    ShoppingListItem.objects.filter(household=household, is_generated=True).delete()

    for item in generated_items:
        qty_parts = []
        if item["total_quantity"]:
            qty_parts.append(str(item["total_quantity"].normalize()))
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

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    # Auto-generate if no generated items exist yet
    has_generated = ShoppingListItem.objects.filter(household=household, is_generated=True).exists()
    if not has_generated:
        _generate_shopping_items(household, request.user)

    # Get all items
    all_items = ShoppingListItem.objects.filter(household=household).select_related("added_by").order_by("checked", "category", "name")

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

    # Counts
    meal_count = MealPlan.objects.filter(household=household, date__range=[monday, sunday]).count()
    total_items = all_items.count()
    checked_items = all_items.filter(checked=True).count()

    return render(
        request,
        "shop/shop.html",
        {
            "categories": category_list,
            "manual_items": manual_items,
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
    """Regenerate the shopping list (clears all items and rebuilds from meal plan)."""
    household = get_household(request.user)
    if household:
        ShoppingListItem.objects.filter(household=household).delete()
        _generate_shopping_items(household, request.user)
    django_messages.success(request, "Shopping list regenerated!")
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
