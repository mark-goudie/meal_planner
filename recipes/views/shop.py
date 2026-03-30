from datetime import date, timedelta

from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
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
    today = timezone.localdate()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _get_shop_date_range():
    """Get the date range for the meal selector: today through end of next week."""
    today = timezone.localdate()
    monday = today - timedelta(days=today.weekday())
    next_sunday = monday + timedelta(days=13)  # end of next week
    return today, next_sunday


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
        # Default: today through end of next week
        shop_start, shop_end = _get_shop_date_range()
        meals = MealPlan.objects.filter(
            household=household,
            date__range=[shop_start, shop_end],
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
    today = timezone.localdate()

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

    # Build meal selector: today through end of next week
    shop_start, shop_end = _get_shop_date_range()
    next_monday = monday + timedelta(days=7)

    upcoming_meals = (
        MealPlan.objects.filter(household=household, date__range=[shop_start, shop_end])
        .select_related("recipe")
        .order_by("date")
    )
    # Check if we have a stored selection from a previous generate action
    selected_meal_ids = request.session.pop("shop_selected_meals", None)

    meal_selector = []
    for meal in upcoming_meals:
        # If we have stored selection, use it. Otherwise default all to checked.
        if selected_meal_ids is not None:
            is_selected = meal.pk in selected_meal_ids
        else:
            is_selected = True
        meal_selector.append(
            {
                "id": meal.pk,
                "date": meal.date,
                "day_name": meal.date.strftime("%a"),
                "day_num": meal.date.day,
                "month": meal.date.strftime("%b"),
                "recipe_title": meal.recipe.title,
                "is_today": meal.date == today,
                "is_next_week": meal.date >= next_monday,
                "is_selected": is_selected,
            }
        )

    this_week_meals = [m for m in meal_selector if not m["is_next_week"]]
    next_week_meals = [m for m in meal_selector if m["is_next_week"]]
    meal_count = len([m for m in meal_selector if m["is_selected"]])
    total_items = all_items.count()
    checked_items = all_items.filter(checked=True).count()

    return render(
        request,
        "shop/shop.html",
        {
            "categories": category_list,
            "manual_items": manual_items,
            "meal_selector": meal_selector,
            "this_week_meals": this_week_meals,
            "next_week_meals": next_week_meals,
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
    selected_ids = [int(m) for m in meal_ids] if meal_ids else []
    if selected_ids:
        _generate_shopping_items(household, request.user, meal_ids=selected_ids)
    else:
        # No meals selected — clear generated items
        ShoppingListItem.objects.filter(household=household, is_generated=True).delete()

    # Store selected meal IDs in session so the page remembers the selection
    request.session["shop_selected_meals"] = selected_ids

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
