(() => {
    const root = document.getElementById('transaction-history');
    const drawer = document.getElementById('transaction-drawer');
    const content = document.getElementById('transaction-drawer-content');
    const title = document.getElementById('transaction-drawer-title');
    if (!drawer || !content || !title) return;

    const addField = (grid, label, value) => {
        const wrapper = document.createElement('div');
        const term = document.createElement('dt');
        term.textContent = label;
        const description = document.createElement('dd');
        description.textContent = value || '—';
        wrapper.append(term, description);
        grid.append(wrapper);
    };

    const render = (transaction) => {
        title.textContent = `Transaction ${transaction.display_id}`;
        content.replaceChildren();
        const grid = document.createElement('dl');
        grid.className = 'transaction-detail-grid';
        addField(grid, 'Status', transaction.status_bucket_label);
        addField(grid, 'Type', transaction.type);
        addField(grid, 'Listing', transaction.listing_title);
        addField(grid, 'Category', transaction.category);
        addField(grid, 'Buyer', `${transaction.buyer_name} (${transaction.buyer_email}) · ${transaction.buyer_account_status}`);
        addField(grid, 'Seller', `${transaction.seller_name} (${transaction.seller_email}) · ${transaction.seller_account_status}`);
        addField(grid, 'Quantity', String(transaction.quantity));
        addField(grid, 'Unit price', transaction.unit_price_display);
        addField(grid, 'Total', transaction.total_display);
        addField(grid, 'Payment method', transaction.payment_method);
        addField(grid, 'Payment reference', transaction.payment_reference);
        addField(grid, 'Payment proof uploaded', transaction.payment_proof_uploaded ? 'Yes' : 'No');
        addField(grid, 'Created (PHT)', transaction.created_display);
        addField(grid, 'Scheduled start (PHT)', transaction.scheduled_start);
        addField(grid, 'Scheduled end (PHT)', transaction.scheduled_end);
        addField(grid, 'Proposed start (PHT)', transaction.proposed_start);
        addField(grid, 'Proposed end (PHT)', transaction.proposed_end);
        addField(grid, 'Submitted (PHT)', transaction.submitted_at);
        addField(grid, 'Responded (PHT)', transaction.responded_at);
        addField(grid, 'Completed (PHT)', transaction.completed_at);
        content.append(grid);
    };

    document.addEventListener('click', async (event) => {
        const button = event.target.closest('[data-transaction-id]');
        if (button) {
            content.textContent = 'Loading transaction details…';
            drawer.showModal();
            const owner = button.closest('[data-detail-base]') || root;
            if (!owner) return;
            const endpoint = owner.dataset.detailBase.replace(/0\/$/, `${button.dataset.transactionId}/`);
            try {
                const response = await fetch(endpoint, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                if (!response.ok) throw new Error('Request failed');
                const data = await response.json();
                render(data.transaction);
            } catch {
                content.textContent = 'Transaction details could not be loaded. Close this panel and try again.';
            }
        }
        if (event.target.closest('[data-drawer-close]')) drawer.close();
    });

    drawer.addEventListener('click', (event) => {
        if (event.target === drawer) drawer.close();
    });
})();
