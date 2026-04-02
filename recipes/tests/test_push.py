import json
from datetime import date, time
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from recipes.models import MealPlan, MealPlannerPreferences, Recipe
from recipes.models.household import Household, HouseholdMembership
from recipes.models.push import PushSubscription


class PushSubscriptionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )

    def test_create_subscription(self):
        sub = PushSubscription.objects.create(
            user=self.user,
            endpoint="https://push.example.com/sub/123",
            p256dh="test-p256dh-key",
            auth="test-auth-key",
        )
        self.assertEqual(str(sub), "Push sub for testuser")
        self.assertEqual(sub.user, self.user)

    def test_unique_constraint(self):
        PushSubscription.objects.create(
            user=self.user,
            endpoint="https://push.example.com/sub/123",
            p256dh="key1",
            auth="auth1",
        )
        with self.assertRaises(Exception):
            PushSubscription.objects.create(
                user=self.user,
                endpoint="https://push.example.com/sub/123",
                p256dh="key2",
                auth="auth2",
            )


@override_settings(
    VAPID_PUBLIC_KEY="test-public-key", VAPID_PRIVATE_KEY="test-private-key"
)
class PushViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.subscription_data = {
            "endpoint": "https://push.example.com/sub/456",
            "keys": {
                "p256dh": "test-p256dh",
                "auth": "test-auth",
            },
        }

    def test_vapid_public_key_requires_login(self):
        response = self.client.get(reverse("vapid_public_key"))
        self.assertEqual(response.status_code, 302)

    def test_vapid_public_key_returns_key(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("vapid_public_key"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["public_key"], "test-public-key")

    def test_subscribe_requires_login(self):
        response = self.client.post(
            reverse("push_subscribe"),
            data=json.dumps(self.subscription_data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)

    def test_subscribe_creates_subscription(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("push_subscribe"),
            data=json.dumps(self.subscription_data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(PushSubscription.objects.count(), 1)
        sub = PushSubscription.objects.first()
        self.assertEqual(sub.endpoint, "https://push.example.com/sub/456")
        self.assertEqual(sub.p256dh, "test-p256dh")
        self.assertEqual(sub.auth, "test-auth")

    def test_subscribe_updates_existing(self):
        self.client.login(username="testuser", password="testpass123")
        PushSubscription.objects.create(
            user=self.user,
            endpoint="https://push.example.com/sub/456",
            p256dh="old-key",
            auth="old-auth",
        )
        response = self.client.post(
            reverse("push_subscribe"),
            data=json.dumps(self.subscription_data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(PushSubscription.objects.count(), 1)
        sub = PushSubscription.objects.first()
        self.assertEqual(sub.p256dh, "test-p256dh")

    def test_subscribe_missing_data(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("push_subscribe"),
            data=json.dumps({"endpoint": "https://push.example.com/sub/456"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_subscribe_invalid_json(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("push_subscribe"),
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_unsubscribe_requires_login(self):
        response = self.client.post(
            reverse("push_unsubscribe"),
            data=json.dumps({"endpoint": "https://push.example.com/sub/456"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)

    def test_unsubscribe_deletes_subscription(self):
        self.client.login(username="testuser", password="testpass123")
        PushSubscription.objects.create(
            user=self.user,
            endpoint="https://push.example.com/sub/456",
            p256dh="key",
            auth="auth",
        )
        response = self.client.post(
            reverse("push_unsubscribe"),
            data=json.dumps({"endpoint": "https://push.example.com/sub/456"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PushSubscription.objects.count(), 0)

    def test_unsubscribe_invalid_json(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("push_unsubscribe"),
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


@override_settings(
    VAPID_PUBLIC_KEY="test-public-key",
    VAPID_PRIVATE_KEY="test-private-key",
    VAPID_ADMIN_EMAIL="mailto:test@example.com",
)
class SendDinnerRemindersTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.household = Household.objects.create(
            name="Test Home", code="ABC123", created_by=self.user
        )
        HouseholdMembership.objects.create(user=self.user, household=self.household)
        self.recipe = Recipe.objects.create(
            title="Test Recipe",
            user=self.user,
            steps="Step 1",
            cook_time=30,
        )

    @patch("recipes.management.commands.send_dinner_reminders.timezone")
    @patch("recipes.management.commands.send_dinner_reminders.webpush")
    def test_sends_reminder_for_matching_user(self, mock_webpush, mock_tz):
        from datetime import datetime

        from django.utils import timezone as real_tz

        now = real_tz.make_aware(datetime(2026, 3, 29, 16, 0, 0))
        mock_tz.localtime.return_value = now

        MealPlannerPreferences.objects.update_or_create(
            user=self.user,
            defaults={"reminder_time": time(16, 0)},
        )
        MealPlan.objects.create(
            household=self.household,
            date=date(2026, 3, 29),
            meal_type="dinner",
            recipe=self.recipe,
            added_by=self.user,
        )
        PushSubscription.objects.create(
            user=self.user,
            endpoint="https://push.example.com/sub/1",
            p256dh="key",
            auth="auth",
        )

        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("send_dinner_reminders", stdout=out)

        mock_webpush.assert_called_once()
        call_args = mock_webpush.call_args
        self.assertEqual(
            call_args[1]["subscription_info"]["endpoint"],
            "https://push.example.com/sub/1",
        )
        payload = json.loads(call_args[1]["data"])
        self.assertEqual(payload["title"], "Tonight's Dinner")
        self.assertIn("Test Recipe", payload["body"])
        self.assertIn("30 min", payload["body"])

    @patch("recipes.management.commands.send_dinner_reminders.timezone")
    @patch("recipes.management.commands.send_dinner_reminders.webpush")
    def test_skips_user_without_dinner(self, mock_webpush, mock_tz):
        from datetime import datetime

        from django.utils import timezone as real_tz

        now = real_tz.make_aware(datetime(2026, 3, 29, 16, 0, 0))
        mock_tz.localtime.return_value = now

        MealPlannerPreferences.objects.update_or_create(
            user=self.user,
            defaults={"reminder_time": time(16, 0)},
        )
        PushSubscription.objects.create(
            user=self.user,
            endpoint="https://push.example.com/sub/1",
            p256dh="key",
            auth="auth",
        )

        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("send_dinner_reminders", stdout=out)

        mock_webpush.assert_not_called()

    @patch("recipes.management.commands.send_dinner_reminders.timezone")
    @patch("recipes.management.commands.send_dinner_reminders.webpush")
    def test_removes_expired_subscription(self, mock_webpush, mock_tz):
        from datetime import datetime

        from django.utils import timezone as real_tz
        from pywebpush import WebPushException

        now = real_tz.make_aware(datetime(2026, 3, 29, 16, 0, 0))
        mock_tz.localtime.return_value = now

        MealPlannerPreferences.objects.update_or_create(
            user=self.user,
            defaults={"reminder_time": time(16, 0)},
        )
        MealPlan.objects.create(
            household=self.household,
            date=date(2026, 3, 29),
            meal_type="dinner",
            recipe=self.recipe,
            added_by=self.user,
        )
        PushSubscription.objects.create(
            user=self.user,
            endpoint="https://push.example.com/sub/1",
            p256dh="key",
            auth="auth",
        )

        # Simulate 410 Gone response
        mock_response = MagicMock()
        mock_response.status_code = 410
        mock_webpush.side_effect = WebPushException("Gone", response=mock_response)

        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("send_dinner_reminders", stdout=out)

        self.assertEqual(PushSubscription.objects.count(), 0)
        self.assertIn("Removed expired subscription", out.getvalue())

    @override_settings(VAPID_PRIVATE_KEY="", VAPID_PUBLIC_KEY="")
    def test_skips_when_no_vapid_keys(self):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("send_dinner_reminders", stdout=out)
        self.assertIn("VAPID keys not configured", out.getvalue())
