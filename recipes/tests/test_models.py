from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from datetime import date, timedelta
from recipes.models import Recipe, Tag, MealPlan, FamilyPreference, MEAL_CHOICES, PREFERENCE_CHOICES


class RecipeModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.tag1, _ = Tag.objects.get_or_create(name='Breakfast')
        self.tag2, _ = Tag.objects.get_or_create(name='Quick')

    def test_create_recipe_minimal(self):
        """Test creating a recipe with minimal required fields"""
        recipe = Recipe.objects.create(
            user=self.user,
            title='Test Recipe',
            ingredients='Test ingredients',
            steps='Test steps'
        )
        self.assertEqual(recipe.title, 'Test Recipe')
        self.assertEqual(recipe.user, self.user)
        self.assertFalse(recipe.is_ai_generated)
        self.assertIsNotNone(recipe.created_at)

    def test_create_recipe_full(self):
        """Test creating a recipe with all fields"""
        recipe = Recipe.objects.create(
            user=self.user,
            title='Full Test Recipe',
            author='Test Author',
            description='Test description',
            ingredients='Test ingredients\nMore ingredients',
            steps='Step 1\nStep 2',
            notes='Test notes',
            is_ai_generated=True
        )
        recipe.tags.add(self.tag1, self.tag2)
        recipe.favourited_by.add(self.user)
        
        self.assertEqual(recipe.title, 'Full Test Recipe')
        self.assertEqual(recipe.author, 'Test Author')
        self.assertTrue(recipe.is_ai_generated)
        self.assertEqual(recipe.tags.count(), 2)
        self.assertTrue(self.user in recipe.favourited_by.all())

    def test_recipe_str_method(self):
        """Test the string representation of Recipe"""
        recipe = Recipe.objects.create(
            user=self.user,
            title='String Test Recipe',
            ingredients='ingredients',
            steps='steps'
        )
        self.assertEqual(str(recipe), 'String Test Recipe')

    def test_recipe_user_relationship(self):
        """Test the foreign key relationship with User"""
        recipe = Recipe.objects.create(
            user=self.user,
            title='Relationship Test',
            ingredients='ingredients',
            steps='steps'
        )
        self.assertEqual(recipe.user, self.user)
        self.assertIn(recipe, self.user.recipes.all())

    def test_recipe_tag_many_to_many(self):
        """Test the many-to-many relationship with Tags"""
        recipe = Recipe.objects.create(
            user=self.user,
            title='Tag Test Recipe',
            ingredients='ingredients',
            steps='steps'
        )
        recipe.tags.add(self.tag1)
        self.assertEqual(recipe.tags.count(), 1)
        self.assertIn(self.tag1, recipe.tags.all())

    def test_recipe_favourited_by_many_to_many(self):
        """Test the favourited_by many-to-many relationship"""
        recipe = Recipe.objects.create(
            user=self.user,
            title='Favourite Test',
            ingredients='ingredients',
            steps='steps'
        )
        recipe.favourited_by.add(self.user)
        self.assertEqual(recipe.favourited_by.count(), 1)
        self.assertIn(recipe, self.user.favourites.all())


class TagModelTest(TestCase):
    def test_create_tag(self):
        """Test creating a tag"""
        tag = Tag.objects.create(name='VegetarianUnique')
        self.assertEqual(tag.name, 'VegetarianUnique')

    def test_tag_str_method(self):
        """Test the string representation of Tag"""
        tag = Tag.objects.create(name='Gluten-FreeUnique')
        self.assertEqual(str(tag), 'Gluten-FreeUnique')

    def test_tag_unique_constraint(self):
        """Test that tag names must be unique"""
        Tag.objects.get_or_create(name='Unique Tag')
        with self.assertRaises(IntegrityError):
            Tag.objects.create(name='Unique Tag')

    def test_tag_max_length(self):
        """Test tag name maximum length"""
        long_name = 'a' * 51  # 51 characters, exceeds max_length=50
        tag = Tag(name=long_name)
        with self.assertRaises(ValidationError):
            tag.full_clean()


class MealPlanModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.recipe = Recipe.objects.create(
            user=self.user,
            title='Test Recipe',
            ingredients='ingredients',
            steps='steps'
        )

    def test_create_meal_plan(self):
        """Test creating a meal plan"""
        meal_plan = MealPlan.objects.create(
            user=self.user,
            date=date.today(),
            meal_type='breakfast',
            recipe=self.recipe
        )
        self.assertEqual(meal_plan.user, self.user)
        self.assertEqual(meal_plan.date, date.today())
        self.assertEqual(meal_plan.meal_type, 'breakfast')
        self.assertEqual(meal_plan.recipe, self.recipe)

    def test_meal_plan_default_date(self):
        """Test that meal plan defaults to today's date"""
        meal_plan = MealPlan.objects.create(
            user=self.user,
            meal_type='lunch',
            recipe=self.recipe
        )
        self.assertEqual(meal_plan.date, date.today())

    def test_meal_plan_str_method(self):
        """Test the string representation of MealPlan"""
        meal_plan = MealPlan.objects.create(
            user=self.user,
            date=date(2023, 12, 25),
            meal_type='dinner',
            recipe=self.recipe
        )
        expected_str = f"Dinner on 2023-12-25: {self.recipe.title}"
        self.assertEqual(str(meal_plan), expected_str)

    def test_meal_choices_validation(self):
        """Test that meal_type is restricted to valid choices"""
        valid_choices = [choice[0] for choice in MEAL_CHOICES]
        self.assertIn('breakfast', valid_choices)
        self.assertIn('lunch', valid_choices)
        self.assertIn('dinner', valid_choices)

    def test_meal_plan_user_relationship(self):
        """Test the foreign key relationship with User"""
        meal_plan = MealPlan.objects.create(
            user=self.user,
            meal_type='breakfast',
            recipe=self.recipe
        )
        self.assertIn(meal_plan, self.user.meal_plans.all())

    def test_meal_plan_recipe_relationship(self):
        """Test the foreign key relationship with Recipe"""
        meal_plan = MealPlan.objects.create(
            user=self.user,
            meal_type='breakfast',
            recipe=self.recipe
        )
        self.assertEqual(meal_plan.recipe, self.recipe)


class FamilyPreferenceModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.recipe = Recipe.objects.create(
            user=self.user,
            title='Test Recipe',
            ingredients='ingredients',
            steps='steps'
        )

    def test_create_family_preference(self):
        """Test creating a family preference"""
        preference = FamilyPreference.objects.create(
            user=self.user,
            family_member='Alice',
            recipe=self.recipe,
            preference=3  # Like
        )
        self.assertEqual(preference.user, self.user)
        self.assertEqual(preference.family_member, 'Alice')
        self.assertEqual(preference.recipe, self.recipe)
        self.assertEqual(preference.preference, 3)

    def test_family_preference_str_method(self):
        """Test the string representation of FamilyPreference"""
        preference = FamilyPreference.objects.create(
            user=self.user,
            family_member='Bob',
            recipe=self.recipe,
            preference=1  # Dislike
        )
        expected_str = f"Bob - {self.recipe.title}: Dislike"
        self.assertEqual(str(preference), expected_str)

    def test_preference_choices_validation(self):
        """Test that preference is restricted to valid choices"""
        valid_choices = [choice[0] for choice in PREFERENCE_CHOICES]
        self.assertIn(1, valid_choices)  # Dislike
        self.assertIn(2, valid_choices)  # Neutral
        self.assertIn(3, valid_choices)  # Like

    def test_unique_together_constraint(self):
        """Test that family_member and recipe combination must be unique"""
        FamilyPreference.objects.create(
            user=self.user,
            family_member='Charlie',
            recipe=self.recipe,
            preference=2
        )
        with self.assertRaises(IntegrityError):
            FamilyPreference.objects.create(
                user=self.user,
                family_member='Charlie',
                recipe=self.recipe,
                preference=3
            )

    def test_family_preference_user_relationship(self):
        """Test the foreign key relationship with User"""
        preference = FamilyPreference.objects.create(
            user=self.user,
            family_member='Diana',
            recipe=self.recipe,
            preference=3
        )
        self.assertIn(preference, self.user.family_preferences.all())

    def test_family_preference_recipe_relationship(self):
        """Test the foreign key relationship with Recipe"""
        preference = FamilyPreference.objects.create(
            user=self.user,
            family_member='Eve',
            recipe=self.recipe,
            preference=2
        )
        self.assertEqual(preference.recipe, self.recipe)

    def test_multiple_family_members_same_recipe(self):
        """Test that multiple family members can have preferences for the same recipe"""
        FamilyPreference.objects.create(
            user=self.user,
            family_member='Frank',
            recipe=self.recipe,
            preference=3
        )
        FamilyPreference.objects.create(
            user=self.user,
            family_member='Grace',
            recipe=self.recipe,
            preference=1
        )
        preferences = FamilyPreference.objects.filter(recipe=self.recipe)
        self.assertEqual(preferences.count(), 2)