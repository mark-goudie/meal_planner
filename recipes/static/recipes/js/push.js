async function setupPushNotifications() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.log('Push notifications not supported');
        return false;
    }

    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
        console.log('Notification permission denied');
        return false;
    }

    try {
        const registration = await navigator.serviceWorker.ready;

        // Get VAPID public key
        const keyResponse = await fetch('/api/push/vapid-key/');
        const { public_key } = await keyResponse.json();

        if (!public_key) {
            console.log('No VAPID key configured');
            return false;
        }

        // Subscribe
        const subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(public_key),
        });

        // Send to server
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
            || document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';

        await fetch('/api/push/subscribe/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify(subscription.toJSON()),
        });

        return true;
    } catch (err) {
        console.error('Push subscription failed:', err);
        return false;
    }
}

async function unsubscribePush() {
    try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.getSubscription();
        if (subscription) {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
                || document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';

            await fetch('/api/push/unsubscribe/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({ endpoint: subscription.endpoint }),
            });
            await subscription.unsubscribe();
        }
        return true;
    } catch (err) {
        console.error('Push unsubscribe failed:', err);
        return false;
    }
}

async function isPushSubscribed() {
    try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.getSubscription();
        return !!subscription;
    } catch {
        return false;
    }
}

function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = atob(base64);
    const arr = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) {
        arr[i] = raw.charCodeAt(i);
    }
    return arr;
}
