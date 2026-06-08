document.addEventListener('alpine:init', () => {
    Alpine.data('cookingMode', () => ({
        wakeLock: null,
        async init() {
            if ('wakeLock' in navigator) {
                try {
                    this.wakeLock = await navigator.wakeLock.request('screen');
                } catch (e) { /* permission denied or not supported */ }
            }
        },
        destroy() {
            if (this.wakeLock) { this.wakeLock.release(); this.wakeLock = null; }
        }
    }));
});

// View Transitions: expose the triggering control's data-vt-dir on <html> for the
// duration of the swap, so scoped CSS can slide the page back/forward.
document.body.addEventListener('htmx:beforeRequest', (e) => {
    const dir = e.detail.elt && e.detail.elt.dataset ? e.detail.elt.dataset.vtDir : null;
    if (dir) {
        document.documentElement.dataset.vtDir = dir;
    } else {
        delete document.documentElement.dataset.vtDir;
    }
});
document.body.addEventListener('htmx:afterSettle', () => {
    delete document.documentElement.dataset.vtDir;
});
