from collections import defaultdict
from datetime import date, timedelta

from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
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


@login_required
def shop_view(request):
    """Full shopping list page."""
    household = get_household(request.user)
    if not household:
        return render(request, "shop/shop.html", {"categories": [], "manual_items": []})

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    # Get this week's meal plans
    meals = MealPlan.objects.filter(
        household=household,
        date__range=[monday, sunday],
    ).select_related("recipe")

    recipes = [m.recipe for m in meals]
    meal_count = len(recipes)

    # Generate structured shopping list from recipes
    generated_items = []
    if recipes:
        generated_items = RecipeService.generate_structured_shopping_list(recipes)

    # Group by category
    categories = defaultdict(list)
    for item in generated_items:
        cat = item["category"] or "other"
        categories[cat].append(item)

    # Build ordered categories list with emojis
    category_list = []
    for cat_key, cat_label in INGREDIENT_CATEGORY_CHOICES:
        if cat_key in categories:
            category_list.append(
                {
                    "key": cat_key,
                    "label": cat_label,
                    "icon": CATEGORY_ICONS.get(cat_key, "box"),
                    "items": categories[cat_key],
                }
            )

    # Manual items
    manual_items = ShoppingListItem.objects.filter(household=household).select_related("added_by")

    total_generated = len(generated_items)
    total_manual = manual_items.count()
    total_items = total_generated + total_manual
    checked_items = manual_items.filter(checked=True).count()

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
    """Regenerate the shopping list."""
    household = get_household(request.user)
    if household:
        ShoppingListItem.objects.filter(household=household).delete()
    django_messages.success(request, "Shopping list regenerated!")
    return redirect("shop")


@login_required
@require_POST
def shop_toggle(request, pk):
    """Toggle a ShoppingListItem's checked state."""
    from django.shortcuts import get_object_or_404

    household = get_household(request.user)
    item = get_object_or_404(ShoppingListItem, pk=pk, household=household)
    item.checked = not item.checked
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
