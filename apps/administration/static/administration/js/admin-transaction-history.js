(() => {
    const root = document.getElementById('transaction-history');
    const form = document.getElementById('transaction-filters');
    const results = document.getElementById('transaction-results');
    const rowContainer = document.getElementById('transaction-rows');
    if (!root || !form || !results || !rowContainer) return;

    let controller;

    const queryFromForm = (resetPage = true) => {
        const params = new URLSearchParams(new FormData(form));
        for (const [key, value] of params.entries()) {
            if (!value) params.delete(key);
        }
        if (resetPage) params.delete('page');
        return params;
    };

    const cell = (text, secondary = '') => {
        const td = document.createElement('td');
        td.textContent = text || '';
        if (secondary) {
            const small = document.createElement('small');
            small.textContent = secondary;
            td.append(small);
        }
        return td;
    };

    const render = (data) => {
        rowContainer.replaceChildren();
        if (!data.results.length) {
            const row = document.createElement('tr');
            const empty = cell('No transactions match these filters.');
            empty.colSpan = 7;
            empty.className = 'transaction-empty';
            row.append(empty);
            rowContainer.append(row);
        }

        for (const item of data.results) {
            const row = document.createElement('tr');
            row.append(cell(item.display_id, item.type));

            const listingCell = document.createElement('td');
            if (item.listing_url) {
                const link = document.createElement('a');
                link.href = item.listing_url;
                link.textContent = item.listing_title;
                listingCell.append(link);
            } else {
                listingCell.textContent = item.listing_title;
            }
            const category = document.createElement('small');
            category.textContent = item.category;
            listingCell.append(category);
            row.append(listingCell);

            const partiesCell = document.createElement('td');
            partiesCell.textContent = item.buyer_name;
            const buyerStatus = document.createElement('small');
            buyerStatus.textContent = `Buyer · ${item.buyer_account_status}`;
            partiesCell.append(buyerStatus);
            const sellerName = document.createElement('span');
            sellerName.textContent = item.seller_name;
            const sellerStatus = document.createElement('small');
            sellerStatus.textContent = `Seller · ${item.seller_account_status}`;
            partiesCell.append(sellerName, sellerStatus);
            row.append(partiesCell);
            const statusCell = document.createElement('td');
            const badge = document.createElement('span');
            badge.className = `transaction-status transaction-status-${item.status_bucket}`;
            badge.textContent = item.status_bucket_label;
            statusCell.append(badge);
            row.append(statusCell);
            row.append(cell(item.total_display));
            row.append(cell(item.created_display));

            const actionCell = document.createElement('td');
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'transaction-icon-button';
            button.dataset.transactionId = item.id;
            button.setAttribute('aria-label', `View transaction ${item.display_id}`);
            const icon = document.createElement('i');
            icon.className = 'bi bi-chevron-right';
            icon.setAttribute('aria-hidden', 'true');
            button.append(icon);
            actionCell.append(button);
            row.append(actionCell);
            rowContainer.append(row);
        }

        const count = document.getElementById('transaction-result-count');
        if (count) count.textContent = `Showing ${data.start}–${data.end} of ${data.total} transactions`;
        renderPagination(data);
        const exportLink = document.querySelector('[data-export-link]');
        if (exportLink) exportLink.href = `${root.dataset.exportUrl}?${new URLSearchParams(data.filters)}`;
    };

    const renderPagination = (data) => {
        const pagination = document.getElementById('transaction-pagination');
        if (!pagination) return;
        pagination.replaceChildren();
        const range = document.createElement('span');
        range.textContent = `Showing ${data.start}–${data.end} of ${data.total}`;
        pagination.append(range);

        const controls = document.createElement('div');
        if (data.page > 1) addPageLink(controls, 'Previous', data.page - 1, data.filters);
        const label = document.createElement('span');
        label.textContent = `Page ${data.page} of ${data.num_pages || 1}`;
        controls.append(label);
        if (data.page < data.num_pages) addPageLink(controls, 'Next', data.page + 1, data.filters);
        pagination.append(controls);
    };

    const addPageLink = (container, text, page, filters) => {
        const params = new URLSearchParams(filters);
        params.set('page', page);
        const link = document.createElement('a');
        link.href = `?${params}`;
        link.dataset.page = page;
        link.textContent = text;
        container.append(link);
    };

    const showError = () => {
        document.getElementById('transaction-results-error')?.remove();
        const banner = document.createElement('div');
        banner.id = 'transaction-results-error';
        banner.className = 'transaction-results-error';
        const message = document.createElement('span');
        message.textContent = 'Transactions could not be loaded.';
        const retry = document.createElement('button');
        retry.type = 'button';
        retry.className = 'transaction-button';
        retry.textContent = 'Retry';
        retry.addEventListener('click', () => load(new URLSearchParams(location.search), false));
        banner.append(message, retry);
        results.before(banner);
    };

    const load = async (params, updateHistory = true) => {
        controller?.abort();
        controller = new AbortController();
        results.setAttribute('aria-busy', 'true');
        document.getElementById('transaction-results-error')?.remove();
        const url = `${root.dataset.dataUrl}?${params.toString()}`;
        try {
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                signal: controller.signal,
            });
            if (!response.ok) throw new Error('Request failed');
            const data = await response.json();
            render(data);
            if (updateHistory) history.pushState(null, '', `${location.pathname}${params.size ? `?${params}` : ''}`);
        } catch (error) {
            if (error.name !== 'AbortError') showError();
        } finally {
            if (!controller.signal.aborted) results.setAttribute('aria-busy', 'false');
        }
    };

    form.addEventListener('change', () => load(queryFromForm()));
    form.addEventListener('submit', (event) => {
        event.preventDefault();
        load(queryFromForm());
    });

    const search = form.elements.namedItem('q');
    let searchTimer;
    search?.addEventListener('input', () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => load(queryFromForm()), 250);
    });

    root.addEventListener('click', (event) => {
        const pageLink = event.target.closest('[data-page]');
        if (pageLink) {
            event.preventDefault();
            const params = new URLSearchParams(location.search);
            params.set('page', pageLink.dataset.page);
            load(params);
            return;
        }
        const clearLink = event.target.closest('[data-clear-filters]');
        if (clearLink) {
            event.preventDefault();
            for (const control of form.elements) {
                if (control.name) control.value = control.name === 'sort' ? 'newest' : '';
            }
            load(new URLSearchParams());
        }
    });

    window.addEventListener('popstate', () => {
        const params = new URLSearchParams(location.search);
        for (const control of form.elements) {
            if (control.name) control.value = params.get(control.name) || '';
        }
        load(params, false);
    });
})();
