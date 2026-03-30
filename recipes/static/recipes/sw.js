const CACHE_NAME = 'meal-planner-v2';
const PRECACHE_URLS = [
    '/static/recipes/css/app.css',
    '/static/recipes/js/app.js',
    '/static/recipes/js/push.js',
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    // Clean up old caches
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        ).then(() => clients.claim())
    );
});

self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Stale-while-revalidate for static assets (CSS, JS, fonts, images)
    if (url.pathname.startsWith('/static/') || url.hostname === 'cdn.jsdelivr.net' || url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') {
        event.respondWith(
            caches.open(CACHE_NAME).then(cache =>
                cache.match(event.request).then(cached => {
                    const fetched = fetch(event.request).then(response => {
                        if (response.ok) {
                            cache.put(event.request, response.clone());
                        }
                        return response;
                    }).catch(() => cached);
                    return cached || fetched;
                })
            )
        );
        return;
    }

    // Network-first strategy for navigation — fall back to cache only when offline
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                    return response;
                })
                .catch(() => caches.match(event.request))
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
