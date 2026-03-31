const CACHE_NAME = 'meal-planner-v3';
const STATIC_ASSETS = [
    '/static/recipes/css/app.css',
    '/static/recipes/js/app.js',
    '/static/recipes/js/push.js',
    '/static/recipes/icons/icon-192.png',
    '/static/recipes/icons/icon-512.png',
    '/offline/',
];

// Install: cache static assets and offline page
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        ).then(() => clients.claim())
    );
});

// Fetch: network-first for pages, cache-first for static
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Skip non-GET requests
    if (event.request.method !== 'GET') return;

    // Static assets: cache-first with network update
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

    // HTML pages: network-first, cache recipe and week pages
    if (event.request.mode === 'navigate' || event.request.headers.get('accept')?.includes('text/html')) {
        event.respondWith(
            fetch(event.request).then(response => {
                // Cache recipe detail pages, week view, and home for offline
                if (response.ok && (url.pathname.match(/^\/recipes\/\d+\/$/) || url.pathname === '/week/' || url.pathname === '/')) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                }
                return response;
            }).catch(() => {
                // Offline: try cache first
                return caches.match(event.request).then(cached => {
                    if (cached) return cached;
                    // Offline fallback page
                    return caches.match('/offline/');
                });
            })
        );
        return;
    }

    // Everything else: network with cache fallback
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
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
