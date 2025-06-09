from django import template

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