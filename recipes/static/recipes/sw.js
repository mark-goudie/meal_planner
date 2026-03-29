const CACHE_NAME = 'meal-planner-v1';

self.addEventListener('install', event => {
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(clients.claim());
});

self.addEventListener('fetch', event => {
    // Network-first strategy — fall back to cache only when offline
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).catch(() => caches.match(event.request))
        );
    }
});

// Push notification handler
self.addEventListener('push', event => {
    const data = event.data ? event.data.json() : {};
    const title = data.title || 'Meal Planner';
    const options = {
        body: data.body || '',
        icon: '/static/recipes/icons/icon-192.png',
        badge: '/static/recipes/icons/icon-192.png',
        data: { url: data.url || '/week/' },
        vibrate: [100, 50, 100],
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

// Notification click handler
self.addEventListener('notificationclick', event => {
    event.notification.close();
    const url = event.notification.data?.url || '/week/';
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then(clientList => {
            for (const client of clientList) {
                if (client.url.includes(url) && 'focus' in client) {
                    return client.focus();
                }
            }
            return clients.openWindow(url);
        })
    );
});
