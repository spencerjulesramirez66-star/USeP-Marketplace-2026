import { qs, debounce, escapeHtml } from './dom.js';
import { get } from './api.js';

const MIN_QUERY_LENGTH = 2;
const DEBOUNCE_MS = 250;

// Conversation search (sidebar) and message search (inside a thread) are
// separate features with separate endpoints and result panels, but share
// the same debounce/cancel/render shape, so one module covers both.

export function initConversationSearch({ input, resultsEl, searchUrl, listEl }) {
    if (!input) return;
    let controller = null;

    const run = debounce(async (query) => {
        if (query.length < MIN_QUERY_LENGTH) {
            resultsEl.hidden = true;
            listEl.hidden = false;
            return;
        }
        controller?.abort();
        controller = new AbortController();
        try {
            const data = await get(`${searchUrl}?q=${encodeURIComponent(query)}`, { signal: controller.signal });
            listEl.hidden = true;
            resultsEl.hidden = false;
            resultsEl.innerHTML = data.results.length
                ? data.results.map((c) => `
                    <a class="conversation-row" href="${c.url}">
                        <img class="conversation-avatar" src="${c.image_url}" alt="">
                        <span class="conversation-row-copy"><strong>${escapeHtml(c.listing_title)}</strong><span>${escapeHtml(c.participant.name)}</span></span>
                        ${c.unread_count ? `<span class="conversation-unread-badge">${c.unread_count}</span>` : ''}
                    </a>`).join('')
                : '<div class="conversation-empty"><span>No matching conversations.</span></div>';
        } catch (error) {
            if (error.name !== 'AbortError') resultsEl.innerHTML = '<div class="conversation-empty"><span>Search failed. Try again.</span></div>';
        }
    }, DEBOUNCE_MS);

    input.addEventListener('input', () => run(input.value.trim()));
}

export function initMessageSearch({ toggleButton, panel, headerEl, input, statusEl, resultsEl, prevButton, nextButton, counterEl, searchUrl, onJumpTo, closeButton }) {
    if (!toggleButton) return;
    let matches = [];
    let activeIndex = -1;
    let controller = null;

    function open() {
        panel.hidden = false;
        headerEl.hidden = false;
        toggleButton.setAttribute('aria-expanded', 'true');
        input.focus();
    }
    function close() {
        panel.hidden = true;
        headerEl.hidden = true;
        toggleButton.setAttribute('aria-expanded', 'false');
        input.value = '';
        matches = [];
        activeIndex = -1;
        updateNav();
    }

    function updateNav() {
        const hasMatches = matches.length > 0;
        prevButton.hidden = nextButton.hidden = !hasMatches;
        prevButton.disabled = nextButton.disabled = !hasMatches;
        counterEl.hidden = !hasMatches;
        if (hasMatches) counterEl.textContent = `${activeIndex + 1} / ${matches.length}`;
    }

    const run = debounce(async (query) => {
        if (query.length < MIN_QUERY_LENGTH) {
            statusEl.hidden = false;
            statusEl.textContent = 'Type at least 2 characters to search.';
            resultsEl.innerHTML = '';
            matches = [];
            updateNav();
            return;
        }
        controller?.abort();
        controller = new AbortController();
        try {
            const data = await get(`${searchUrl}?q=${encodeURIComponent(query)}`, { signal: controller.signal });
            matches = data.results;
            activeIndex = matches.length ? 0 : -1;
            statusEl.hidden = true;
            resultsEl.innerHTML = matches.length
                ? matches.map((m, i) => `
                    <button type="button" class="messaging-message-search-result" data-index="${i}">
                        <strong>${escapeHtml(m.sender)}</strong><span>${escapeHtml(m.snippet)}</span>
                    </button>`).join('')
                : '<p class="messaging-message-search-status">No matches.</p>';
            updateNav();
        } catch (error) {
            if (error.name !== 'AbortError') resultsEl.innerHTML = '<p class="messaging-message-search-status">Search failed.</p>';
        }
    }, DEBOUNCE_MS);

    input.addEventListener('input', () => run(input.value.trim()));
    resultsEl.addEventListener('click', (evt) => {
        const button = evt.target.closest('[data-index]');
        if (!button) return;
        activeIndex = Number(button.dataset.index);
        updateNav();
        onJumpTo(matches[activeIndex].id);
    });
    prevButton.addEventListener('click', () => {
        if (!matches.length) return;
        activeIndex = (activeIndex - 1 + matches.length) % matches.length;
        updateNav();
        onJumpTo(matches[activeIndex].id);
    });
    nextButton.addEventListener('click', () => {
        if (!matches.length) return;
        activeIndex = (activeIndex + 1) % matches.length;
        updateNav();
        onJumpTo(matches[activeIndex].id);
    });
    toggleButton.addEventListener('click', () => (panel.hidden ? open() : close()));
    closeButton.addEventListener('click', close);
}
