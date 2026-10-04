import { on } from './dom.js';

// Wires up the two chat-side purchase interactions:
//   1. Seller: "Confirm purchase" item in the attachment menu -> posts a card.
//   2. Either side: buttons on a card (cancel / confirm / decline) -> posts the
//      action and swaps the card's HTML for the server's updated version.
//
// The server decides who may do what (listing owner / buyer). The composer
// only renders the menu item for the listing owner, but that's cosmetic.

function csrfToken() {
    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    return input ? input.value : '';
}

async function post(url, body) {
    const response = await fetch(url, {
        method: 'POST',
        body,
        credentials: 'same-origin',
        headers: {
            'X-CSRFToken': csrfToken(),
            'X-Requested-With': 'XMLHttpRequest',
            Accept: 'application/json',
        },
    });
    const data = await response.json().catch(() => null);
    if (!response.ok || !data || !data.ok) {
        throw new Error((data && data.error) || 'Something went wrong. Please try again.');
    }
    return data;
}

/**
 * @param {object}   opts
 * @param {Element}  opts.menu            the attachment menu (#messaging-attachment-menu)
 * @param {Element}  opts.toggleButton    the "+" button (#messaging-attachment-toggle)
 * @param {Function} opts.appendMessage   (html, id) => void. Your existing "add a message to the thread" code.
 * @param {Function} opts.showError       (message) => void. E.g. the attachment warning element.
 * @param {Function} [opts.replaceMessage] (html, id) => void. Defaults to swapping [data-message-id="<id>"].
 */
export function initPurchaseRequests({ menu, toggleButton, appendMessage, showError, replaceMessage }) {
    const replace = replaceMessage || ((html, id) => {
        const node = document.querySelector(`[data-message-id="${id}"]`);
        if (node) node.outerHTML = html;
    });

    // 1. Seller sends the card
    on(menu, 'click', '[data-purchase-request]', async (evt, target) => {
        menu.hidden = true;
        toggleButton.setAttribute('aria-expanded', 'false');
        target.disabled = true;
        try {
            const data = await post(target.dataset.url);
            appendMessage(data.html, data.id);
        } catch (error) {
            showError(error.message);
        } finally {
            target.disabled = false;
        }
    });

    // 2. Buttons inside a card
    on(document, 'click', '[data-purchase-action]', async (evt, target) => {
        const body = new FormData();
        body.append('action', target.dataset.purchaseAction);
        const buttons = target.closest('.messaging-purchase-card__actions').querySelectorAll('button');
        buttons.forEach((b) => { b.disabled = true; });
        try {
            const data = await post(target.dataset.url, body);
            replace(data.html, data.id);
        } catch (error) {
            buttons.forEach((b) => { b.disabled = false; });
            showError(error.message);
        }
    });
}