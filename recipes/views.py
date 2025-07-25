from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Count
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date
from django.utils import timezone
from datetime import date, timedelta

from .models import Recipe, MealPlan, Tag, FamilyPreference
from .forms import RecipeForm, MealPlanForm, FamilyPreferenceForm, CustomUserCreationForm
from .templatetags.recipe_extras import ai_generate_surprise_recipe

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
            Q(ingredients__icontains=query)
        )

    if tag_id:
        recipes = recipes.filter(tags__id=tag_id)

    if selected_members:
        recipes = recipes.annotate(
            matching_likes=Count(
                'familypreference',
                filter=Q(familypreference__preference=3, familypreference__family_member__in=selected_members, familypreference__user=request.user),
                distinct=True
            )
        ).filter(matching_likes=len(selected_members))

    if favourites_only:
        recipes = recipes.filter(favourited_by=request.user)

    recipes = recipes.annotate(
        total_likes=Count(
            'familypreference',
            filter=Q(familypreference__preference=3, familypreference__user=request.user),
            distinct=True
        )
    ).distinct().order_by('-created_at')

    # Pagination
    paginator = Paginator(recipes, 12)  # 12 recipes per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Only show upcoming meal plans (today and future)
    today = date.today()
    meal_plans = MealPlan.objects.filter(
        user=request.user,
        date__gte=today
    ).order_by('date', 'meal_type')
    tags = Tag.objects.all()
    family_members = FamilyPreference.objects.filter(user=request.user).values_list('family_member', flat=True).distinct()

    return render(request, 'recipes/recipe_list.html', {
        'page_obj': page_obj,
        'recipes': page_obj.object_list,
        'meal_plans': meal_plans,
        'tags': tags,
        'query': query,
        'selected_tag': int(tag_id) if tag_id else None,
        'family_members': family_members,
        'selected_members': selected_members,
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
    recipe = get_object_or_404(Recipe, pk=pk, user=request.user)
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
def ai_generate_recipe(request):
    generated_recipe = None
    error = None

    if request.method == 'POST':
        if 'prompt' in request.POST:
            prompt = request.POST.get('prompt')
            try:
                full_prompt = (
                    f"Create a family-friendly recipe using: {prompt}. "
                    f"Include a title, ingredients, and clear steps. Format as:\n"
                    f"Title:\nIngredients:\nSteps:"
                )

                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You're a helpful chef assistant."},
                        {"role": "user", "content": full_prompt},
                    ],
                    temperature=0.7
                )

                content = response.choices[0].message.content
                generated_recipe = content.strip() if content else None

            except Exception as e:
                error = str(e)

        elif 'use_recipe' in request.POST:
            raw = request.POST.get('generated_recipe', '')
            title, ingredients, steps = parse_generated_recipe(raw)

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

def parse_generated_recipe(text):
    import re

    # Use regex to robustly extract sections
    title = ""
    ingredients = ""
    steps = ""

    # Match "Title: ..." on a single line
    title_match = re.search(r"Title:\s*(.+)", text, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()

    # Match everything between "Ingredients:" and "Steps:" or "Directions:"
    ingredients_match = re.search(
        r"Ingredients:\s*([\s\S]*?)(?:\n(?:Steps:|Directions:))", text, re.IGNORECASE
    )
    if ingredients_match:
        ingredients = ingredients_match.group(1).strip()

    # Match everything after "Steps:" or "Directions:"
    steps_match = re.search(r"(?:Steps:|Directions:)\s*([\s\S]*)", text, re.IGNORECASE)
    if steps_match:
        steps = steps_match.group(1).strip()

    return title, ingredients, steps

@login_required
def meal_plan_list(request):
    plans = MealPlan.objects.filter(user=request.user).order_by('date', 'meal_type')
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
            meal_plan = form.save(commit=False)
            meal_plan.user = request.user
            meal_plan.save()
            # Redirect back to the weekly meal plan with the correct week offset
            return redirect(f"{reverse('meal_plan_week')}?week={week_offset}")
    else:
        form = MealPlanForm(initial=initial, user=request.user)
    return render(request, 'recipes/meal_plan_form.html', {'form': form})

@login_required
def add_preference(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id, user=request.user)
    form = FamilyPreferenceForm(request.POST or None)

    if form.is_valid():
        pref = form.save(commit=False)
        pref.recipe = recipe
        pref.user = request.user
        try:
            existing = FamilyPreference.objects.get(recipe=recipe, family_member=pref.family_member, user=request.user)
            existing.preference = pref.preference
            existing.save()
        except FamilyPreference.DoesNotExist:
            pref.save()
        return redirect('recipe_detail', pk=recipe_id)

    return render(request, 'recipes/add_preference.html', {
        'form': form,
        'recipe': recipe,
    })

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
            if recipe.ingredients:
                for line in recipe.ingredients.splitlines():
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
    ).order_by('date', 'meal_type')

    # Build a structure: {date: {breakfast: ..., lunch: ..., dinner: ...}}
    week_days = []
    meal_types = ['breakfast', 'lunch', 'dinner']
    for i in range(7):
        day_date = start_of_week + timedelta(days=i)
        day_plan = {mt: None for mt in meal_types}
        for plan in plans.filter(date=day_date):
            day_plan[plan.meal_type] = plan.recipe
        week_days.append({
            'date': day_date,
            'name': day_date.strftime('%A'),
            'is_today': (day_date == today),
            **day_plan
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
def ai_surprise_me(request):
    if request.method == "POST":
        ai_recipe_raw = ai_generate_surprise_recipe()
        # Parse the AI response into title, ingredients, steps
        title, ingredients, steps = parse_generated_recipe(ai_recipe_raw)
        request.session['ai_recipe_data'] = {
            'title': title,
            'ingredients': ingredients,
            'steps': steps,
            'is_ai_generated': True
        }
        return redirect('recipe_create_from_ai')
    return redirect('recipe_list')