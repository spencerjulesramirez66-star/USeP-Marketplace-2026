import { qs, qsa } from './dom.js';
import { get } from './api.js';

// The server only extracts URLs; the browser fetches a preview per link.
// Previews are cached so the panel can be re-rendered without refetching.

export function initLinkPreviews({ container, previewUrl }) {
    if (!container || !previewUrl) return { enrich() {} };
    const cache = new Map();

    function apply(card, preview) {
        const visual = qs('.messaging-link-card-visual', card);
        if (preview.image) {
            visual.classList.remove('placeholder');
            visual.innerHTML = `<img src="${preview.image}" alt="">`;
        }
        const titleEl = qs('.messaging-link-card-copy strong', card);
        if (titleEl && preview.title) {
            titleEl.textContent = preview.title;
            titleEl.title = preview.title;
        }
    }

    function enrich() {
        qsa('[data-shared-links] > .messaging-link-card', container).forEach(async (card) => {
            const visual = qs('.messaging-link-card-visual', card);
            if (!visual.classList.contains('placeholder')) return;
            if (cache.has(card.href)) {
                const cached = cache.get(card.href);
                if (cached) apply(card, cached);
                return;
            }
            cache.set(card.href, null);
            try {
                const data = await get(`${previewUrl}?url=${encodeURIComponent(card.href)}`);
                if (!data.preview) return;
                cache.set(card.href, data.preview);
                apply(card, data.preview);
            } catch { /* keep the placeholder */ }
        });
    }

    enrich();
    return { enrich };
}