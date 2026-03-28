import random
import string

from django.contrib.auth.models import User
from django.db import models


def generate_household_code():
    """Generate a 6-character alphanumeric code excluding ambiguous chars (0, O, 1, I, L)."""
    allowed = [c for c in string.ascii_uppercase + string.digits if c not in "0O1IL"]
    while True:
        code = "".join(random.choices(allowed, k=6))
        if not Household.objects.filter(code=code).exists():
            return code


class Household(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=8, unique=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_households"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_household_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class HouseholdMembership(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="household_membership"
    )
    household = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="members"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} in {self.household.name}"


class DayComment(models.Model):
    household = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="day_comments"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    text = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("household", "user", "date")

    def __str__(self):
        return f"{self.user.username} on {self.date}: {self.text[:30]}"


def get_household(user):
    """Return the user's household via household_membership, or None."""
    try:
        return user.household_membership.household
    except (HouseholdMembership.DoesNotExist, AttributeError):
        return None
