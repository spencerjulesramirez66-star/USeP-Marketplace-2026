(function () {
    'use strict';

    function init() {
        const results = document.getElementById('reputation-results');
        const announcer = document.getElementById('reputation-announcer');
        if (!results || !announcer) return;

        let controller = null;

        function syncFilters(url) {
            const form = results.querySelector('[data-reputation-form]');
            if (!form) return;
            const params = url.searchParams;
            form.querySelectorAll('select[name]').forEach((select) => {
                select.value = params.get(select.name) || '';
            });
        }

        function announceResult() {
            const line = results.querySelector('.reputation-results-heading p');
            if (line) announcer.textContent = line.textContent.trim();
        }

        function showError() {
            let error = results.querySelector('.reputation-error');
            if (!error) {
                error = document.createElement('div');
                error.className = 'reputation-error';
                error.setAttribute('role', 'alert');
                error.innerHTML = '<span>Reviews could not be updated. Check your connection and try again.</span> ';
                const retry = document.createElement('button');
                retry.type = 'button';
                retry.className = 'btn btn-outline';
                retry.dataset.reputationRetry = '';
                retry.textContent = 'Retry';
                error.append(retry);
                results.append(error);
            }
            error.hidden = false;
        }

        function buildFilterUrl() {
            const form = results.querySelector('[data-reputation-form]');
            const url = new URL(window.location.href);
            if (!form) return url;
            form.querySelectorAll('select[name]').forEach((select) => {
                if (select.value) url.searchParams.set(select.name, select.value);
                else url.searchParams.delete(select.name);
            });
            url.searchParams.set('page', '1');
            return url;
        }

        async function load(url, updateHistory) {
            if (controller) controller.abort();
            const requestController = new AbortController();
            controller = requestController;
            results.setAttribute('aria-busy', 'true');
            results.classList.add('is-loading');

            try {
                const response = await fetch(url, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    signal: requestController.signal,
                });
                if (!response.ok || response.redirected) throw new Error('Request failed');
                const html = await response.text();
                if (controller !== requestController) return;
                results.innerHTML = html;
                syncFilters(new URL(url, window.location.href));
                if (updateHistory) history.pushState(null, '', url);
                const error = results.querySelector('.reputation-error');
                if (error) error.remove();
                announceResult();
            } catch (error) {
                if (controller === requestController && error.name !== 'AbortError') {
                    syncFilters(new URL(window.location.href));
                    showError();
                }
            } finally {
                if (controller === requestController) {
                    results.removeAttribute('aria-busy');
                    results.classList.remove('is-loading');
                }
            }
        }

        results.addEventListener('change', (event) => {
            if (event.target.matches('[data-reputation-form] select')) {
                load(buildFilterUrl(), true);
            }
        });

        results.addEventListener('submit', (event) => {
            if (!event.target.matches('[data-reputation-form]')) return;
            event.preventDefault();
            load(buildFilterUrl(), true);
        });

        results.addEventListener('click', (event) => {
            const link = event.target.closest('[data-filter-url]');
            if (link && !event.ctrlKey && !event.metaKey && !event.shiftKey && event.button === 0) {
                event.preventDefault();
                load(new URL(link.href, window.location.href), true);
                return;
            }
            if (event.target.closest('[data-reputation-retry]')) {
                load(new URL(window.location.href), false);
            }
        });

        document.addEventListener('input', (event) => {
            const textarea = event.target.closest('[data-reply-counter]');
            if (!textarea) return;
            const counter = textarea.parentElement.querySelector('[data-character-count]');
            if (counter) counter.textContent = `${textarea.value.length} / 2000`;
        });

        window.addEventListener('popstate', () => {
            const url = new URL(window.location.href);
            load(url, false);
        });

        syncFilters(new URL(window.location.href));
        announceResult();
    }

    document.addEventListener('DOMContentLoaded', init);
})();
