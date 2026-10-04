import { initPurchaseRequests } from './purchase-request.js';

// Starts the purchase-request handlers on the messaging page.
// Does nothing when no conversation is open (the menu doesn't exist then).

const menu = document.getElementById('messaging-attachment-menu');
const toggleButton = document.getElementById('messaging-attachment-toggle');
const warning = document.getElementById('messaging-attachment-warning');

if (menu && toggleButton) {
    // Interim: reload so the server-rendered thread shows the new card state.
    // Swap these two for main.js's own append/replace helpers to update in place.
    const refresh = () => window.location.reload();

    initPurchaseRequests({
        menu,
        toggleButton,
        appendMessage: refresh,
        replaceMessage: refresh,
        showError: (message) => {
            if (!warning) return;
            warning.hidden = false;
            warning.textContent = message;
        },
    });
}