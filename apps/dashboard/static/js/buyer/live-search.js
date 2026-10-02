/**
 * Live search: typing in the navbar search box refreshes #feed-results via AJAX
 * (debounced). Enter/submit uses the same path instead of a full page reload.
 */
(function () {
    'use strict';

    const DEBOUNCE_MS = 300;

    function init() {
        const form = document.querySelector('.navbar-search');
        const input = form ? form.querySelector('input[name="q"]') : null;
        const results = document.getElementById('feed-results');
        if (!form || !input || !results) return;

        let timer = null;
        let controller = null;

        function buildUrl() {
            const params = new URLSearchParams(window.location.search);
            const query = input.value.trim();
            if (query) params.set('q', query);
            else params.delete('q');
            return `${form.action}?${params.toString()}`;
        }

        function run() {
            const url = buildUrl();
            if (controller) controller.abort();
            controller = new AbortController();
            results.setAttribute('aria-busy', 'true');

            fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                signal: controller.signal,
            })
                .then((response) => {
                    if (!response.ok) throw new Error(`Search request failed: ${response.status}`);
                    return response.text();
                })
                .then((html) => {
                    results.innerHTML = html;
                    history.replaceState(null, '', url);
                })
                .catch((error) => {
                    if (error.name !== 'AbortError') console.error(error);
                })
                .finally(() => results.removeAttribute('aria-busy'));
        }

        input.addEventListener('input', () => {
            clearTimeout(timer);
            timer = setTimeout(run, DEBOUNCE_MS);
        });

        form.addEventListener('submit', (event) => {
            event.preventDefault();
            clearTimeout(timer);
            run();
        });
    }

    document.addEventListener('DOMContentLoaded', init);
})();
