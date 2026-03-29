"""
End-to-end tests using Playwright.

Tests the key user flows through a real browser to catch UI/interaction bugs
that unit tests miss.

Run with: python manage.py test recipes.tests.test_e2e -v2

Uses StaticLiveServerTestCase so HTMX and Alpine.js scripts load via
Django's static file serving.
"""

import os
from datetime import date
from decimal import Decimal

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

from django.contrib.auth.models import User  # noqa: E402
from django.contrib.staticfiles.testing import StaticLiveServerTestCase  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

from recipes.models import (  # noqa: E402
    CookingNote,
    Ingredient,
    MealPlan,
    Recipe,
    RecipeIngredient,
    ShoppingListItem,
    Tag,
)
from recipes.models.household import DayComment, Household, HouseholdMembership  # noqa: E402


class PlaywrightTestCase(StaticLiveServerTestCase):
    """Base class for Playwright E2E tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()

    def setUp(self):
        self.page = self.browser.new_page()
        # Create test user with household
        self.user = User.objects.create_user("testuser", password="testpass123")
        self.household = Household.objects.create(name="Test Family", created_by=self.user)
        HouseholdMembership.objects.create(user=self.user, household=self.household)

    def tearDown(self):
        self.page.close()

    def login(self):
        """Log in as the test user and wait for the week/home page to load."""
        self.page.goto(f"{self.live_server_url}/accounts/login/")
        self.page.fill('input[name="username"]', "testuser")
        self.page.fill('input[name="password"]', "testpass123")
        self.page.click('button[type="submit"]')
        # After login, Django redirects to LOGIN_REDIRECT_URL = "/" (week view)
        # Wait for the day-card selector which appears on the week page
        self.page.wait_for_selector(".day-card", timeout=5000)

    def url(self, path):
        return f"{self.live_server_url}{path}"


class AuthenticationE2ETest(PlaywrightTestCase):
    """Test login, registration, and household code flows."""

    def test_login_and_redirect_to_week(self):
        """User logs in and lands on the This Week page."""
        self.login()
        # After login, Django redirects to "/" which renders week_view
        # The week view shows day cards
        self.page.wait_for_selector(".day-card", timeout=5000)
        assert self.page.locator(".day-card").count() > 0

    def test_login_with_wrong_password(self):
        """Wrong password shows error, stays on login page."""
        self.page.goto(self.url("/accounts/login/"))
        self.page.fill('input[name="username"]', "testuser")
        self.page.fill('input[name="password"]', "wrongpassword")
        self.page.click('button[type="submit"]')
        # Login template renders non_field_errors in ul.form-error-list
        self.page.wait_for_selector(".form-error-list", timeout=5000)
        assert self.page.locator(".form-error-list").is_visible()
        assert "/login/" in self.page.url

    def test_register_creates_household(self):
        """New user registration creates a household automatically."""
        self.page.goto(self.url("/register/"))
        self.page.fill('input[name="username"]', "newuser")
        self.page.fill('input[name="email"]', "newuser@example.com")
        self.page.fill('input[name="password1"]', "Str0ngP@ss!")
        self.page.fill('input[name="password2"]', "Str0ngP@ss!")
        self.page.click('button[type="submit"]')
        # register_view does redirect("week") -> /week/; wait for week page content
        self.page.wait_for_selector(".day-card", timeout=5000)
        assert "/week/" in self.page.url
        new_user = User.objects.get(username="newuser")
        assert hasattr(new_user, "household_membership")

    def test_register_with_household_code(self):
        """Registration with household code joins existing household."""
        self.page.goto(self.url("/register/"))
        self.page.fill('input[name="username"]', "familymember")
        self.page.fill('input[name="email"]', "familymember@example.com")
        self.page.fill('input[name="password1"]', "Str0ngP@ss!")
        self.page.fill('input[name="password2"]', "Str0ngP@ss!")
        self.page.fill('input[name="household_code"]', self.household.code)
        self.page.click('button[type="submit"]')
        # register_view does redirect("week") -> /week/; wait for week page content
        self.page.wait_for_selector(".day-card", timeout=5000)
        assert "/week/" in self.page.url
        new_user = User.objects.get(username="familymember")
        assert new_user.household_membership.household == self.household

    def test_register_with_invalid_code(self):
        """Invalid household code shows error."""
        self.page.goto(self.url("/register/"))
        self.page.fill('input[name="username"]', "badcode")
        self.page.fill('input[name="email"]', "badcode@example.com")
        self.page.fill('input[name="password1"]', "Str0ngP@ss!")
        self.page.fill('input[name="password2"]', "Str0ngP@ss!")
        self.page.fill('input[name="household_code"]', "XXXXXX")
        self.page.click('button[type="submit"]')
        # register_view adds form error via form.add_error(None, "Invalid household code.")
        # This renders in ul.form-error-list > li
        self.page.wait_for_selector(".form-error-list", timeout=5000)
        assert self.page.locator(".form-error-list").is_visible()
        assert self.page.locator(".form-error-list li").text_content().strip() == "Invalid household code."
        assert not User.objects.filter(username="badcode").exists()


class WeekViewE2ETest(PlaywrightTestCase):
    """Test the This Week screen."""

    def setUp(self):
        super().setUp()
        self.recipe = Recipe.objects.create(user=self.user, title="Test Pasta", steps="Cook pasta", cook_time=20)
        tag = Tag.objects.create(name="Italian", tag_type="cuisine")
        self.recipe.tags.add(tag)

    def test_week_view_shows_seven_days(self):
        """Week view displays 7 day cards."""
        self.login()
        cards = self.page.locator(".day-card")
        assert cards.count() == 7

    def test_week_view_shows_empty_slots(self):
        """Empty day cards show 'Tap to add a meal'."""
        self.login()
        assert self.page.locator("text=Tap to add a meal...").count() > 0

    def test_week_view_shows_planned_meal(self):
        """Planned meals appear on their day card."""
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today(),
            meal_type="dinner",
            recipe=self.recipe,
        )
        self.login()
        assert self.page.locator("text=Test Pasta").is_visible()

    def test_assign_meal_via_picker(self):
        """Click empty slot, picker overlay opens, click a recipe, meal is assigned."""
        self.login()
        # Click an empty day slot to trigger HTMX picker overlay
        self.page.locator(".day-card--empty .day-card__empty").first.click()
        # Wait for the picker overlay to appear (loaded via HTMX)
        self.page.wait_for_selector(".picker-overlay", timeout=5000)
        # The picker should show our recipe
        recipe_card = self.page.locator(".picker .recipe-card", has_text="Test Pasta")
        recipe_card.wait_for(timeout=5000)
        # Click the recipe card to assign it (hx-post)
        recipe_card.click()
        # Wait for HTMX swap to complete
        self.page.wait_for_timeout(2000)
        # Verify the meal was saved in the database
        assert MealPlan.objects.filter(recipe=self.recipe).exists()

    def test_week_navigation(self):
        """Click next week arrow, verify title changes."""
        self.login()
        # Verify we start on "This Week"
        assert self.page.locator(".week-header__title", has_text="This Week").is_visible()
        # Click the next week navigation arrow (right arrow)
        self.page.locator('.week-header__nav[aria-label="Next week"]').click()
        # Wait for HTMX swap to complete
        self.page.wait_for_timeout(1000)
        # Title should now say "Next Week"
        assert self.page.locator(".week-header__title", has_text="Next Week").is_visible()

    def test_day_comment_add(self):
        """Click Note button, fill text, submit, verify comment saved."""
        self.login()
        # Click the Note button on the first day card to expand comment form (Alpine.js)
        self.page.locator(".day-card__note-btn").first.click()
        # Wait for the comment form to become visible
        self.page.wait_for_selector('.day-card__add-comment input[name="text"]', timeout=3000)
        # Fill in the comment text
        self.page.fill('.day-card__add-comment input[name="text"]', "Work dinner tonight")
        # Submit the comment form (HTMX post)
        self.page.locator(".day-card__add-comment button[type='submit']").first.click()
        # Wait for HTMX swap to complete
        self.page.wait_for_timeout(1000)
        # Verify the comment appears in the DOM
        assert self.page.locator("text=Work dinner tonight").is_visible()
        # Verify it was saved to the database
        assert DayComment.objects.filter(text="Work dinner tonight").exists()


class RecipeE2ETest(PlaywrightTestCase):
    """Test recipe CRUD flows."""

    def setUp(self):
        super().setUp()
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Chicken Curry",
            steps="Cook it",
            cook_time=30,
            difficulty="easy",
        )
        tag = Tag.objects.create(name="Asian", tag_type="cuisine")
        self.recipe.tags.add(tag)

    def test_recipe_list_shows_recipes(self):
        """Recipe list displays user's recipes."""
        self.login()
        self.page.goto(self.url("/recipes/"))
        assert self.page.locator("text=Chicken Curry").is_visible()

    def test_recipe_list_search(self):
        """Type in search, wait for HTMX response, verify filtered results."""
        # Create a second recipe so we can verify filtering
        Recipe.objects.create(user=self.user, title="Beef Stew", steps="Stew it", cook_time=60)
        self.login()
        self.page.goto(self.url("/recipes/"))
        # Both recipes should be visible initially
        assert self.page.locator("text=Chicken Curry").is_visible()
        assert self.page.locator("text=Beef Stew").is_visible()
        # Type in the search input to filter
        self.page.fill('input[name="q"]', "Chicken")
        # Wait for HTMX debounced search to complete
        self.page.wait_for_timeout(1000)
        # Chicken Curry should still be visible, Beef Stew should be filtered out
        assert self.page.locator("#recipe-results").locator("text=Chicken Curry").is_visible()
        assert self.page.locator("#recipe-results").locator("text=Beef Stew").count() == 0

    def test_create_recipe_manually(self):
        """Creating a recipe via the form saves it."""
        self.login()
        self.page.goto(self.url("/recipes/new/"))
        self.page.fill('input[name="title"]', "Spaghetti Bolognese")
        self.page.fill('textarea[name="steps"]', "Brown mince\nAdd sauce\nCook pasta")
        self.page.fill('input[name="cook_time"]', "25")
        self.page.click('button[type="submit"]')
        # After create, redirects to /recipes/<pk>/
        self.page.wait_for_selector("h1", timeout=5000)
        assert Recipe.objects.filter(title="Spaghetti Bolognese").exists()

    def test_recipe_detail_shows_info(self):
        """Recipe detail page shows recipe information."""
        self.login()
        self.page.goto(self.url(f"/recipes/{self.recipe.pk}/"))
        assert self.page.locator("h1").text_content().strip() == "Chicken Curry"
        # Cook time chip renders as "30m" inside a .chip--primary span
        assert self.page.locator(".chip--primary", has_text="30m").first.is_visible()

    def test_toggle_favourite(self):
        """Click heart button, verify favourite is toggled."""
        self.login()
        self.page.goto(self.url(f"/recipes/{self.recipe.pk}/"))
        # Initially not favourited - heart should be outlined (bi-heart)
        fav_btn = self.page.locator("#fav-btn button")
        assert fav_btn.is_visible()
        # Click the favourite button (HTMX post)
        fav_btn.click()
        # Wait for HTMX swap
        self.page.wait_for_timeout(1000)
        # After toggling, the heart should be filled (bi-heart-fill)
        assert self.page.locator("#fav-btn .bi-heart-fill").is_visible()
        # Verify in database
        self.recipe.refresh_from_db()
        assert self.user in self.recipe.favourited_by.all()

    def test_delete_recipe(self):
        """Deleting a recipe removes it."""
        self.login()
        self.page.goto(self.url(f"/recipes/{self.recipe.pk}/delete/"))
        self.page.click('button[type="submit"]')
        # After delete, redirects to /recipes/
        self.page.wait_for_url(f"{self.live_server_url}/recipes/", timeout=5000)
        assert not Recipe.objects.filter(pk=self.recipe.pk).exists()


class ShoppingListE2ETest(PlaywrightTestCase):
    """Test shopping list."""

    def setUp(self):
        super().setUp()
        self.recipe = Recipe.objects.create(user=self.user, title="Soup", steps="Make soup", cook_time=30)
        self.ingredient = Ingredient.objects.create(name="onion", category="produce")
        RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient,
            quantity=Decimal("2"),
            unit="piece",
            order=0,
        )
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today(),
            meal_type="dinner",
            recipe=self.recipe,
        )

    def test_shop_view_shows_generated_items(self):
        """Shopping list auto-generates items from meal plan."""
        self.login()
        self.page.goto(self.url("/shop/"))
        self.page.wait_for_selector(".shop-item", timeout=5000)
        assert self.page.locator("text=onion").is_visible()

    def test_shop_toggle_item(self):
        """Click item toggle, verify checked state changes."""
        self.login()
        self.page.goto(self.url("/shop/"))
        self.page.wait_for_selector(".shop-item", timeout=5000)
        # Get the first shop item
        item = self.page.locator(".shop-item").first
        # It should not be checked initially
        assert "shop-item--checked" not in (item.get_attribute("class") or "")
        # Click the toggle area (HTMX post)
        item.locator(".shop-item__toggle").click()
        # Wait for HTMX swap
        self.page.wait_for_timeout(1000)
        # After toggling, item should have the checked class
        item = self.page.locator(".shop-item").first
        assert "shop-item--checked" in (item.get_attribute("class") or "")

    def test_shop_add_manual_item(self):
        """Fill input, submit, verify item created."""
        self.login()
        self.page.goto(self.url("/shop/"))
        self.page.wait_for_selector(".shop-item", timeout=5000)
        # Fill the manual item form
        self.page.fill('#manual-items-list + form input[name="name"]', "milk")
        # Submit the form (HTMX post)
        self.page.locator('#manual-items-list + form button[type="submit"]').click()
        # Wait for HTMX swap
        self.page.wait_for_timeout(1000)
        # Verify the new item appears
        assert self.page.locator("#manual-items-list").locator("text=milk").is_visible()
        # Verify in database
        assert ShoppingListItem.objects.filter(name="milk").exists()

    def test_shop_regenerate(self):
        """Regenerating the list updates items via standard form POST."""
        self.login()
        self.page.goto(self.url("/shop/"))
        self.page.wait_for_selector(".shop-item", timeout=5000)
        # Click regenerate -- this is a standard form POST (method="post" action="/shop/generate/")
        self.page.click('button[type="submit"]:has-text("Update Shopping List")')
        # shop_generate redirects back to /shop/
        self.page.wait_for_url(f"{self.live_server_url}/shop/", timeout=5000)
        assert self.page.locator("text=onion").is_visible()


class CookingModeE2ETest(PlaywrightTestCase):
    """Test cooking mode."""

    def setUp(self):
        super().setUp()
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Toast",
            steps="Get bread\nPut in toaster\nButter it",
            cook_time=5,
        )

    def test_cooking_mode_shows_steps(self):
        """Cooking mode displays the first step."""
        self.login()
        self.page.goto(self.url(f"/cook/{self.recipe.pk}/"))
        assert self.page.locator("text=Get bread").is_visible()

    def test_cooking_mode_next_step(self):
        """Click Next, verify step advances."""
        self.login()
        self.page.goto(self.url(f"/cook/{self.recipe.pk}/"))
        # Verify we are on step 1
        assert self.page.locator("text=Get bread").is_visible()
        # Click Next button (HTMX get)
        self.page.locator("button", has_text="Next").click()
        # Wait for HTMX swap
        self.page.wait_for_timeout(1000)
        # Step 2 text should now be visible
        assert self.page.locator("text=Put in toaster").is_visible()

    def test_cooking_mode_done_saves_note(self):
        """Navigate to last step, click Done, fill rating, submit."""
        self.login()
        self.page.goto(self.url(f"/cook/{self.recipe.pk}/"))
        # Navigate through all steps to the end
        # Step 1 -> Step 2
        self.page.locator("button", has_text="Next").click()
        self.page.wait_for_timeout(1000)
        # Step 2 -> Step 3
        self.page.locator("button", has_text="Next").click()
        self.page.wait_for_timeout(1000)
        # Step 3 is last step, click Done
        self.page.locator("button", has_text="Done").click()
        self.page.wait_for_timeout(1000)
        # Should now see the "All done!" completion screen
        assert self.page.locator("text=All done!").is_visible()
        # Fill in the note
        self.page.fill('textarea[name="note"]', "Perfectly toasted")
        # Submit the form (standard POST, not HTMX)
        self.page.click('button[type="submit"]:has-text("Save")')
        # After POST, should redirect to recipe detail page
        self.page.wait_for_url(f"**/recipes/{self.recipe.pk}/", timeout=5000)
        # Verify the cooking note was saved
        assert CookingNote.objects.filter(recipe=self.recipe, note="Perfectly toasted").exists()


class NavigationE2ETest(PlaywrightTestCase):
    """Test bottom navigation and page transitions."""

    def test_bottom_nav_visible_when_logged_in(self):
        """Bottom nav shows 4 tabs for authenticated users."""
        self.login()
        nav = self.page.locator(".bottom-nav")
        assert nav.is_visible()
        assert nav.locator(".nav-tab").count() == 4

    def test_bottom_nav_hidden_on_login_page(self):
        """Bottom nav is hidden for unauthenticated users."""
        self.page.goto(self.url("/accounts/login/"))
        assert not self.page.locator(".bottom-nav").is_visible()

    def test_navigate_between_tabs(self):
        """All tab navigation works."""
        self.login()
        # Recipes tab
        self.page.click('.nav-tab:has-text("Recipes")')
        self.page.wait_for_url(f"{self.live_server_url}/recipes/", timeout=5000)
        assert self.page.locator("text=Recipes").first.is_visible()
        # Shop tab
        self.page.click('.nav-tab:has-text("Shop")')
        self.page.wait_for_url(f"{self.live_server_url}/shop/", timeout=5000)
        assert self.page.locator("text=Shopping List").is_visible()
        # Settings/More tab
        self.page.click('.nav-tab:has-text("More")')
        self.page.wait_for_url(f"{self.live_server_url}/settings/", timeout=5000)
        assert self.page.locator("h1", has_text="Settings").is_visible()
        # Back to This Week
        self.page.click('.nav-tab:has-text("This Week")')
        self.page.wait_for_url(f"{self.live_server_url}/week/", timeout=5000)


class HouseholdSharingE2ETest(PlaywrightTestCase):
    """Test household sharing between two users."""

    def setUp(self):
        super().setUp()
        # Create second user in same household
        self.user2 = User.objects.create_user("partner", password="testpass123")
        HouseholdMembership.objects.create(user=self.user2, household=self.household)
        self.shared_recipe = Recipe.objects.create(
            user=self.user,
            title="Shared Dinner",
            steps="Cook it",
            shared=True,
        )

    def _login_as(self, username, password):
        """Log in as a given user and wait for the week page."""
        self.page.goto(self.url("/accounts/login/"))
        self.page.fill('input[name="username"]', username)
        self.page.fill('input[name="password"]', password)
        self.page.click('button[type="submit"]')
        self.page.wait_for_selector(".day-card", timeout=5000)

    def test_both_users_see_shared_meal_plan(self):
        """Both household members see the same meal plan."""
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date.today(),
            meal_type="dinner",
            recipe=self.shared_recipe,
        )
        # User 1
        self._login_as("testuser", "testpass123")
        assert self.page.locator("text=Shared Dinner").is_visible()
        self.page.close()
        # User 2
        self.page = self.browser.new_page()
        self._login_as("partner", "testpass123")
        assert self.page.locator("text=Shared Dinner").is_visible()

    def test_shared_recipe_visible_to_household_member(self):
        """Shared recipes appear in household member's recipe list."""
        self._login_as("partner", "testpass123")
        self.page.goto(self.url("/recipes/"))
        assert self.page.locator("text=Shared Dinner").is_visible()

    def test_unshared_recipe_hidden_from_household_member(self):
        """Unshared recipes don't appear in household member's recipe list."""
        Recipe.objects.create(
            user=self.user,
            title="Private Recipe",
            steps="Secret",
            shared=False,
        )
        self._login_as("partner", "testpass123")
        self.page.goto(self.url("/recipes/"))
        assert not self.page.locator("text=Private Recipe").is_visible()

    def test_household_code_shown_in_settings(self):
        """Settings page shows the household code."""
        self.login()
        self.page.goto(self.url("/settings/"))
        assert self.page.locator(f"text={self.household.code}").is_visible()
