from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from recipes.models.household import Household, HouseholdMembership


class BottomNavTests(TestCase):
    """The bottom nav is hx-boosted to swap only #main-content (no full reload)."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="navtester", password="pw")
        self.household = Household.objects.create(name="Home")
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.client.login(username="navtester", password="pw")

    def test_bottom_nav_is_boosted_to_main_content(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'hx-boost="true"')
        self.assertContains(response, 'hx-target="#main-content"')
        self.assertContains(response, 'hx-select="#main-content"')
