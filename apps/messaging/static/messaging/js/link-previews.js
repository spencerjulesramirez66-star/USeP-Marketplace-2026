import { qs, qsa, escapeHtml } from './dom.js';
import { get } from './api.js';

// Enriches the "Links" section of the details panel: the server only
// extracts URLs from message text (no network access there), so the browser
// fetches a small preview (title/image) for each link, one request per link.

export function initLinkPreviews({ container, previewUrl }) {
    if (!container || !previewUrl) return;

    qsa('[data-shared-links] > .messaging-link-card', container).forEach(async (card) => {
        const visual = qs('.messaging-link-card-visual', card);
        if (!visual.classList.contains('placeholder')) return; // already has an image from a previous render
        try {
            const data = await get(`${previewUrl}?url=${encodeURIComponent(card.href)}`);
            if (!data.preview) return;
            if (data.preview.image) {
                visual.classList.remove('placeholder');
                visual.innerHTML = `<img src="${data.preview.image}" alt="">`;
            }
            const titleEl = qs('.messaging-link-card-copy strong', card);
            if (titleEl && data.preview.title) {
                titleEl.textContent = data.preview.title;
                titleEl.title = data.preview.title;
            }
        } catch { /* keep the placeholder */ }
    });
}
