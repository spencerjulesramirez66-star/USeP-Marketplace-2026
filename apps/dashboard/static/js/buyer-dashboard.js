document.addEventListener('DOMContentLoaded', () => {
    const renderCartState = (button, inCart) => {
        const listingTitle = button.dataset.listingTitle || 'listing';
        button.dataset.inCart = String(inCart);
        button.classList.toggle('cart-in-cart', inCart);
        button.innerHTML = `<i class="bi ${inCart ? 'bi-check-lg' : 'bi-cart3'}" aria-hidden="true"></i>`;
        button.setAttribute('aria-label', inCart ? `Remove ${listingTitle} from cart` : `Add ${listingTitle} to cart`);
        button.title = inCart ? 'Remove from cart' : 'Add to cart';
    };
    document.addEventListener('submit', (event) => {
        const form = event.target.closest('[data-cart-form]');
        if (!form) return;
        event.preventDefault();
        const button = form.querySelector('button[type="submit"]');
        if (!button || button.disabled) return;
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
        fetch(form.action, { method: 'POST', body: new FormData(form), credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then((response) => response.json())
            .then((payload) => {
                if (typeof payload.saved !== 'boolean') throw new Error('Cart state could not be updated.');
                renderCartState(button, payload.saved);
                button.classList.add(payload.saved ? 'cart-save-success' : 'cart-remove-success');
                button.removeAttribute('aria-busy');
                button.disabled = false;
                const badge = document.querySelector('#navbar-cart-badge'); if (badge) badge.textContent = payload.cart_count;
                window.setTimeout(() => {
                    button.classList.remove('cart-save-success', 'cart-remove-success');
                }, 160);
            }).catch(() => {
                button.disabled = false;
                button.removeAttribute('aria-busy');
            });
    });
    const mainImage = document.querySelector('.detail-image');
    const thumbs = document.querySelectorAll('.thumb');

    if (mainImage && thumbs.length) {
        const updateMainImage = (src) => {
            mainImage.style.backgroundImage = `url('${src}')`;
            thumbs.forEach((thumb) => thumb.classList.toggle('active', thumb.dataset.image === src));
        };

        thumbs.forEach((thumb) => {
            thumb.addEventListener('click', () => updateMainImage(thumb.dataset.image));
        });
    }

    // LIVE SEARCH
    // Types into the navbar search box and refreshes the product feed via
    // AJAX as the user types - no Enter, no full page reload. The navbar
    // markup (and its search form) is shared across pages, but this script
    // only loads on the buyer dashboard, so it's safe to wire up here
    // without needing to guard against other pages.
    const searchForm = document.querySelector('.navbar-search');
    const searchInput = searchForm ? searchForm.querySelector('input[name="q"]') : null;
    const feedResults = document.getElementById('feed-results');

    if (searchForm && searchInput && feedResults) {
        const SEARCH_DEBOUNCE_MS = 300;
        let debounceTimer = null;
        let activeRequest = null;

        const runSearch = () => {
            const params = new URLSearchParams(window.location.search);
            const query = searchInput.value.trim();
            if (query) {
                params.set('q', query);
            } else {
                params.delete('q');
            }
            const url = `${searchForm.action}?${params.toString()}`;

            if (activeRequest) activeRequest.abort();
            activeRequest = new AbortController();

            feedResults.setAttribute('aria-busy', 'true');

            fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                signal: activeRequest.signal,
            })
                .then((response) => {
                    if (!response.ok) throw new Error(`Search request failed: ${response.status}`);
                    return response.text();
                })
                .then((html) => {
                    feedResults.innerHTML = html;
                    history.replaceState(null, '', url);
                })
                .catch((error) => {
                    if (error.name !== 'AbortError') console.error(error);
                })
                .finally(() => {
                    feedResults.removeAttribute('aria-busy');
                });
        };

        searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(runSearch, SEARCH_DEBOUNCE_MS);
        });

        // Still handle Enter/submit (e.g. no-JS-first users, autofill,
        // mobile "go" button) by running the same AJAX path immediately
        // instead of letting the form do a full page reload.
        searchForm.addEventListener('submit', (event) => {
            event.preventDefault();
            clearTimeout(debounceTimer);
            runSearch();
        });
    }

    const backToTopButton = document.getElementById('back-to-top');
    if (backToTopButton) {
        const toggleBackToTop = () => backToTopButton.classList.toggle('visible', window.scrollY > 400);
        window.addEventListener('scroll', toggleBackToTop, { passive: true });
        backToTopButton.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
        toggleBackToTop();
    }
});
