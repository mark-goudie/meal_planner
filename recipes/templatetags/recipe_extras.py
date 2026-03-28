import hashlib

import anthropic
from django import template
from django.conf import settings

register = template.Library()


@register.filter
def get_meal(plans, meal_type):
    """
    Returns the first plan in the list with the given meal_type, or None.
    """
    for plan in plans:
        if getattr(plan, "meal_type", None) == meal_type:
            return plan
    return None


@register.filter
def get(dict_obj, key):
    return dict_obj.get(key)


@register.filter
def recipe_gradient(title):
    """Generate a CSS gradient from recipe title hash."""
    h = hashlib.md5(title.lower().encode()).hexdigest()
    hue1 = int(h[:3], 16) % 360
    hue2 = (hue1 + 40 + int(h[3:5], 16) % 40) % 360
    return f"linear-gradient(135deg, hsl({hue1}, 65%, 45%), hsl({hue2}, 55%, 35%))"


@register.filter
def recipe_initials(title):
    """Get initials from recipe title (max 2 chars)."""
    words = title.strip().split()
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    elif words:
        return words[0][:2].upper()
    return "?"


def ai_generate_surprise_recipe():
    prompt = (
        "Create a unique, family-friendly recipe using a mix of common and surprising ingredients. "
        "Include a title, ingredients, and clear steps. Format as:\n"
        "Title:\nIngredients:\nSteps:"
    )
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        system="You're a helpful chef assistant.",
        messages=[
            {"role": "user", "content": prompt},
        ],
    )
    content = next((b.text for b in response.content if b.type == "text"), "")
    return content.strip() if content else None
