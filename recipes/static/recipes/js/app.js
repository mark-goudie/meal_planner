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
