from django import template
import openai
from django.conf import settings

register = template.Library()

@register.filter
def get_meal(plans, meal_type):
    """
    Returns the first plan in the list with the given meal_type, or None.
    """
    for plan in plans:
        if getattr(plan, 'meal_type', None) == meal_type:
            return plan
    return None

@register.filter
def get(dict_obj, key):
    return dict_obj.get(key)

def ai_generate_surprise_recipe():
    prompt = (
        "Create a unique, family-friendly recipe using a mix of common and surprising ingredients. "
        "Include a title, ingredients, and clear steps. Format as:\n"
        "Title:\nIngredients:\nSteps:"
    )
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You're a helpful chef assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.9
    )
    content = response.choices[0].message.content
    return content.strip() if content else None

