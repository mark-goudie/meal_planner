from datetime import date

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse

from recipes.models import (
    DayComment,
    Household,
    HouseholdMembership,
    MealPlan,
    Recipe,
    ShoppingListItem,
    generate_household_code,
    get_household,
)


class HouseholdModelTests(TestCase):
    def test_household_creation(self):
        user = User.objects.create_user("alice", password="pass")
        h = Household.objects.create(name="Test Kitchen", created_by=user)
        self.assertEqual(h.name, "Test Kitchen")
        self.assertEqual(h.created_by, user)
        self.assertIsNotNone(h.created_at)

    def test_auto_generated_code(self):
        user = User.objects.create_user("alice", password="pass")
        h = Household.objects.create(name="Test Kitchen", created_by=user)
        self.assertEqual(len(h.code), 6)
        self.assertTrue(h.code.isalnum())

    def test_code_uniqueness(self):
        user = User.objects.create_user("alice", password="pass")
        h1 = Household.objects.create(name="Kitchen 1", created_by=user)
        h2 = Household.objects.create(name="Kitchen 2", created_by=user)
        self.assertNotEqual(h1.code, h2.code)

    def test_ambiguous_char_exclusion(self):
        """Generated codes should not contain 0, O, 1, I, or L."""
        ambiguous = set("0O1IL")
        for _ in range(50):
            code = generate_household_code()
            self.assertEqual(len(code), 6)
            self.assertFalse(
                ambiguous & set(code),
                f"Code {code} contains ambiguous character(s)",
            )


class HouseholdMembershipTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user("alice", password="pass")
        self.user2 = User.objects.create_user("bob", password="pass")
        self.household = Household.objects.create(name="Test Kitchen", created_by=self.user1)

    def test_membership_creation(self):
        m = HouseholdMembership.objects.create(user=self.user1, household=self.household)
        self.assertEqual(m.user, self.user1)
        self.assertEqual(m.household, self.household)

    def test_one_to_one_constraint(self):
        HouseholdMembership.objects.create(user=self.user1, household=self.household)
        with self.assertRaises(IntegrityError):
            HouseholdMembership.objects.create(user=self.user1, household=self.household)

    def test_household_members_count(self):
        HouseholdMembership.objects.create(user=self.user1, household=self.household)
        HouseholdMembership.objects.create(user=self.user2, household=self.household)
        self.assertEqual(self.household.members.count(), 2)


class DayCommentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="pass")
        self.household = Household.objects.create(name="Test Kitchen", created_by=self.user)

    def test_day_comment_creation(self):
        comment = DayComment.objects.create(
            household=self.household,
            user=self.user,
            date=date(2026, 3, 28),
            text="Pizza night!",
        )
        self.assertEqual(comment.text, "Pizza night!")
        self.assertEqual(comment.date, date(2026, 3, 28))

    def test_unique_together_constraint(self):
        DayComment.objects.create(
            household=self.household,
            user=self.user,
            date=date(2026, 3, 28),
            text="First comment",
        )
        with self.assertRaises(IntegrityError):
            DayComment.objects.create(
                household=self.household,
                user=self.user,
                date=date(2026, 3, 28),
                text="Duplicate comment",
            )


class GetHouseholdHelperTests(TestCase):
    def test_get_household_returns_household(self):
        user = User.objects.create_user("alice", password="pass")
        household = Household.objects.create(name="Alice's Kitchen", created_by=user)
        HouseholdMembership.objects.create(user=user, household=household)
        self.assertEqual(get_household(user), household)

    def test_get_household_returns_none_for_no_membership(self):
        user = User.objects.create_user("alice", password="pass")
        self.assertIsNone(get_household(user))


class RecipeSharedFieldTests(TestCase):
    def test_shared_default_false(self):
        user = User.objects.create_user("alice", password="pass")
        recipe = Recipe.objects.create(
            user=user,
            title="Test Recipe",
            steps="Step 1",
        )
        self.assertFalse(recipe.shared)

    def test_shared_toggle(self):
        user = User.objects.create_user("alice", password="pass")
        recipe = Recipe.objects.create(
            user=user,
            title="Test Recipe",
            steps="Step 1",
        )
        recipe.shared = True
        recipe.save()
        recipe.refresh_from_db()
        self.assertTrue(recipe.shared)


class MealPlanHouseholdTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="pass")
        self.household = Household.objects.create(name="Test Kitchen", created_by=self.user)
        self.recipe = Recipe.objects.create(
            user=self.user,
            title="Test Recipe",
            steps="Step 1",
        )

    def test_mealplan_with_household(self):
        mp = MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date(2026, 3, 28),
            meal_type="dinner",
            recipe=self.recipe,
        )
        self.assertEqual(mp.household, self.household)
        self.assertEqual(mp.added_by, self.user)

    def test_mealplan_for_household_queryset(self):
        MealPlan.objects.create(
            household=self.household,
            added_by=self.user,
            date=date(2026, 3, 28),
            meal_type="dinner",
            recipe=self.recipe,
        )
        qs = MealPlan.objects.for_household(self.household)
        self.assertEqual(qs.count(), 1)


class ShoppingListItemHouseholdTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="pass")
        self.household = Household.objects.create(name="Test Kitchen", created_by=self.user)

    def test_shopping_item_with_household(self):
        item = ShoppingListItem.objects.create(
            household=self.household,
            added_by=self.user,
            name="Milk",
        )
        self.assertEqual(item.household, self.household)
        self.assertEqual(item.added_by, self.user)


class HouseholdSharingTests(TestCase):
    """Both users in a household should see the same MealPlan and ShoppingListItem."""

    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pass")
        self.bob = User.objects.create_user("bob", password="pass")
        self.household = Household.objects.create(name="Shared Kitchen", created_by=self.alice)
        HouseholdMembership.objects.create(user=self.alice, household=self.household)
        HouseholdMembership.objects.create(user=self.bob, household=self.household)
        self.recipe = Recipe.objects.create(
            user=self.alice,
            title="Shared Recipe",
            steps="Step 1",
        )

    def test_both_users_see_same_meal_plan(self):
        mp = MealPlan.objects.create(
            household=self.household,
            added_by=self.alice,
            date=date(2026, 3, 28),
            meal_type="dinner",
            recipe=self.recipe,
        )
        # Both users query via household -- they see the same meal plan
        alice_household = get_household(self.alice)
        bob_household = get_household(self.bob)
        self.assertEqual(alice_household, bob_household)
        alice_plans = MealPlan.objects.for_household(alice_household)
        bob_plans = MealPlan.objects.for_household(bob_household)
        self.assertEqual(list(alice_plans), list(bob_plans))
        self.assertIn(mp, alice_plans)

    def test_both_users_see_same_shopping_item(self):
        item = ShoppingListItem.objects.create(
            household=self.household,
            added_by=self.alice,
            name="Eggs",
        )
        alice_household = get_household(self.alice)
        bob_household = get_household(self.bob)
        alice_items = ShoppingListItem.objects.filter(household=alice_household)
        bob_items = ShoppingListItem.objects.filter(household=bob_household)
        self.assertEqual(list(alice_items), list(bob_items))
        self.assertIn(item, alice_items)


class RegistrationHouseholdTest(TestCase):
    def test_register_creates_new_household(self):
        client = Client()
        client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "Testpass123!",
                "password2": "Testpass123!",
            },
        )
        user = User.objects.get(username="newuser")
        self.assertTrue(hasattr(user, "household_membership"))

    def test_register_with_valid_code_joins_household(self):
        owner = User.objects.create_user("owner", password="testpass123")
        household = Household.objects.create(name="Family", created_by=owner)
        HouseholdMembership.objects.create(user=owner, household=household)

        client = Client()
        client.post(
            reverse("register"),
            {
                "username": "joiner",
                "email": "joiner@example.com",
                "password1": "Testpass123!",
                "password2": "Testpass123!",
                "household_code": household.code,
            },
        )
        joiner = User.objects.get(username="joiner")
        self.assertEqual(joiner.household_membership.household, household)

    def test_register_with_invalid_code_shows_error(self):
        client = Client()
        response = client.post(
            reverse("register"),
            {
                "username": "badcode",
                "email": "bad@example.com",
                "password1": "Testpass123!",
                "password2": "Testpass123!",
                "household_code": "XXXXXX",
            },
        )
        self.assertFalse(User.objects.filter(username="badcode").exists())
        self.assertContains(response, "Invalid household code")


class DayCommentViewTest(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Family")
        self.user = User.objects.create_user("mark", password="testpass123")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.client = Client()
        self.client.login(username="mark", password="testpass123")

    def test_add_day_comment(self):
        today_str = date.today().strftime("%Y-%m-%d")
        response = self.client.post(reverse("day_comment", args=[today_str]), {"text": "Work dinner"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(DayComment.objects.filter(household=self.household).exists())

    def test_comment_shows_on_week_view(self):
        DayComment.objects.create(household=self.household, user=self.user, date=date.today(), text="Out tonight")
        response = self.client.get(reverse("week"))
        self.assertContains(response, "Out tonight")

    def test_empty_text_deletes_comment(self):
        DayComment.objects.create(household=self.household, user=self.user, date=date.today(), text="Old note")
        today_str = date.today().strftime("%Y-%m-%d")
        self.client.post(reverse("day_comment", args=[today_str]), {"text": ""})
        self.assertFalse(DayComment.objects.filter(household=self.household, date=date.today()).exists())


class HouseholdViewIntegrationTest(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Family")
        self.user1 = User.objects.create_user("mark", password="testpass123")
        self.user2 = User.objects.create_user("lisa", password="testpass123")
        HouseholdMembership.objects.create(user=self.user1, household=self.household)
        HouseholdMembership.objects.create(user=self.user2, household=self.household)
        self.recipe = Recipe.objects.create(user=self.user1, title="Shared Dinner", steps="cook", shared=True)
        self.client1 = Client()
        self.client1.login(username="mark", password="testpass123")
        self.client2 = Client()
        self.client2.login(username="lisa", password="testpass123")

    def test_user2_sees_shared_recipe(self):
        response = self.client2.get(reverse("recipe_list"))
        self.assertContains(response, "Shared Dinner")

    def test_user2_does_not_see_unshared_recipe(self):
        Recipe.objects.create(user=self.user1, title="Private Meal", steps="cook", shared=False)
        response = self.client2.get(reverse("recipe_list"))
        self.assertNotContains(response, "Private Meal")

    def test_both_users_see_same_meal_plan(self):
        MealPlan.objects.create(
            household=self.household, added_by=self.user1, date=date.today(), meal_type="dinner", recipe=self.recipe
        )
        resp1 = self.client1.get(reverse("week"))
        resp2 = self.client2.get(reverse("week"))
        self.assertContains(resp1, "Shared Dinner")
        self.assertContains(resp2, "Shared Dinner")

    def test_both_users_see_same_shopping_items(self):
        ShoppingListItem.objects.create(household=self.household, added_by=self.user1, name="Eggs")
        resp1 = self.client1.get(reverse("shop"))
        resp2 = self.client2.get(reverse("shop"))
        self.assertContains(resp1, "Eggs")
        self.assertContains(resp2, "Eggs")
