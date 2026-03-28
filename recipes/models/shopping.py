from django.contrib.auth.models import User
from django.db import models


class ShoppingListItem(models.Model):
    household = models.ForeignKey(
        "Household", on_delete=models.CASCADE, related_name="shopping_items",
    )
    added_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="+",
    )
    name = models.CharField(max_length=200)
    checked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["checked", "created_at"]

    def __str__(self):
        status = "x" if self.checked else " "
        return f"[{status}] {self.name}"
