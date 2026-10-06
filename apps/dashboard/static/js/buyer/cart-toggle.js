/**
 * Add/remove-from-cart buttons (any <form data-cart-form>).
 * Posts via fetch, then updates the button icon and the navbar badge.
 * Uses event delegation, so it also works on feed HTML swapped in by live-search.js.
 */
(function () {
    'use strict';

    const FLASH_MS = 160;

    function renderCartState(button, inCart) {
        const title = button.dataset.listingTitle || 'listing';
        button.dataset.inCart = String(inCart);
        button.classList.toggle('cart-in-cart', inCart);
        button.innerHTML = `<i class="bi ${inCart ? 'bi-check-lg' : 'bi-cart3'}" aria-hidden="true"></i>`;
        button.setAttribute('aria-label', inCart ? `Remove ${title} from cart` : `Add ${title} to cart`);
        button.title = inCart ? 'Remove from cart' : 'Add to cart';
    }

    function updateCartBadge(count) {
        const badge = document.querySelector('#navbar-cart-badge');
        if (badge) badge.textContent = count;
    }

    function setBusy(button, busy) {
        button.disabled = busy;
        if (busy) button.setAttribute('aria-busy', 'true');
        else button.removeAttribute('aria-busy');
    }

    function onSubmit(event) {
        const form = event.target.closest('[data-cart-form]');
        if (!form) return;
        event.preventDefault();

        const button = form.querySelector('button[type="submit"]');
        if (!button || button.disabled) return;
        setBusy(button, true);

        fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        })
            .then((response) => response.json())
            .then((payload) => {
                if (typeof payload.saved !== 'boolean') throw new Error('Cart state could not be updated.');
                renderCartState(button, payload.saved);
                updateCartBadge(payload.cart_count);

                const flash = payload.saved ? 'cart-save-success' : 'cart-remove-success';
                button.classList.add(flash);
                window.setTimeout(() => button.classList.remove('cart-save-success', 'cart-remove-success'), FLASH_MS);
            })
            .catch((error) => console.error(error))
            .finally(() => setBusy(button, false));
    }

    document.addEventListener('submit', onSubmit);
})();
