from django.shortcuts import render, get_object_or_404, redirect, get_list_or_404
from django.db.models import Q, Count
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse

from .models import Recipe, MealPlan, Tag, FamilyPreference
from .forms import RecipeForm, MealPlanForm, FamilyPreferenceForm

import openai

# --------------------------
# Public Views
# --------------------------

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('recipe_list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


# --------------------------
# Authenticated Views
# --------------------------

@login_required
def recipe_list(request):
    query = request.GET.get('q')
    tag_id = request.GET.get('tag')
    selected_members = request.GET.getlist('member')
    favourites_only = request.GET.get('favourites') == '1'

    recipes = Recipe.objects.all()

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
                filter=Q(familypreference__preference=3, familypreference__family_member__in=selected_members),
                distinct=True
            )
        ).filter(matching_likes=len(selected_members))

    if favourites_only:
        recipes = recipes.filter(favourited_by=request.user)

    recipes = recipes.annotate(
        total_likes=Count(
            'familypreference',
            filter=Q(familypreference__preference=3),
            distinct=True
        )
    ).distinct()

    meal_plans = MealPlan.objects.order_by('date', 'meal_type')
    tags = Tag.objects.all()
    family_members = FamilyPreference.objects.values_list('family_member', flat=True).distinct()

    return render(request, 'recipes/recipe_list.html', {
        'recipes': recipes,
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
        form.save()
        return redirect('recipe_list')
    return render(request, 'recipes/recipe_form.html', {'form': form})

@login_required
def recipe_create_from_ai(request):
    data = request.session.get('ai_recipe_data', {})
    form = RecipeForm(initial=data)

    if request.method == 'POST':
        form = RecipeForm(request.POST)
        if form.is_valid():
            form.save()
            request.session.pop('ai_recipe_data', None)
            return redirect('recipe_list')

    return render(request, 'recipes/recipe_form.html', {'form': form, 'update': False})

@login_required
def recipe_detail(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    return render(request, 'recipes/recipe_detail.html', {'recipe': recipe})

@login_required
def recipe_update(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    form = RecipeForm(request.POST or None, instance=recipe)
    if form.is_valid():
        form.save()
        return redirect('recipe_detail', pk=recipe.pk)
    return render(request, 'recipes/recipe_form.html', {'form': form, 'update': True})

@login_required
def recipe_delete(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
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
    title, ingredients, steps = "", "", ""
    section, buffer = None, []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("title:"):
            if buffer and section == "steps":
                steps = "\n".join(buffer).strip()
            buffer = []
            section = "title"
        elif stripped.lower().startswith("ingredients:"):
            if buffer and section == "title":
                title = "\n".join(buffer).strip()
            buffer = []
            section = "ingredients"
        elif stripped.lower().startswith("steps:"):
            if buffer and section == "ingredients":
                ingredients = "\n".join(buffer).strip()
            buffer = []
            section = "steps"
        elif stripped:
            buffer.append(stripped)

    if section == "steps":
        steps = "\n".join(buffer).strip()

    return title, ingredients, steps

@login_required
def meal_plan_list(request):
    plans = MealPlan.objects.order_by('date', 'meal_type')
    return render(request, 'recipes/meal_plan_list.html', {'plans': plans})

@login_required
def meal_plan_create(request):
    form = MealPlanForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('meal_plan_list')
    return render(request, 'recipes/meal_plan_form.html', {'form': form})

@login_required
def add_preference(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    form = FamilyPreferenceForm(request.POST or None)

    if form.is_valid():
        pref = form.save(commit=False)
        pref.recipe = recipe
        try:
            existing = FamilyPreference.objects.get(recipe=recipe, family_member=pref.family_member)
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
    recipe = get_object_or_404(Recipe, id=recipe_id)
    if request.user in recipe.favourited_by.all():
        recipe.favourited_by.remove(request.user)
    else:
        recipe.favourited_by.add(request.user)
    return HttpResponseRedirect(reverse('recipe_detail', args=[recipe.pk]))

@login_required
def generate_shopping_list(request):
    if request.method == "POST":
        recipe_ids = request.POST.getlist('recipe_ids')
        recipes = Recipe.objects.filter(id__in=recipe_ids)
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