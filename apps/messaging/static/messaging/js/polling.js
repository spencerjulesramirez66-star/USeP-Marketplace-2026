// A small, reusable poller: page-visibility-aware, cancels its own in-flight
// request before starting another, and backs off on repeated failures.
//
// This is the seam for a future move to WebSockets/Django Channels: whatever
// calls createPoller(fetchChanges, onResult) would instead subscribe to a
// socket and call the same onResult callback, and nothing else changes.

export function createPoller(fetchChanges, onResult, { intervalMs = 3000, maxIntervalMs = 20000 } = {}) {
    let timer = null;
    let controller = null;
    let currentInterval = intervalMs;
    let stopped = true;

    async function tick() {
        if (stopped) return;
        if (document.hidden) {
            schedule(currentInterval);
            return;
        }
        controller = new AbortController();
        try {
            const result = await fetchChanges(controller.signal);
            currentInterval = intervalMs;
            onResult(result);
        } catch (error) {
            if (error.name !== 'AbortError') {
                currentInterval = Math.min(currentInterval * 2, maxIntervalMs);
            }
        } finally {
            schedule(currentInterval);
        }
    }

    function schedule(delay) {
        clearTimeout(timer);
        if (!stopped) timer = setTimeout(tick, delay);
    }

    function start() {
        if (!stopped) return;
        stopped = false;
        tick();
    }

    function stop() {
        stopped = true;
        clearTimeout(timer);
        if (controller) controller.abort();
    }

    document.addEventListener('visibilitychange', () => {
        if (!document.hidden && !stopped) tick(); // catch up immediately when the tab returns
    });

    return { start, stop };
}
