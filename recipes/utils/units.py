"""Unit normalization utilities for AI-generated recipe ingredients."""

from ..models.recipe import UNIT_CHOICES

# Set of valid unit values from UNIT_CHOICES (excluding the empty string)
VALID_UNITS = {c[0] for c in UNIT_CHOICES if c[0]}

# Normalization map for common AI variations that don't match UNIT_CHOICES
UNIT_NORMALIZE = {
    "cloves": "clove",
    "grams": "g",
    "gram": "g",
    "kilograms": "kg",
    "kilogram": "kg",
    "milliliters": "ml",
    "millilitres": "ml",
    "milliliter": "ml",
    "millilitre": "ml",
    "liters": "l",
    "litres": "l",
    "liter": "l",
    "litre": "l",
    "teaspoon": "tsp",
    "teaspoons": "tsp",
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",
    "cups": "cup",
    "ounces": "oz",
    "ounce": "oz",
    "pounds": "lb",
    "pound": "lb",
    "pieces": "piece",
    "slices": "slice",
    "pinches": "pinch",
    "handfuls": "handful",
    "bunches": "bunch",
    "cans": "can",
    "whole": "piece",
    "medium": "piece",
    "large": "piece",
    "small": "piece",
    "stalks": "piece",
    "stalk": "piece",
    "heads": "piece",
    "head": "piece",
    "sprigs": "bunch",
    "sprig": "bunch",
}


def normalize_unit(raw_unit):
    """Normalize an AI-returned unit string to a valid UNIT_CHOICES value.

    Returns the matching UNIT_CHOICES key, or "" if the unit is unknown.
    """
    if not raw_unit:
        return ""
    unit = raw_unit.lower().strip()
    # Direct match against valid unit keys
    if unit in VALID_UNITS:
        return unit
    # Check normalization map
    if unit in UNIT_NORMALIZE:
        return UNIT_NORMALIZE[unit]
    # Unknown unit -- default to empty string
    return ""
