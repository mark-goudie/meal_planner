# Household Sharing — Design Spec

**Date:** 2026-03-29
**Status:** Approved

## Overview

Add household sharing so two users (Mark and Lisa) can collaborate on weekly meal planning, share a shopping list, and selectively share recipes. A household is joined via a simple 6-digit code shared verbally.

## Data Model

### New Models

**`Household`**
- `name` — CharField(100). E.g. "The Goudies"
- `code` — CharField(8), unique, auto-generated. Alphanumeric, case-insensitive. Displayed in Settings for sharing.
- `created_by` — FK(User, SET_NULL, nullable)
- `created_at` — DateTimeField(auto_now_add)

**`HouseholdMembership`**
- `user` — OneToOneField(User, CASCADE, related_name='household_membership')
- `household` — FK(Household, CASCADE, related_name='members')
- `joined_at` — DateTimeField(auto_now_add)

**`DayComment`**
- `household` — FK(Household, CASCADE, related_name='day_comments')
- `user` — FK(User, CASCADE) — who wrote it
- `date` — DateField
- `text` — CharField(200)
- `created_at` — DateTimeField(auto_now_add)
- Unique together: (household, user, date) — one comment per user per date

### Modified Models

**`Recipe`**
- Add: `shared` — BooleanField(default=False). When True, visible to all household members.

**`MealPlan`**
- Change: `user` FK → `household` FK(Household, CASCADE, related_name='meal_plans')
- Add: `added_by` FK(User, SET_NULL, nullable) — who added this meal
- Keep: date, meal_type, recipe FK, notes, unique_together changes to (household, date, meal_type)

**`ShoppingListItem`**
- Change: `user` FK → `household` FK(Household, CASCADE, related_name='shopping_items')
- Add: `added_by` FK(User, SET_NULL, nullable) — who added this item

### Migration Strategy

Existing data needs to be migrated:
1. Create a Household for each existing user
2. Create HouseholdMembership for each user → their household
3. Migrate MealPlan.user → MealPlan.household (set to user's household)
4. Migrate ShoppingListItem.user → ShoppingListItem.household
5. Drop old user FKs after data migration

## Sharing Rules

| Data | Behaviour |
|------|-----------|
| Meal Plan | Shared within household. Both see, add, remove, rearrange. |
| Shopping List | Shared within household. Both can add items and tick off. |
| Day Comments | Shared within household. Each user can add one comment per day. |
| Recipes | Private by default. Owner can toggle `shared=True` to make visible to household. |
| Cooking Notes | Personal. Visible to household members on shared recipes. |
| Settings/Preferences | Personal per user. |

## Query Changes

### Recipe List
- Show: `Recipe.objects.filter(Q(user=request.user) | Q(shared=True, user__household_membership__household=household))`
- Shared recipes from others show a "Shared by [name]" label.

### Meal Plan (This Week)
- Filter by `household` instead of `user`: `MealPlan.objects.filter(household=household)`
- Both users see identical view.

### Shopping List
- Filter by `household`: `ShoppingListItem.objects.filter(household=household)`
- Manual items show "added by [name]".

### Recipe Picker (assigning to meal plan)
- Show user's own recipes + household shared recipes.

### Suggest Meals
- Pull from all household-visible recipes (own + shared by household members).

## Registration Flow

1. Registration form adds optional field: "Have a household code?" with text input.
2. If code entered and valid: create user, join that household via HouseholdMembership.
3. If code empty: create user, create new Household (name defaults to "[username]'s Kitchen"), create HouseholdMembership.
4. If code entered but invalid: show error "Invalid household code."

## Settings Page Changes

New "Household" section:
- Household name (editable)
- Household code (displayed, copyable)
- "Regenerate Code" button
- Members list showing names and joined dates

## This Week UI Changes

### Day Comments
- Each day card shows a comment icon (bi-chat-dots) if any DayComment exists for that date.
- Comment text displays inline on the card below the meal: "Mark: Work dinner tonight" in muted text.
- Tapping the comment icon (or an "add comment" area on empty days) opens a small inline form (HTMX) to add/edit a comment.
- If a day has comments but no meal, the card shows the comment with "Tap to add a meal..." still visible.

### Added-by attribution
- Day cards show a subtle "added by [name]" if the meal was added by the other household member.

## Recipe Form Changes

- New toggle on recipe create/edit form: "Share with household" checkbox (default unchecked).
- When checked, recipe is visible to all household members in recipe list and meal plan picker.

## Shopping List Changes

- Manual items show "(added by Lisa)" or "(added by Mark)" in muted text.
- Tick state is shared — if Lisa ticks "eggs," Mark sees it ticked too.

## Helper Function

A utility to get the current user's household, used throughout views:

```python
def get_household(user):
    """Get the user's household. Returns None if user has no household."""
    try:
        return user.household_membership.household
    except HouseholdMembership.DoesNotExist:
        return None
```

## Code Generation for Households

```python
import secrets
import string

def generate_household_code():
    """Generate a 6-character alphanumeric code."""
    chars = string.ascii_uppercase + string.digits
    # Exclude ambiguous characters (0/O, 1/I/L)
    chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '').replace('L', '')
    while True:
        code = ''.join(secrets.choice(chars) for _ in range(6))
        if not Household.objects.filter(code=code).exists():
            return code
```
