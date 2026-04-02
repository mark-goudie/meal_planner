from django.contrib.auth.models import User
from django.db import models


class CookingNote(models.Model):
    recipe = models.ForeignKey(
        "Recipe",
        on_delete=models.CASCADE,
        related_name="cooking_notes",
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="cooking_notes"
    )
    cooked_date = models.DateField()
    rating = models.IntegerField(
        null=True,
        blank=True,
        choices=[(i, str(i)) for i in range(1, 6)],
    )
    note = models.TextField(blank=True)
    would_make_again = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-cooked_date"]
        indexes = [
            models.Index(fields=["user", "-cooked_date"]),
        ]

    def __str__(self):
        return f"{self.recipe} on {self.cooked_date}"
