"""Management command to fix existing bad ingredient data.

Normalizes invalid unit strings on RecipeIngredient records and removes
blank-name Ingredient records (and their associated RecipeIngredient rows).
"""

from django.core.management.base import BaseCommand

from recipes.models import Ingredient, RecipeIngredient
from recipes.utils.units import VALID_UNITS, normalize_unit


class Command(BaseCommand):
    help = "Normalize invalid unit strings on RecipeIngredient records and remove blank-name ingredients."

    def handle(self, *args, **options):
        # Fix 4: Normalize bad units
        fixed = 0
        for ri in RecipeIngredient.objects.exclude(unit__in=VALID_UNITS).exclude(unit=""):
            old = ri.unit
            new = normalize_unit(old)
            if new != old:
                ri.unit = new
                ri.save(update_fields=["unit"])
                fixed += 1
                self.stdout.write(f"  {ri.ingredient.name}: '{old}' -> '{new}'")

        self.stdout.write(self.style.SUCCESS(f"Fixed {fixed} RecipeIngredient unit(s)."))

        # Fix 5: Remove blank-name Ingredient records
        blank = Ingredient.objects.filter(name="")
        if blank.exists():
            ri_count = RecipeIngredient.objects.filter(ingredient__name="").count()
            RecipeIngredient.objects.filter(ingredient__name="").delete()
            blank_count = blank.count()
            blank.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Removed {blank_count} blank Ingredient record(s) "
                    f"and {ri_count} associated RecipeIngredient row(s)."
                )
            )
        else:
            self.stdout.write("No blank-name Ingredient records found.")
