from django.shortcuts import render, get_object_or_404, redirect
from .models import Recipe, MealPlan, Tag, FamilyPreference
from .forms import RecipeForm, MealPlanForm, FamilyPreferenceForm

from django.db.models import Q
import openai
from django.conf import settings

def recipe_list(request):
    query = request.GET.get('q')
    tag_id = request.GET.get('tag')
    family_member = request.GET.get('member')

    recipes = Recipe.objects.all()

    if query:
        recipes = recipes.filter(
            Q(title__icontains=query) |
            Q(ingredients__icontains=query)
        )

    if tag_id:
        recipes = recipes.filter(tags__id=tag_id)

    if family_member:
        recipes = recipes.filter(
            familypreference__family_member__iexact=family_member,
            familypreference__preference=3
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
        'selected_member': family_member,
    })



def recipe_create(request):
    form = RecipeForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('recipe_list')
    return render(request, 'recipes/recipe_form.html', {'form': form})

def recipe_detail(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    return render(request, 'recipes/recipe_detail.html', {'recipe': recipe})

def recipe_update(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    form = RecipeForm(request.POST or None, instance=recipe)
    if form.is_valid():
        form.save()
        return redirect('recipe_detail', pk=recipe.pk)
    return render(request, 'recipes/recipe_form.html', {'form': form, 'update': True})

def recipe_delete(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    if request.method == 'POST':
        recipe.delete()
        return redirect('recipe_list')
    return render(request, 'recipes/recipe_confirm_delete.html', {'recipe': recipe})

def ai_generate_recipe(request):
    generated_recipe = None
    error = None

    if request.method == 'POST':
        if 'prompt' in request.POST:
            # First form: prompt submitted
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
                generated_recipe = content.strip() if content is not None else None

            except Exception as e:
                error = str(e)

        elif 'use_recipe' in request.POST:
            # Second form: "Use this recipe" clicked
            raw = request.POST.get('generated_recipe', '')
            title, ingredients, steps = parse_generated_recipe(raw)

            # Save pre-filled data to session (could also pass via GET or hidden form)
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
    title = ""
    ingredients = ""
    steps = ""

    lines = text.splitlines()
    section = None
    buffer = []

    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("title:"):
            if buffer and section == "steps":
                steps = "\n".join(buffer).strip()
            buffer = []
            section = "title"
            continue
        elif stripped.lower().startswith("ingredients:"):
            if buffer and section == "title":
                title = "\n".join(buffer).strip()
            buffer = []
            section = "ingredients"
            continue
        elif stripped.lower().startswith("steps:"):
            if buffer and section == "ingredients":
                ingredients = "\n".join(buffer).strip()
            buffer = []
            section = "steps"
            continue
        elif stripped == "":
            continue
        else:
            buffer.append(stripped)

    # Catch the last section
    if section == "steps":
        steps = "\n".join(buffer).strip()

    return title, ingredients, steps

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

def meal_plan_list(request):
    plans = MealPlan.objects.order_by('date', 'meal_type')
    return render(request, 'recipes/meal_plan_list.html', {'plans': plans})

def meal_plan_create(request):
    form = MealPlanForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('meal_plan_list')
    return render(request, 'recipes/meal_plan_form.html', {'form': form})

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
