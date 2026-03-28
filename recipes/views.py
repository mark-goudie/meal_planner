import json
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Count, Avg, Max
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden
from django.urls import reverse
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import date, timedelta
from django_ratelimit.decorators import ratelimit

from .models import (
    Recipe, MealPlan, Tag, MealPlannerPreferences,
    Ingredient, RecipeIngredient, CookingNote, UNIT_CHOICES,
)
from .forms import (
    RecipeForm, MealPlanForm, CustomUserCreationForm,
    MealPlannerPreferencesForm, WeeklyPlanGeneratorForm
)
from .services import (
    AIService, AIConfigurationError, AIValidationError, AIAPIError,
    MealPlanningAssistantService
)

import openai

# --------------------------
# Public Views
# --------------------------

def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("recipe_list")
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/register.html", {"form": form})

def privacy(request):
    return render(request, "legal/privacy.html")

def terms(request):
    return render(request, "legal/terms.html")

def disclaimer(request):
    return render(request, "legal/disclaimer.html")

# --------------------------
# Authenticated Views
# --------------------------

@login_required
def recipe_list(request):
    query = request.GET.get('q')
    tag_id = request.GET.get('tag')
    selected_members = request.GET.getlist('member')
    favourites_only = request.GET.get('favourites') == '1'

    recipes = Recipe.objects.filter(user=request.user)

    if query:
        recipes = recipes.filter(
            Q(title__icontains=query) |
            Q(ingredients_text__icontains=query)
        )

    if tag_id:
        recipes = recipes.filter(tags__id=tag_id)

    if favourites_only:
        recipes = recipes.filter(favourited_by=request.user)

    recipes = recipes.distinct().select_related(
        'user'
    ).prefetch_related(
        'tags',
        'favourited_by'
    ).order_by('-created_at')

    # Pagination
    paginator = Paginator(recipes, 12)  # 12 recipes per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Only show upcoming meal plans (today and future)
    today = date.today()
    meal_plans = MealPlan.objects.filter(
        user=request.user,
        date__gte=today
    ).select_related(
        'recipe'
    ).order_by('date', 'meal_type')
    tags = Tag.objects.all()

    return render(request, 'recipes/recipe_list.html', {
        'page_obj': page_obj,
        'recipes': page_obj.object_list,
        'meal_plans': meal_plans,
        'tags': tags,
        'query': query,
        'selected_tag': int(tag_id) if tag_id else None,
        'favourites_only': favourites_only,
    })

@login_required
def recipe_create(request):
    form = RecipeForm(request.POST or None)
    if form.is_valid():
        recipe = form.save(commit=False)
        recipe.user = request.user
        recipe.save()
        form.save_m2m()
        return redirect('recipe_list')
    return render(request, 'recipes/recipe_form.html', {'form': form})

@login_required
def recipe_create_from_ai(request):
    data = request.session.get('ai_recipe_data', {})
    form = RecipeForm(initial=data)

    if request.method == 'POST':
        form = RecipeForm(request.POST)
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.user = request.user
            recipe.save()
            form.save_m2m()
            request.session.pop('ai_recipe_data', None)
            return redirect('recipe_list')

    return render(request, 'recipes/recipe_form.html', {'form': form, 'update': False})

@login_required
def recipe_detail(request, pk):
    recipe = get_object_or_404(
        Recipe.objects.select_related('user').prefetch_related('tags', 'favourited_by'),
        pk=pk,
        user=request.user
    )
    return render(request, 'recipes/recipe_detail.html', {'recipe': recipe})

@login_required
def recipe_update(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
    form = RecipeForm(request.POST or None, instance=recipe)
    if form.is_valid():
        form.save()
        return redirect('recipe_detail', pk=recipe.pk)
    return render(request, 'recipes/recipe_form.html', {'form': form, 'update': True})

@login_required
def recipe_delete(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
    if request.method == 'POST':
        recipe.delete()
        return redirect('recipe_list')
    return render(request, 'recipes/recipe_confirm_delete.html', {'recipe': recipe})

@login_required
@ratelimit(key='user', rate='5/h', method='POST', block=True)
def ai_generate_recipe(request):
    generated_recipe = None
    error = None

    if request.method == 'POST':
        if 'prompt' in request.POST:
            prompt = request.POST.get('prompt')

            try:
                # Use AIService for generation
                generated_recipe = AIService.generate_recipe_from_prompt(prompt)

            except (AIConfigurationError, AIValidationError, AIAPIError) as e:
                error = str(e)

        elif 'use_recipe' in request.POST:
            raw = request.POST.get('generated_recipe', '')
            title, ingredients, steps = AIService.parse_generated_recipe(raw)

            request.session['ai_recipe_data'] = {
                'title': title,
                'ingredients': ingredients,
                'steps': steps,
                'is_ai_generated': True
            }
            return redirect('recipe_create_from_ai')

    return render(request, 'recipes/ai_generate.html', {
        'generated_recipe': generated_recipe,
        'error': error
    })

@login_required
def meal_plan_list(request):
    plans = MealPlan.objects.filter(
        user=request.user
    ).select_related(
        'recipe',
        'recipe__user'
    ).prefetch_related(
        'recipe__tags'
    ).order_by('date', 'meal_type')
    return render(request, 'recipes/meal_plan_list.html', {'plans': plans})

@login_required
def meal_plan_create(request):
    initial = {}
    # Pre-populate date and meal_type from query params if present
    if 'date' in request.GET:
        initial['date'] = request.GET['date']
    if 'meal_type' in request.GET:
        initial['meal_type'] = request.GET['meal_type']
    
    # Determine the week offset for redirect
    selected_date = parse_date(request.GET.get('date', str(date.today())))
    if selected_date is None:
        selected_date = date.today()
    week_offset = (selected_date - date.today()).days // 7

    if request.method == 'POST':
        form = MealPlanForm(request.POST, user=request.user)
        if form.is_valid():
            # Use get_or_create to handle duplicate meal plans
            # (unique constraint on user, date, meal_type)
            meal_plan, created = MealPlan.objects.update_or_create(
                user=request.user,
                date=form.cleaned_data['date'],
                meal_type=form.cleaned_data['meal_type'],
                defaults={'recipe': form.cleaned_data['recipe']}
            )
            # Redirect back to the weekly meal plan with the correct week offset
            return redirect(f"{reverse('meal_plan_week')}?week={week_offset}")
    else:
        form = MealPlanForm(initial=initial, user=request.user)
    return render(request, 'recipes/meal_plan_form.html', {'form': form})

@login_required
def toggle_favourite(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id, user=request.user)
    if request.user in recipe.favourited_by.all():
        recipe.favourited_by.remove(request.user)
    else:
        recipe.favourited_by.add(request.user)
    return HttpResponseRedirect(reverse('recipe_detail', args=[recipe.pk]))

@login_required
def generate_shopping_list(request):
    if request.method == "POST":
        recipe_ids = request.POST.getlist('recipe_ids')
        recipes = Recipe.objects.filter(id__in=recipe_ids, user=request.user)
        # Combine ingredients (assuming ingredients are stored as text, one per line)
        ingredient_set = set()
        for recipe in recipes:
            if recipe.ingredients_text:
                for line in recipe.ingredients_text.splitlines():
                    line = line.strip()
                    if line:
                        ingredient_set.add(line)
        shopping_list = sorted(ingredient_set)
        return render(request, 'recipes/shopping_list.html', {
            'shopping_list': shopping_list,
            'recipes': recipes,
        })
    # If GET or no recipes selected, redirect or show empty
    return render(request, 'recipes/shopping_list.html', {'shopping_list': [], 'recipes': []})

def getting_started(request):
    return render(request, "recipes/getting_started.html")

@login_required
def meal_plan_week(request):
    # Get week offset from query param (?week=0 for current, -1 for prev, 1 for next)
    week_offset = int(request.GET.get('week', 0))
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)

    # Fetch meal plans for this week
    plans = MealPlan.objects.filter(
        user=request.user,
        date__range=[start_of_week, end_of_week]
    ).select_related(
        'recipe',
        'recipe__user'
    ).prefetch_related(
        'recipe__tags'
    ).order_by('date', 'meal_type')

    # Build a structure: {date: {breakfast: ..., lunch: ..., dinner: ...}}
    # Convert to dict for efficient lookup
    plans_by_date = {}
    for plan in plans:
        if plan.date not in plans_by_date:
            plans_by_date[plan.date] = {}
        plans_by_date[plan.date][plan.meal_type] = plan.recipe

    week_days = []
    meal_types = ['breakfast', 'lunch', 'dinner']
    for i in range(7):
        day_date = start_of_week + timedelta(days=i)
        day_plan = plans_by_date.get(day_date, {})
        week_days.append({
            'date': day_date,
            'name': day_date.strftime('%A'),
            'is_today': (day_date == today),
            'breakfast': day_plan.get('breakfast'),
            'lunch': day_plan.get('lunch'),
            'dinner': day_plan.get('dinner'),
        })

    context = {
        'week_days': week_days,
        'week_start': start_of_week,
        'week_end': end_of_week,
        'prev_week': week_offset - 1,
        'next_week': week_offset + 1,
        'this_week': 0,
        'meal_types': meal_types,
    }
    return render(request, 'recipes/meal_plan_week.html', context)

@login_required
@ratelimit(key='user', rate='3/h', method='POST', block=True)
def ai_surprise_me(request):
    if request.method == "POST":
        try:
            # Use AIService for surprise recipe generation
            ai_recipe_raw = AIService.generate_surprise_recipe()
            # Parse the AI response into title, ingredients, steps
            title, ingredients, steps = AIService.parse_generated_recipe(ai_recipe_raw)
            request.session['ai_recipe_data'] = {
                'title': title,
                'ingredients': ingredients,
                'steps': steps,
                'is_ai_generated': True
            }
            return redirect('recipe_create_from_ai')
        except (AIConfigurationError, AIAPIError):
            # On error, redirect to recipe list
            return redirect('recipe_list')
    return redirect('recipe_list')


# --------------------------
# Smart Meal Planner Views
# --------------------------

@login_required
def meal_planner_preferences(request):
    """Configure smart meal planner preferences"""
    preferences = MealPlanningAssistantService.get_or_create_preferences(request.user)

    if request.method == 'POST':
        form = MealPlannerPreferencesForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            return redirect('smart_meal_planner')
    else:
        form = MealPlannerPreferencesForm(instance=preferences)

    return render(request, 'recipes/meal_planner_preferences.html', {
        'form': form,
        'preferences': preferences,
    })


@login_required
def smart_meal_planner(request):
    """Smart weekly meal plan generator"""
    preferences = MealPlanningAssistantService.get_or_create_preferences(request.user)

    if request.method == 'POST':
        form = WeeklyPlanGeneratorForm(request.POST)
        if form.is_valid():
            week_start = form.cleaned_data.get('week_start')
            meals_to_plan = form.cleaned_data.get('meals_to_plan')

            try:
                # Generate the plan
                plan = MealPlanningAssistantService.generate_weekly_plan(
                    user=request.user,
                    week_start=week_start,
                    meals_per_day=meals_to_plan
                )

                return redirect('meal_plan_week')

            except ValueError as e:
                form.add_error(None, str(e))
    else:
        form = WeeklyPlanGeneratorForm()

    return render(request, 'recipes/smart_meal_planner.html', {
        'form': form,
        'preferences': preferences,
    })


# --------------------------
# Redesign Views — This Week
# --------------------------

def _get_week_dates(offset=0):
    """Get Monday-Sunday dates for a given week offset."""
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return [monday + timedelta(days=i) for i in range(7)]


def _build_week_context(user, offset=0):
    """Build template context for the weekly view."""
    dates = _get_week_dates(offset)
    start, end = dates[0], dates[-1]
    meals = MealPlan.objects.with_related().for_user(user).in_date_range(start, end)
    meal_lookup = {(m.date, m.meal_type): m for m in meals}

    days = []
    for d in dates:
        meal = meal_lookup.get((d, 'dinner'))
        days.append({
            'date': d,
            'day_name': d.strftime('%a'),
            'day_num': d.day,
            'is_today': d == date.today(),
            'meal': meal,
        })

    return {
        'days': days,
        'week_start': start,
        'week_end': end,
        'offset': offset,
    }


@login_required
def week_view(request):
    """This Week — full page weekly meal plan view."""
    offset = int(request.GET.get('offset', 0))
    context = _build_week_context(request.user, offset)
    return render(request, 'week/week.html', context)


@login_required
def week_slot(request, date_str, meal_type):
    """HTMX partial: return a single day card."""
    from datetime import datetime as dt
    slot_date = dt.strptime(date_str, '%Y-%m-%d').date()

    meal = MealPlan.objects.with_related().for_user(request.user).filter(
        date=slot_date, meal_type=meal_type
    ).first()

    day = {
        'date': slot_date,
        'day_name': slot_date.strftime('%a'),
        'day_num': slot_date.day,
        'is_today': slot_date == date.today(),
        'meal': meal,
    }
    return render(request, 'week/partials/meal_card.html', {'day': day})


@login_required
def week_assign(request, date_str, meal_type):
    """HTMX partial: recipe picker (GET) or assign a recipe (POST)."""
    from datetime import datetime as dt
    slot_date = dt.strptime(date_str, '%Y-%m-%d').date()

    if request.method == 'POST':
        recipe_id = request.POST.get('recipe_id')
        recipe = get_object_or_404(Recipe, pk=recipe_id, user=request.user)

        MealPlan.objects.update_or_create(
            user=request.user,
            date=slot_date,
            meal_type=meal_type,
            defaults={'recipe': recipe},
        )

        meal = MealPlan.objects.with_related().for_user(request.user).filter(
            date=slot_date, meal_type=meal_type
        ).first()

        day = {
            'date': slot_date,
            'day_name': slot_date.strftime('%a'),
            'day_num': slot_date.day,
            'is_today': slot_date == date.today(),
            'meal': meal,
        }
        return render(request, 'week/partials/meal_card.html', {'day': day})

    # GET — show recipe picker
    search_query = request.GET.get('q', '').strip()
    recipes = Recipe.objects.for_user(request.user)
    if search_query:
        recipes = recipes.search(search_query)
    recipes = recipes.order_by('title')

    return render(request, 'week/partials/recipe_picker.html', {
        'recipes': recipes,
        'date_str': date_str,
        'meal_type': meal_type,
        'day_label': f"{slot_date.strftime('%A %d %b')}",
        'search_query': search_query,
    })


@login_required
def week_suggest(request):
    """Placeholder for AI meal suggestions — returns empty response."""
    from django.http import HttpResponse
    return HttpResponse('')


# --------------------------
# Redesign Views — Auth
# --------------------------

def register_view(request):
    """New-style registration view that redirects to week view."""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('week')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


# --------------------------
# Redesign Views — Placeholders
# --------------------------

@login_required
def shop_placeholder(request):
    """Placeholder shopping list page."""
    return render(request, 'week/placeholder.html', {
        'title': 'Shopping List',
        'message': 'Coming soon!',
    })


@login_required
def settings_placeholder(request):
    """Placeholder settings page."""
    return render(request, 'week/placeholder.html', {
        'title': 'Settings',
        'message': 'Coming soon!',
    })


# --------------------------
# Redesign Views — Recipes
# --------------------------

def _get_sorted_recipes(queryset, sort, user):
    """Apply sort ordering to a recipe queryset."""
    from django.db.models import F

    if sort == 'rating':
        return queryset.annotate(
            avg_rating=Avg('cooking_notes__rating')
        ).order_by(F('avg_rating').desc(nulls_last=True), '-created_at')
    elif sort == 'times_cooked':
        return queryset.annotate(
            cook_count_val=Count('cooking_notes')
        ).order_by('-cook_count_val', '-created_at')
    elif sort == 'recently_cooked':
        return queryset.annotate(
            last_cooked=Max('cooking_notes__cooked_date')
        ).order_by(F('last_cooked').desc(nulls_last=True), '-created_at')
    else:  # 'newest' or default
        return queryset.order_by('-created_at')


@login_required
def recipe_list_view(request):
    """Recipe Collection — full page view with search, filter, sort."""
    recipes = Recipe.objects.for_user(request.user).with_related()

    query = request.GET.get('q', '').strip()
    tag_id = request.GET.get('tag', '')
    sort = request.GET.get('sort', 'newest')
    favourites_only = request.GET.get('favourites') == '1'

    if query:
        recipes = recipes.search(query)

    if tag_id:
        recipes = recipes.with_tag(tag_id)

    if favourites_only:
        recipes = recipes.favourited_by_user(request.user)

    recipes = _get_sorted_recipes(recipes, sort, request.user)

    paginator = Paginator(recipes, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    tags = Tag.objects.all()

    return render(request, 'recipes/list.html', {
        'page_obj': page_obj,
        'recipes': page_obj.object_list,
        'tags': tags,
        'query': query,
        'selected_tag': int(tag_id) if tag_id else None,
        'sort': sort,
        'favourites_only': favourites_only,
    })


@login_required
def recipe_search(request):
    """HTMX partial — returns filtered recipe cards without page wrapper."""
    recipes = Recipe.objects.for_user(request.user).with_related()

    query = request.GET.get('q', '').strip()
    tag_id = request.GET.get('tag', '')
    sort = request.GET.get('sort', 'newest')
    favourites_only = request.GET.get('favourites') == '1'

    if query:
        recipes = recipes.search(query)

    if tag_id:
        recipes = recipes.with_tag(tag_id)

    if favourites_only:
        recipes = recipes.favourited_by_user(request.user)

    recipes = _get_sorted_recipes(recipes, sort, request.user)

    paginator = Paginator(recipes, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recipes/partials/search_results.html', {
        'page_obj': page_obj,
        'recipes': page_obj.object_list,
        'query': query,
        'selected_tag': int(tag_id) if tag_id else None,
        'sort': sort,
        'favourites_only': favourites_only,
    })


@login_required
def recipe_detail_view(request, pk):
    """Recipe Detail — full page view with ingredients, steps, notes."""
    recipe = get_object_or_404(
        Recipe.objects.select_related('user').prefetch_related(
            'tags', 'favourited_by',
            'recipe_ingredients__ingredient',
            'cooking_notes',
        ),
        pk=pk,
        user=request.user,
    )
    structured_ingredients = recipe.recipe_ingredients.all()
    cooking_notes = recipe.cooking_notes.all()
    is_favourited = request.user in recipe.favourited_by.all()

    return render(request, 'recipes/detail.html', {
        'recipe': recipe,
        'structured_ingredients': structured_ingredients,
        'cooking_notes': cooking_notes,
        'is_favourited': is_favourited,
    })


def _process_structured_ingredients(request, recipe):
    """Process dynamically named ingredient fields from the form POST."""
    # Clear existing structured ingredients
    recipe.recipe_ingredients.all().delete()

    count = int(request.POST.get('ingredient_count', 0))
    for i in range(count):
        name = request.POST.get(f'ing_name_{i}', '').strip()
        if not name:
            continue
        ingredient, _ = Ingredient.objects.get_or_create(
            name=name.lower(),
            defaults={'category': 'other'},
        )
        qty = request.POST.get(f'ing_qty_{i}', '').strip()
        try:
            quantity = Decimal(qty) if qty else None
        except (InvalidOperation, ValueError):
            quantity = None
        RecipeIngredient.objects.create(
            recipe=recipe,
            ingredient=ingredient,
            quantity=quantity,
            unit=request.POST.get(f'ing_unit_{i}', ''),
            preparation_notes=request.POST.get(f'ing_notes_{i}', '').strip(),
            order=i,
        )


@login_required
def recipe_create_view(request):
    """Create a new recipe with structured ingredient entry."""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            return render(request, 'recipes/form.html', {
                'error': 'Title is required.',
                'unit_choices': UNIT_CHOICES,
            })

        recipe = Recipe.objects.create(
            user=request.user,
            title=title,
            description=request.POST.get('description', '').strip(),
            prep_time=int(request.POST['prep_time']) if request.POST.get('prep_time') else None,
            cook_time=int(request.POST['cook_time']) if request.POST.get('cook_time') else None,
            servings=int(request.POST.get('servings', 4)),
            difficulty=request.POST.get('difficulty', 'medium'),
            source=request.POST.get('source', 'manual'),
            steps=request.POST.get('steps', ''),
            notes=request.POST.get('notes', ''),
            ingredients_text=request.POST.get('ingredients_text', ''),
        )
        # Tags
        tag_ids = request.POST.getlist('tags')
        if tag_ids:
            recipe.tags.set(tag_ids)

        _process_structured_ingredients(request, recipe)

        return redirect('recipe_detail', pk=recipe.pk)

    tags = Tag.objects.all()
    return render(request, 'recipes/form.html', {
        'tags': tags,
        'unit_choices': UNIT_CHOICES,
    })


@login_required
def recipe_update_view(request, pk):
    """Edit an existing recipe."""
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            existing_ingredients_data = []
            for ri in recipe.recipe_ingredients.select_related('ingredient').all():
                existing_ingredients_data.append({
                    'name': ri.ingredient.name,
                    'quantity': str(ri.quantity) if ri.quantity else '',
                    'unit': ri.unit,
                    'notes': ri.preparation_notes,
                })
            return render(request, 'recipes/form.html', {
                'recipe': recipe,
                'error': 'Title is required.',
                'tags': Tag.objects.all(),
                'unit_choices': UNIT_CHOICES,
                'update': True,
                'existing_ingredients': json.dumps(existing_ingredients_data),
            })

        recipe.title = title
        recipe.description = request.POST.get('description', '').strip()
        recipe.prep_time = int(request.POST['prep_time']) if request.POST.get('prep_time') else None
        recipe.cook_time = int(request.POST['cook_time']) if request.POST.get('cook_time') else None
        recipe.servings = int(request.POST.get('servings', 4))
        recipe.difficulty = request.POST.get('difficulty', 'medium')
        recipe.source = request.POST.get('source', 'manual')
        recipe.steps = request.POST.get('steps', '')
        recipe.notes = request.POST.get('notes', '')
        recipe.ingredients_text = request.POST.get('ingredients_text', '')
        recipe.save()

        tag_ids = request.POST.getlist('tags')
        recipe.tags.set(tag_ids)

        _process_structured_ingredients(request, recipe)

        return redirect('recipe_detail', pk=recipe.pk)

    tags = Tag.objects.all()
    existing_ingredients = []
    for ri in recipe.recipe_ingredients.select_related('ingredient').all():
        existing_ingredients.append({
            'name': ri.ingredient.name,
            'quantity': str(ri.quantity) if ri.quantity else '',
            'unit': ri.unit,
            'notes': ri.preparation_notes,
        })

    return render(request, 'recipes/form.html', {
        'recipe': recipe,
        'tags': tags,
        'unit_choices': UNIT_CHOICES,
        'update': True,
        'existing_ingredients': json.dumps(existing_ingredients),
    })


@login_required
def recipe_delete_view(request, pk):
    """Delete confirmation and deletion."""
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
    if request.method == 'POST':
        recipe.delete()
        return redirect('recipe_list')
    return render(request, 'recipes/confirm_delete.html', {'recipe': recipe})


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

    return render(request, 'recipes/partials/favourite_button.html', {
        'recipe': recipe,
        'is_favourited': is_favourited,
    })