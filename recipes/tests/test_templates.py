from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from recipes.models import Household, HouseholdMembership, MealPlan, Recipe
from recipes.models.template import MealPlanTemplate, MealPlanTemplateEntry


class MealPlanTemplateTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", password="testpass123")
        self.household = Household.objects.create(name="Test")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.recipe1 = Recipe.objects.create(
            user=self.user, title="Monday Meal", steps="cook"
        )
        self.recipe2 = Recipe.objects.create(
            user=self.user, title="Tuesday Meal", steps="cook"
        )
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_save_template(self):
        # Create meals for this week
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=monday,
            meal_type="dinner",
            recipe=self.recipe1,
        )
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=monday + timedelta(days=1),
            meal_type="dinner",
            recipe=self.recipe2,
        )

        response = self.client.post(
            reverse("save_template"), {"name": "Test Template", "offset": "0"}
        )
        self.assertEqual(response.status_code, 302)
        template = MealPlanTemplate.objects.get(name="Test Template")
        self.assertEqual(template.entries.count(), 2)

    def test_apply_template_fills_empty_slots(self):
        # Create template
        template = MealPlanTemplate.objects.create(
            household=self.household,
            name="Test",
            created_by=self.user,
        )
        MealPlanTemplateEntry.objects.create(
            template=template, day_of_week=0, recipe=self.recipe1
        )
        MealPlanTemplateEntry.objects.create(
            template=template, day_of_week=1, recipe=self.recipe2
        )

        response = self.client.post(
            reverse("apply_template", args=[template.pk]), {"offset": "0"}
        )
        self.assertEqual(response.status_code, 302)
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        self.assertTrue(
            MealPlan.objects.filter(household=self.household, date=monday).exists()
        )

    def test_apply_template_does_not_overwrite(self):
        # Create existing meal on Monday
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        existing = Recipe.objects.create(user=self.user, title="Existing", steps="cook")
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=monday,
            meal_type="dinner",
            recipe=existing,
        )

        # Create template with Monday meal
        template = MealPlanTemplate.objects.create(
            household=self.household,
            name="Test",
            created_by=self.user,
        )
        MealPlanTemplateEntry.objects.create(
            template=template, day_of_week=0, recipe=self.recipe1
        )

        self.client.post(reverse("apply_template", args=[template.pk]), {"offset": "0"})
        # Monday should still have the existing meal, not the template's
        meal = MealPlan.objects.get(
            household=self.household, date=monday, meal_type="dinner"
        )
        self.assertEqual(meal.recipe.title, "Existing")

    def test_delete_template(self):
        template = MealPlanTemplate.objects.create(
            household=self.household,
            name="Delete Me",
            created_by=self.user,
        )
        response = self.client.post(reverse("delete_template", args=[template.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(MealPlanTemplate.objects.filter(pk=template.pk).exists())

    def test_save_template_requires_name(self):
        response = self.client.post(
            reverse("save_template"), {"name": "", "offset": "0"}
        )
        self.assertEqual(response.status_code, 302)  # redirects with error message
        self.assertEqual(MealPlanTemplate.objects.count(), 0)

    def test_list_templates(self):
        MealPlanTemplate.objects.create(
            household=self.household,
            name="Template 1",
            created_by=self.user,
        )
        response = self.client.get(reverse("list_templates"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Template 1")
