"""Compose ranked, reasoned meal suggestions for a single date.

Depends on MealPlanningAssistantService for household-wide scoring/recency.
Deterministic: ranking is stable (score, then recipe id) so 'Swap' can walk
predictably to the next-best pick.
"""

from django.db.models import Avg, Q

from ..models import CookingNote, Recipe
from .meal_planning_assistant import MealPlanningAssistantService as MPA


class SuggestionService:
    @staticmethod
    def rank_for_slot(household, user, slot_date, exclude_ids=()):
        """Return [{recipe, score, reasons}] ranked best-first for slot_date."""
        prefs = MPA.get_or_create_preferences(user)

        if household:
            candidates = list(
                Recipe.objects.filter(
                    Q(user=user)
                    | Q(shared=True, user__household_membership__household=household)
                )
                .distinct()
                .prefetch_related("tags")
            )
        else:
            candidates = list(Recipe.objects.filter(user=user).prefetch_related("tags"))

        exclude = set(exclude_ids)
        pool = [r for r in candidates if r.id not in exclude]
        if not pool:
            return []

        recently = set(MPA.get_recently_cooked_recipes(user, prefs.avoid_repeat_days))
        fresh = [r for r in pool if r.id not in recently]
        pool = fresh or pool  # fall back if everything was recently cooked

        is_weekend = slot_date.weekday() in MPA.WEEKENDS
        max_time = prefs.max_weekend_time if is_weekend else prefs.max_weeknight_time
        time_ok = [r for r in pool if r.total_time is None or r.total_time <= max_time]
        pool = time_ok or pool

        scored = [
            (r, float(MPA.calculate_recipe_happiness_score(r, user))) for r in pool
        ]
        # Deterministic: highest score first, tie-break by id descending.
        scored.sort(key=lambda x: (x[1], x[0].id), reverse=True)

        return [
            {
                "recipe": r,
                "score": round(s),
                "reasons": SuggestionService.build_reasons(r, slot_date, prefs, user),
            }
            for r, s in scored
        ]

    @staticmethod
    def build_reasons(recipe, slot_date, prefs, user):
        """Human reason chips from data the scorer already uses."""
        user_ids = MPA._household_user_ids(user)
        reasons = []

        agg = CookingNote.objects.filter(
            recipe=recipe, user__in=user_ids, rating__isnull=False
        ).aggregate(avg=Avg("rating"))
        avg = agg["avg"]
        if avg is None:
            reasons.append({"icon": "bi-stars", "text": "Never tried"})
        elif avg >= 4.5:
            loved = "You both love it" if len(user_ids) > 1 else "You love it"
            reasons.append({"icon": "bi-heart-fill", "text": loved})
        else:
            reasons.append({"icon": "bi-star-fill", "text": f"{avg:.1f} avg"})

        latest = (
            CookingNote.objects.filter(recipe=recipe, user__in=user_ids)
            .order_by("-cooked_date")
            .first()
        )
        if latest:
            weeks = max((slot_date - latest.cooked_date).days // 7, 0)
            if weeks >= 1:
                unit = "wk" if weeks == 1 else "wks"
                reasons.append(
                    {"icon": "bi-clock-history", "text": f"{weeks} {unit} since"}
                )

        if recipe.total_time:
            reasons.append(
                {"icon": "bi-lightning-charge", "text": f"{recipe.total_time} min"}
            )

        return reasons

    @staticmethod
    def latest_household_note(recipe, user):
        """Most recent CookingNote for this recipe across the household, or None."""
        user_ids = MPA._household_user_ids(user)
        return (
            CookingNote.objects.filter(recipe=recipe, user__in=user_ids)
            .order_by("-cooked_date")
            .first()
        )
