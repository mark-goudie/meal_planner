from django.test import TestCase
from django.contrib.auth.models import User
from recipes.forms import RecipeForm, MealPlanForm, FamilyPreferenceForm, CustomUserCreationForm
from recipes.models import Recipe, Tag, MealPlan, FamilyPreference


class RecipeFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.tag1, _ = Tag.objects.get_or_create(name='Breakfast')
        self.tag2, _ = Tag.objects.get_or_create(name='Quick')

    def test_recipe_form_valid_data(self):
        """Test RecipeForm with valid data"""
        form_data = {
            'title': 'Test Recipe',
            'author': 'Test Author',
            'description': 'A test recipe description',
            'ingredients': 'Test ingredients\nMore ingredients',
            'steps': 'Step 1\nStep 2',
            'notes': 'Test notes',
            'is_ai_generated': False,
            'tags': [self.tag1.id, self.tag2.id]
        }
        form = RecipeForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_recipe_form_minimal_required_data(self):
        """Test RecipeForm with minimal required data"""
        form_data = {
            'title': 'Minimal Recipe',
            'ingredients': 'Basic ingredients',
            'steps': 'Basic steps'
        }
        form = RecipeForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_recipe_form_missing_required_fields(self):
        """Test RecipeForm with missing required fields"""
        form_data = {
            'title': 'Recipe Without Required Fields',
            'author': 'Test Author'
        }
        form = RecipeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('ingredients', form.errors)
        self.assertIn('steps', form.errors)

    def test_recipe_form_empty_title(self):
        """Test RecipeForm with empty title"""
        form_data = {
            'title': '',
            'ingredients': 'Test ingredients',
            'steps': 'Test steps'
        }
        form = RecipeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)

    def test_recipe_form_save(self):
        """Test saving a valid RecipeForm"""
        form_data = {
            'title': 'Saveable Recipe',
            'ingredients': 'Saveable ingredients',
            'steps': 'Saveable steps',
            'tags': [self.tag1.id]
        }
        form = RecipeForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        recipe = form.save(commit=False)
        recipe.user = self.user
        recipe.save()
        form.save_m2m()
        
        self.assertEqual(recipe.title, 'Saveable Recipe')
        self.assertEqual(recipe.user, self.user)
        self.assertEqual(recipe.tags.count(), 1)
        self.assertIn(self.tag1, recipe.tags.all())

    def test_recipe_form_widget_attributes(self):
        """Test that form widgets have correct attributes"""
        form = RecipeForm()
        
        # Check textarea widgets have correct rows and cols
        self.assertEqual(form.fields['description'].widget.attrs['rows'], 4)
        self.assertEqual(form.fields['ingredients'].widget.attrs['rows'], 4)
        self.assertEqual(form.fields['steps'].widget.attrs['rows'], 4)
        self.assertEqual(form.fields['notes'].widget.attrs['rows'], 2)

    def test_recipe_form_labels(self):
        """Test form field labels"""
        form = RecipeForm()
        self.assertEqual(form.fields['title'].label, 'Recipe Title')
        self.assertEqual(form.fields['author'].label, 'Author Name')
        self.assertEqual(form.fields['ingredients'].label, 'Ingredients')
        self.assertEqual(form.fields['steps'].label, 'Cooking Steps')

    def test_recipe_form_help_texts(self):
        """Test form field help texts"""
        form = RecipeForm()
        self.assertEqual(form.fields['title'].help_text, 'Enter the title of the recipe.')
        self.assertEqual(form.fields['ingredients'].help_text, 'List all ingredients required for the recipe.')


class MealPlanFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        self.recipe = Recipe.objects.create(
            user=self.user,
            title='Test Recipe',
            ingredients='Test ingredients',
            steps='Test steps'
        )
        self.other_recipe = Recipe.objects.create(
            user=self.other_user,
            title='Other Recipe',
            ingredients='Other ingredients',
            steps='Other steps'
        )

    def test_meal_plan_form_valid_data(self):
        """Test MealPlanForm with valid data"""
        form_data = {
            'date': '2023-12-25',
            'meal_type': 'breakfast',
            'recipe': self.recipe.id
        }
        form = MealPlanForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_meal_plan_form_missing_required_fields(self):
        """Test MealPlanForm with missing required fields"""
        form_data = {
            'date': '2023-12-25',
            'meal_type': 'breakfast'
        }
        form = MealPlanForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('recipe', form.errors)

    def test_meal_plan_form_invalid_meal_type(self):
        """Test MealPlanForm with invalid meal type"""
        form_data = {
            'date': '2023-12-25',
            'meal_type': 'invalid_meal',
            'recipe': self.recipe.id
        }
        form = MealPlanForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('meal_type', form.errors)

    def test_meal_plan_form_user_recipe_filtering(self):
        """Test that MealPlanForm only shows user's recipes"""
        form = MealPlanForm(user=self.user)
        recipe_queryset = form.fields['recipe'].queryset
        
        self.assertIn(self.recipe, recipe_queryset)
        self.assertNotIn(self.other_recipe, recipe_queryset)

    def test_meal_plan_form_save(self):
        """Test saving a valid MealPlanForm"""
        form_data = {
            'date': '2023-12-25',
            'meal_type': 'dinner',
            'recipe': self.recipe.id
        }
        form = MealPlanForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        meal_plan = form.save(commit=False)
        meal_plan.user = self.user
        meal_plan.save()
        
        self.assertEqual(meal_plan.recipe, self.recipe)
        self.assertEqual(meal_plan.meal_type, 'dinner')


class FamilyPreferenceFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.recipe = Recipe.objects.create(
            user=self.user,
            title='Test Recipe',
            ingredients='Test ingredients',
            steps='Test steps'
        )

    def test_family_preference_form_valid_data(self):
        """Test FamilyPreferenceForm with valid data"""
        form_data = {
            'family_member': 'Alice',
            'preference': 3
        }
        form = FamilyPreferenceForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_family_preference_form_missing_required_fields(self):
        """Test FamilyPreferenceForm with missing required fields"""
        form_data = {
            'family_member': 'Alice'
        }
        form = FamilyPreferenceForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('preference', form.errors)

    def test_family_preference_form_empty_family_member(self):
        """Test FamilyPreferenceForm with empty family member"""
        form_data = {
            'family_member': '',
            'preference': 2
        }
        form = FamilyPreferenceForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('family_member', form.errors)

    def test_family_preference_form_invalid_preference(self):
        """Test FamilyPreferenceForm with invalid preference value"""
        form_data = {
            'family_member': 'Bob',
            'preference': 5  # Invalid choice
        }
        form = FamilyPreferenceForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('preference', form.errors)

    def test_family_preference_form_widget_attributes(self):
        """Test form widget attributes"""
        form = FamilyPreferenceForm()
        family_member_widget = form.fields['family_member'].widget
        self.assertEqual(family_member_widget.attrs['placeholder'], 'e.g. Nina')

    def test_family_preference_form_labels(self):
        """Test form field labels"""
        form = FamilyPreferenceForm()
        self.assertEqual(form.fields['family_member'].label, 'Family Member')
        self.assertEqual(form.fields['preference'].label, 'Preference Level')

    def test_family_preference_form_save(self):
        """Test saving a valid FamilyPreferenceForm"""
        form_data = {
            'family_member': 'Charlie',
            'preference': 1
        }
        form = FamilyPreferenceForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        preference = form.save(commit=False)
        preference.user = self.user
        preference.recipe = self.recipe
        preference.save()
        
        self.assertEqual(preference.family_member, 'Charlie')
        self.assertEqual(preference.preference, 1)
        self.assertEqual(preference.user, self.user)
        self.assertEqual(preference.recipe, self.recipe)


class CustomUserCreationFormTest(TestCase):
    def test_custom_user_creation_form_valid_data(self):
        """Test CustomUserCreationForm with valid data"""
        form_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_custom_user_creation_form_missing_email(self):
        """Test CustomUserCreationForm without email"""
        form_data = {
            'username': 'newuser',
            'password1': 'complexpass123',
            'password2': 'complexpass123'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_custom_user_creation_form_invalid_email(self):
        """Test CustomUserCreationForm with invalid email"""
        form_data = {
            'username': 'newuser',
            'email': 'invalid-email',
            'password1': 'complexpass123',
            'password2': 'complexpass123'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_custom_user_creation_form_password_mismatch(self):
        """Test CustomUserCreationForm with password mismatch"""
        form_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'complexpass123',
            'password2': 'differentpass123'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_custom_user_creation_form_weak_password(self):
        """Test CustomUserCreationForm with weak password"""
        form_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': '123',
            'password2': '123'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_custom_user_creation_form_duplicate_username(self):
        """Test CustomUserCreationForm with duplicate username"""
        # Create existing user
        User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='existingpass123'
        )
        
        form_data = {
            'username': 'existinguser',
            'email': 'new@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_custom_user_creation_form_save(self):
        """Test saving a valid CustomUserCreationForm"""
        form_data = {
            'username': 'saveableuser',
            'email': 'saveable@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        user = form.save()
        self.assertEqual(user.username, 'saveableuser')
        self.assertEqual(user.email, 'saveable@example.com')
        self.assertTrue(user.check_password('complexpass123'))

    def test_custom_user_creation_form_email_widget_class(self):
        """Test that email field has correct widget class"""
        form = CustomUserCreationForm()
        email_widget = form.fields['email'].widget
        self.assertIn('form-control', email_widget.attrs['class'])


class FormIntegrationTest(TestCase):
    """Test forms working together in realistic scenarios"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.tag = Tag.objects.create(name='Test Tag')

    def test_recipe_to_meal_plan_workflow(self):
        """Test creating recipe and then adding it to meal plan"""
        # Create recipe
        recipe_form_data = {
            'title': 'Workflow Recipe',
            'ingredients': 'Workflow ingredients',
            'steps': 'Workflow steps',
            'tags': [self.tag.id]
        }
        recipe_form = RecipeForm(data=recipe_form_data)
        self.assertTrue(recipe_form.is_valid())
        
        recipe = recipe_form.save(commit=False)
        recipe.user = self.user
        recipe.save()
        recipe_form.save_m2m()
        
        # Create meal plan with the recipe
        meal_plan_form_data = {
            'date': '2023-12-25',
            'meal_type': 'breakfast',
            'recipe': recipe.id
        }
        meal_plan_form = MealPlanForm(data=meal_plan_form_data, user=self.user)
        self.assertTrue(meal_plan_form.is_valid())
        
        meal_plan = meal_plan_form.save(commit=False)
        meal_plan.user = self.user
        meal_plan.save()
        
        self.assertEqual(meal_plan.recipe, recipe)

    def test_recipe_to_family_preference_workflow(self):
        """Test creating recipe and then adding family preferences"""
        # Create recipe
        recipe = Recipe.objects.create(
            user=self.user,
            title='Preference Recipe',
            ingredients='Preference ingredients',
            steps='Preference steps'
        )
        
        # Add family preference
        preference_form_data = {
            'family_member': 'Test Family Member',
            'preference': 3
        }
        preference_form = FamilyPreferenceForm(data=preference_form_data)
        self.assertTrue(preference_form.is_valid())
        
        preference = preference_form.save(commit=False)
        preference.user = self.user
        preference.recipe = recipe
        preference.save()
        
        self.assertEqual(preference.recipe, recipe)
        self.assertEqual(preference.user, self.user)