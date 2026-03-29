import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from ..models.push import PushSubscription


@login_required
def vapid_public_key(request):
    """Return the VAPID public key for push subscription."""
    return JsonResponse({"public_key": settings.VAPID_PUBLIC_KEY})


@login_required
@require_POST
def push_subscribe(request):
    """Store a push subscription for the current user."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    endpoint = data.get("endpoint", "")
    keys = data.get("keys", {})
    p256dh = keys.get("p256dh", "")
    auth = keys.get("auth", "")

    if not endpoint or not p256dh or not auth:
        return JsonResponse({"error": "Missing subscription data"}, status=400)

    PushSubscription.objects.update_or_create(
        user=request.user,
        endpoint=endpoint,
        defaults={"p256dh": p256dh, "auth": auth},
    )
    return JsonResponse({"status": "subscribed"}, status=201)


@login_required
@require_POST
def push_unsubscribe(request):
    """Remove a push subscription."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    endpoint = data.get("endpoint", "")
    PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
    return JsonResponse({"status": "unsubscribed"})
