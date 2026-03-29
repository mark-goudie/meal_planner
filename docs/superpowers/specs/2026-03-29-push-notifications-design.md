# Push Notifications — Design Spec

**Date:** 2026-03-29
**Status:** Approved
**Scope:** Daily dinner reminder only (household activity and planning reminders deferred)

## Overview

Send a daily push notification reminding the user of tonight's planned dinner. "Tonight's dinner: Thai Green Curry (40 min)". Only sent if there's a meal planned for today. Reminder time is configurable per user (default 4:00 PM).

## How Web Push Works

1. User visits the app, browser requests notification permission
2. If granted, browser creates a push subscription (endpoint + keys)
3. Subscription is sent to our server and stored
4. A scheduled management command runs periodically, checks which users should receive reminders now, and sends push notifications via the Web Push protocol
5. Service worker receives the push event and displays the notification

## Data Model

### New Model: `PushSubscription`

```
recipes/models/push.py

PushSubscription:
  - user: FK(User, CASCADE, related_name="push_subscriptions")
  - endpoint: URLField(max_length=500)
  - p256dh: CharField(max_length=200) — browser public key
  - auth: CharField(max_length=200) — browser auth secret
  - created_at: DateTimeField(auto_now_add)

  Meta: unique_together = (user, endpoint)
```

One user can have multiple subscriptions (phone + laptop).

### Modified Model: `MealPlannerPreferences`

Add field:
- `reminder_time` — TimeField(default=time(16, 0), help_text="Daily dinner reminder time")

## VAPID Keys

Web Push requires VAPID (Voluntary Application Server Identification) keys. Generated once, stored in `.env`:

```
VAPID_PRIVATE_KEY=<base64 encoded>
VAPID_PUBLIC_KEY=<base64 encoded>
VAPID_ADMIN_EMAIL=mark@example.com
```

Generate with: `python -c "from pywebpush import Vapid; v = Vapid(); v.generate_keys(); print(v.private_pem()); print(v.public_key)"`

Or use the `py_vapid` CLI: `vapid --gen`

## Backend

### Dependencies

Add to requirements.txt:
- `pywebpush>=2.0.0` — for sending push notifications
- `py-vapid>=1.9.0` — for VAPID key management

### Settings

In `config/settings.py`:
```python
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_ADMIN_EMAIL = os.getenv("VAPID_ADMIN_EMAIL", "")
```

### Views: `recipes/views/push.py`

**`push_subscribe(request)`** — POST
- Accepts JSON body: `{endpoint, keys: {p256dh, auth}}`
- Creates or updates PushSubscription for the user
- Returns 201

**`push_unsubscribe(request)`** — POST
- Accepts JSON body: `{endpoint}`
- Deletes the matching PushSubscription
- Returns 200

**`vapid_public_key(request)`** — GET
- Returns the VAPID public key as JSON (needed by the browser to create subscriptions)

### Management Command: `send_dinner_reminders`

`recipes/management/commands/send_dinner_reminders.py`

Logic:
1. Get current time (in the user's timezone — use settings.TIME_ZONE for now since both users are in Sydney)
2. Find all users whose `reminder_time` matches the current hour and minute (within a 5-minute window to account for cron timing)
3. For each user, check if there's a MealPlan for today in their household
4. If yes, build the notification payload: `{title: "Tonight's Dinner", body: "Thai Green Curry (40 min)", url: "/week/"}`
5. Send via `pywebpush.webpush()` to all of that user's PushSubscriptions
6. Handle expired/invalid subscriptions — delete them on 404/410 response

Run via cron every 5 minutes: `*/5 * * * * cd /path/to/project && python manage.py send_dinner_reminders`

## Frontend

### Service Worker: `recipes/static/recipes/sw.js`

Add push event handler:
```javascript
self.addEventListener('push', event => {
    const data = event.data ? event.data.json() : {};
    const title = data.title || 'Meal Planner';
    const options = {
        body: data.body || '',
        icon: '/static/recipes/icons/icon-192.png',
        badge: '/static/recipes/icons/icon-192.png',
        data: { url: data.url || '/week/' },
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', event => {
    event.notification.close();
    const url = event.notification.data?.url || '/week/';
    event.waitUntil(clients.openWindow(url));
});
```

### Push Registration: `recipes/static/recipes/js/push.js`

```javascript
async function setupPushNotifications() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;

    const permission = await Notification.requestPermission();
    if (permission !== 'granted') return;

    const registration = await navigator.serviceWorker.ready;

    // Get VAPID public key from server
    const keyResponse = await fetch('/api/push/vapid-key/');
    const { public_key } = await keyResponse.json();

    const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(public_key),
    });

    // Send subscription to server
    await fetch('/api/push/subscribe/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(subscription),
    });
}
```

### When to prompt for permission

Don't prompt on first page load — that's annoying. Instead:
- Show a subtle banner on the Settings page: "Enable dinner reminders?" with an "Enable" button
- Clicking "Enable" triggers `Notification.requestPermission()` and the subscription flow
- If already subscribed, show "Reminders enabled" with a "Disable" button

### Settings Page

Add a "Notifications" section:
- Reminder time picker (time input, default 16:00)
- Enable/Disable push notifications button
- Status indicator: "Enabled" / "Not enabled"

## URL Patterns

```python
path("api/push/subscribe/", push_subscribe, name="push_subscribe"),
path("api/push/unsubscribe/", push_unsubscribe, name="push_unsubscribe"),
path("api/push/vapid-key/", vapid_public_key, name="vapid_public_key"),
```

## Files to Create/Modify

### New:
- `recipes/models/push.py` — PushSubscription model
- `recipes/views/push.py` — subscribe/unsubscribe/vapid-key views
- `recipes/management/commands/send_dinner_reminders.py` — scheduled command
- `recipes/static/recipes/js/push.js` — browser push registration
- `recipes/tests/test_push.py` — tests

### Modified:
- `recipes/models/__init__.py` — export PushSubscription
- `recipes/models/meal_plan.py` — add reminder_time to MealPlannerPreferences
- `recipes/views/__init__.py` — export push views
- `recipes/urls.py` — add push API routes
- `recipes/static/recipes/sw.js` — add push/notification event handlers
- `recipes/templates/settings/settings.html` — add notifications section
- `recipes/templates/base.html` — load push.js
- `requirements.txt` — add pywebpush
- `.env.example` — add VAPID keys
- `config/settings.py` — add VAPID settings
