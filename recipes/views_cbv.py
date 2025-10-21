"""
Class-Based Views for the recipes app.

This module contains class-based view implementations following Django best practices
for better code reusability, composition, and testability.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
)
from django.urls import reverse_lazy, reverse
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator
from django.db.models import Q, Count
from datetime import date

from .models import Recipe, MealPlan, Tag, FamilyPreference
from .forms import RecipeForm, MealPlanForm, FamilyPreferenceForm
from .services import RecipeService, MealPlanService


class UserRecipeAccessMixin(UserPassesTestMixin):
    """Mixin to ensure users can only access their own recipes."""

    def test_func(self):
        recipe = self.get_object()
        return recipe.user == self.request.user


class RecipeListView(LoginRequiredMixin, ListView):
    """
    List view for recipes with filtering and search capabilities.
    """
    model = Recipe
    template_name = 'recipes/recipe_list.html'
    context_object_name = 'recipes'
    paginate_by = 12

    def get_queryset(self):
        """Get filtered and optimized recipe queryset."""
        user = self.request.user
        query = self.request.GET.get('q')
        tag_id = self.request.GET.get('tag')
        selected_members = self.request.GET.getlist('member')
        favourites_only = self.request.GET.get('favourites') == '1'

        # Use service layer for business logic
        recipes = RecipeService.get_recipes_for_user(
            user=user,
            query=query,
            tag_id=int(tag_id) if tag_id else None,
            selected_members=selected_members,
            favourites_only=favourites_only
        )

        return recipes

    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)

        # Get upcoming meal plans
        today = date.today()
        context['meal_plans'] = MealPlan.objects.for_user(
            self.request.user
        ).with_related().filter(
            date__gte=today
        ).order_by('date', 'meal_type')

        # Add filter options
        context['tags'] = RecipeService.get_all_tags()
        context['family_members'] = RecipeService.get_family_members(self.request.user)

        # Preserve filter state
        context['query'] = self.request.GET.get('q')
        tag_id = self.request.GET.get('tag')
        context['selected_tag'] = int(tag_id) if tag_id else None
        context['selected_members'] = self.request.GET.getlist('member')
        context['favourites_only'] = self.request.GET.get('favourites') == '1'

        # Fix pagination object names
        context['page_obj'] = context['page_obj']
        context['recipes'] = context['page_obj'].object_list

        return context


class RecipeDetailView(LoginRequiredMixin, UserRecipeAccessMixin, DetailView):
    """
    Detail view for a single recipe.
    """
    model = Recipe
    template_name = 'recipes/recipe_detail.html'
    context_object_name = 'recipe'

    def get_queryset(self):
        """Optimize query with related objects."""
        return Recipe.objects.with_related()


class RecipeCreateView(LoginRequiredMixin, CreateView):
    """
    Create view for recipes.
    """
    model = Recipe
    form_class = RecipeForm
    template_name = 'recipes/recipe_form.html'
    success_url = reverse_lazy('recipe_list')

    def form_valid(self, form):
        """Set the user before saving."""
        form.instance.user = self.request.user
        return super().form_valid(form)


class RecipeUpdateView(LoginRequiredMixin, UserRecipeAccessMixin, UpdateView):
    """
    Update view for recipes.
    """
    model = Recipe
    form_class = RecipeForm
    template_name = 'recipes/recipe_form.html'

    def get_success_url(self):
        """Redirect to recipe detail after update."""
        return reverse('recipe_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        """Add update flag to context."""
        context = super().get_context_data(**kwargs)
        context['update'] = True
        return context


class RecipeDeleteView(LoginRequiredMixin, UserRecipeAccessMixin, DeleteView):
    """
    Delete view for recipes.
    """
    model = Recipe
    template_name = 'recipes/recipe_confirm_delete.html'
    success_url = reverse_lazy('recipe_list')
    context_object_name = 'recipe'


class MealPlanListView(LoginRequiredMixin, ListView):
    """
    List view for meal plans.
    """
    model = MealPlan
    template_name = 'recipes/meal_plan_list.html'
    context_object_name = 'plans'

    def get_queryset(self):
        """Get user's meal plans with optimized queries."""
        return MealPlan.objects.for_user(
            self.request.user
        ).with_related().order_by('date', 'meal_type')


class MealPlanCreateView(LoginRequiredMixin, CreateView):
    """
    Create view for meal plans.
    """
    model = MealPlan
    form_class = MealPlanForm
    template_name = 'recipes/meal_plan_form.html'

    def get_form_kwargs(self):
        """Pass user to form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_initial(self):
        """Pre-populate form with query parameters."""
        initial = super().get_initial()
        if 'date' in self.request.GET:
            initial['date'] = self.request.GET['date']
        if 'meal_type' in self.request.GET:
            initial['meal_type'] = self.request.GET['meal_type']
        return initial

    def form_valid(self, form):
        """Use service layer to create or update meal plan."""
        from datetime import datetime

        plan_date = form.cleaned_data['date']
        recipe = form.cleaned_data['recipe']
        meal_type = form.cleaned_data['meal_type']

        # Use service to create or update
        MealPlanService.create_or_update_meal_plan(
            user=self.request.user,
            recipe=recipe,
            plan_date=plan_date,
            meal_type=meal_type
        )

        # Calculate week offset for redirect
        selected_date = plan_date if plan_date else date.today()
        week_offset = (selected_date - date.today()).days // 7

        return redirect(f"{reverse('meal_plan_week')}?week={week_offset}")


class FamilyPreferenceCreateView(LoginRequiredMixin, CreateView):
    """
    Create view for family preferences.
    """
    model = FamilyPreference
    form_class = FamilyPreferenceForm
    template_name = 'recipes/add_preference.html'

    def dispatch(self, request, *args, **kwargs):
        """Store recipe for use in form handling."""
        self.recipe = get_object_or_404(
            Recipe,
            pk=kwargs.get('recipe_id'),
            user=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add recipe to context."""
        context = super().get_context_data(**kwargs)
        context['recipe'] = self.recipe
        return context

    def form_valid(self, form):
        """Use service layer to create or update preference."""
        RecipeService.add_or_update_preference(
            user=self.request.user,
            recipe=self.recipe,
            family_member=form.cleaned_data['family_member'],
            preference=form.cleaned_data['preference']
        )
        return redirect('recipe_detail', pk=self.recipe.pk)
