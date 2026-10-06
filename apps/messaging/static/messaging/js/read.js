import { postForm } from './api.js';

// Marks the other participant's messages as read: once on load, and again
// whenever new messages arrive while the tab is visible and focused.

export function initRead({ readUrl }) {
    if (!readUrl) return { markRead() {} };

    let pending = false;

    function markRead() {
        if (document.hidden || pending) return;
        pending = true;
        postForm(readUrl, new FormData())
            .catch(() => {})
            .finally(() => { pending = false; });
    }

    markRead();
    document.addEventListener('visibilitychange', () => { if (!document.hidden) markRead(); });
    window.addEventListener('focus', markRead);

    return { markRead };
}
