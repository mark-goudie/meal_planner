import json
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from pywebpush import webpush, WebPushException

from recipes.models import MealPlan, MealPlannerPreferences
from recipes.models.household import get_household
from recipes.models.push import PushSubscription


class Command(BaseCommand):
    help = "Send daily dinner reminder push notifications"

    def handle(self, *args, **options):
        if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
            self.stdout.write(self.style.WARNING("VAPID keys not configured. Skipping."))
            return

        now = timezone.localtime()
        today = now.date()
        current_time = now.time()

        # Find users whose reminder_time is within 5 minutes of now
        window_start = (datetime.combine(today, current_time) - timedelta(minutes=2)).time()
        window_end = (datetime.combine(today, current_time) + timedelta(minutes=3)).time()

        prefs = MealPlannerPreferences.objects.filter(
            reminder_time__gte=window_start,
            reminder_time__lte=window_end,
        ).select_related("user")

        sent_count = 0
        for pref in prefs:
            user = pref.user
            household = get_household(user)
            if not household:
                continue

            # Check for today's dinner
            meal = MealPlan.objects.filter(
                household=household, date=today, meal_type="dinner"
            ).select_related("recipe").first()

            if not meal:
                continue

            # Build notification payload
            cook_time = f" ({meal.recipe.cook_time} min)" if meal.recipe.cook_time else ""
            payload = json.dumps({
                "title": "Tonight's Dinner",
                "body": f"{meal.recipe.title}{cook_time}",
                "url": "/week/",
            })

            # Send to all of this user's subscriptions
            subscriptions = PushSubscription.objects.filter(user=user)
            for sub in subscriptions:
                try:
                    webpush(
                        subscription_info={
                            "endpoint": sub.endpoint,
                            "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                        },
                        data=payload,
                        vapid_private_key=settings.VAPID_PRIVATE_KEY,
                        vapid_claims={"sub": settings.VAPID_ADMIN_EMAIL},
                    )
                    sent_count += 1
                except WebPushException as e:
                    if e.response and e.response.status_code in (404, 410):
                        # Subscription expired, remove it
                        sub.delete()
                        self.stdout.write(f"Removed expired subscription for {user.username}")
                    else:
                        self.stdout.write(self.style.ERROR(f"Push failed for {user.username}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Sent {sent_count} dinner reminders"))
