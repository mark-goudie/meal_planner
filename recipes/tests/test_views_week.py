from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from recipes.models import MealPlan, Recipe
from recipes.models.household import Household, HouseholdMembership


class WeekViewTest(TestCase):
    """Tests for the This Week view and related HTMX endpoints."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.household = Household.objects.create(name="Test")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Spaghetti Carbonara",
            steps="Cook pasta. Make sauce.",
            cook_time=30,
        )
        self.client.login(username="testuser", password="testpass123")

    # ------------------------------------------------------------------
    # Full page tests
    # ------------------------------------------------------------------

    def test_week_view_returns_200(self):
        """The week view should return 200 for authenticated users."""
        response = self.client.get(reverse("week"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "week/week.html")

    def test_home_url_returns_week_view(self):
        """The root URL should serve the week view."""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "week/week.html")

    def test_week_view_shows_planned_meal(self):
        """A meal planned for this week should appear in the view."""
        today = date.today()
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=today,
            meal_type="dinner",
            recipe=self.recipe,
        )
        response = self.client.get(reverse("week"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Spaghetti Carbonara")

    def test_week_view_shows_empty_slots(self):
        """Days without meals should show the 'Tap to add' prompt."""
        response = self.client.get(reverse("week"))
        self.assertContains(response, "Tap to add a meal...")

    def test_week_view_requires_login(self):
        """Unauthenticated users should be redirected to login."""
        self.client.logout()
        response = self.client.get(reverse("week"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_week_navigation_offset(self):
        """Passing offset should shift the week displayed."""
        response = self.client.get(reverse("week") + "?offset=1")
        self.assertEqual(response.status_code, 200)
        # Next week should have next Monday's date
        today = date.today()
        next_monday = today - timedelta(days=today.weekday()) + timedelta(weeks=1)
        self.assertContains(response, next_monday.strftime("%b"))

    def test_week_navigation_negative_offset(self):
        """Negative offset should show previous week."""
        response = self.client.get(reverse("week") + "?offset=-1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Last Week")

    def test_week_context_has_seven_days(self):
        """Context should contain exactly 7 days."""
        response = self.client.get(reverse("week"))
        self.assertEqual(len(response.context["days"]), 7)

    def test_week_context_starts_on_monday(self):
        """The first day in context should be a Monday."""
        response = self.client.get(reverse("week"))
        first_day = response.context["days"][0]["date"]
        self.assertEqual(first_day.weekday(), 0)  # 0 = Monday

    # ------------------------------------------------------------------
    # HTMX slot & assign tests
    # ------------------------------------------------------------------

    def test_slot_view_returns_200(self):
        """The slot endpoint should return the meal card partial."""
        today = date.today()
        date_str = today.strftime("%Y-%m-%d")
        response = self.client.get(reverse("week_slot", args=[date_str, "dinner"]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "week/partials/meal_card.html")

    def test_assign_get_shows_picker(self):
        """GET to assign endpoint should show recipe picker."""
        today = date.today()
        date_str = today.strftime("%Y-%m-%d")
        response = self.client.get(reverse("week_assign", args=[date_str, "dinner"]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "week/partials/recipe_picker.html")
        self.assertContains(response, "Spaghetti Carbonara")

    def test_assign_get_search_filter(self):
        """GET with ?q= should filter recipes."""
        Recipe.objects.create(
            user=self.user,
            title="Thai Green Curry",
            steps="Make curry.",
        )
        today = date.today()
        date_str = today.strftime("%Y-%m-%d")

        response = self.client.get(reverse("week_assign", args=[date_str, "dinner"]) + "?q=Thai")
        self.assertContains(response, "Thai Green Curry")
        self.assertNotContains(response, "Spaghetti Carbonara")

    def test_slot_assign_htmx(self):
        """POST to assign should create a MealPlan and return the card."""
        today = date.today()
        date_str = today.strftime("%Y-%m-%d")

        response = self.client.post(
            reverse("week_assign", args=[date_str, "dinner"]),
            data={"recipe_id": self.recipe.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Spaghetti Carbonara")

        # Verify MealPlan was created
        self.assertTrue(
            MealPlan.objects.filter(
                household=self.household,
                date=today,
                meal_type="dinner",
                recipe=self.recipe,
            ).exists()
        )

    def test_slot_assign_updates_existing(self):
        """POST to assign should update an existing MealPlan."""
        today = date.today()
        date_str = today.strftime("%Y-%m-%d")
        new_recipe = Recipe.objects.create(
            user=self.user,
            title="Fish Tacos",
            steps="Make tacos.",
        )

        # Create initial meal plan
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=today,
            meal_type="dinner",
            recipe=self.recipe,
        )

        # Assign a different recipe
        response = self.client.post(
            reverse("week_assign", args=[date_str, "dinner"]),
            data={"recipe_id": new_recipe.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fish Tacos")

        # Should still be just one plan for this slot
        self.assertEqual(
            MealPlan.objects.filter(
                household=self.household,
                date=today,
                meal_type="dinner",
            ).count(),
            1,
        )

    # ------------------------------------------------------------------
    # Suggest view
    # ------------------------------------------------------------------

    def test_suggest_returns_200(self):
        """Suggest endpoint should return 200."""
        response = self.client.get(reverse("week_suggest"))
        self.assertEqual(response.status_code, 200)

    def test_suggest_with_empty_slots_shows_suggestions(self):
        """Suggest should propose recipes for empty dinner slots."""
        # Current week has meals seeded in setUp — clear them to create empty slots
        MealPlan.objects.filter(household=self.household).delete()
        response = self.client.get(reverse("week_suggest"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Accept")

    def test_accept_suggestion_creates_meal_plan(self):
        """Accepting a suggestion should create a MealPlan entry."""
        from datetime import date, timedelta

        tomorrow = date.today() + timedelta(days=1)
        date_str = tomorrow.strftime("%Y-%m-%d")
        MealPlan.objects.filter(household=self.household, date=tomorrow).delete()
        response = self.client.post(
            reverse("week_accept_suggestion", args=[date_str]),
            {"recipe_id": self.recipe.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(MealPlan.objects.filter(household=self.household, date=tomorrow, meal_type="dinner").exists())

    # ------------------------------------------------------------------
    # Placeholder views
    # ------------------------------------------------------------------

    def test_shop_placeholder_returns_200(self):
        """Shop placeholder should return 200."""
        response = self.client.get(reverse("shop"))
        self.assertEqual(response.status_code, 200)

    def test_settings_placeholder_returns_200(self):
        """Settings placeholder should return 200."""
        response = self.client.get(reverse("settings"))
        self.assertEqual(response.status_code, 200)

    # ------------------------------------------------------------------
    # Register view
    # ------------------------------------------------------------------

    def test_register_view_get(self):
        """Register page should render."""
        self.client.logout()
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)

    def test_register_view_post_valid(self):
        """Valid registration should create user and redirect to week."""
        self.client.logout()
        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("week", response.url)
        self.assertTrue(User.objects.filter(username="newuser").exists())


class WeekViewTodayHighlightTest(TestCase):
    """Test that today's card is highlighted correctly."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser2", password="testpass123")
        self.household = Household.objects.create(name="Test")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.client.login(username="testuser2", password="testpass123")

    def test_today_badge_shown(self):
        """Today's card should have the TODAY badge."""
        response = self.client.get(reverse("week"))
        self.assertContains(response, "badge--today")
        self.assertContains(response, "TODAY")

    def test_today_card_has_today_class(self):
        """Today's card should have the day-card--today CSS class."""
        response = self.client.get(reverse("week"))
        self.assertContains(response, "day-card--today")
