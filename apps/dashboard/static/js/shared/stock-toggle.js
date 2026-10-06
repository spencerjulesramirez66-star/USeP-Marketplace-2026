/**
 * Hides the "Stock quantity" field whenever the selected category is
 * "Services" (slug: services), since services aren't tracked in units.
 * Works for every listing form on the site: add listing, manage item,
 * the buyer-detail quick edit modal, and the edit-listing page.
 *
 * This file also applies basic input failsafes to every "stock_quantity"
 * and "price" field on the page (regardless of which form they belong to),
 * since it's already loaded everywhere those fields appear. This is a
 * client-side convenience layer only — ListingForm in forms.py is the
 * real source of truth and re-validates/clamps everything server-side
 * (see clean_price / clean_stock_quantity), so a user bypassing JS
 * (disabled JS, direct POST, etc.) can't submit bad data either way.
 */
(function () {
    function isServiceCategory(select) {
        const selected = select.options[select.selectedIndex];
        return !!selected && selected.dataset.slug === 'services';
    }

    // ---- Stock quantity failsafes -----------------------------------
    // Strip anything non-numeric as the user types, then clamp to a
    // non-negative whole number (no empty value, no leading zeros, no
    // negative sign, no decimals) once they leave the field.
    function guardStockInput(input) {
        if (!input || input.dataset.guarded === 'stock') return;
        input.dataset.guarded = 'stock';

        input.addEventListener('input', () => {
            const cleaned = input.value.replace(/[^\d]/g, '');
            if (cleaned !== input.value) input.value = cleaned;
        });

        input.addEventListener('blur', () => {
            const numeric = parseInt(input.value, 10);
            input.value = Number.isNaN(numeric) || numeric < 0 ? '0' : String(numeric);
        });
    }

    // ---- Price failsafes ----------------------------------------------
    // Allow only digits and a single decimal point while typing, capped
    // at two decimal places (matches the server's price regex). On blur,
    // reject a negative or non-numeric result. An empty value is left
    // alone here since the field's own "required" validation covers that.
    function guardPriceInput(input) {
        if (!input || input.dataset.guarded === 'price') return;
        input.dataset.guarded = 'price';

        input.addEventListener('input', () => {
            let cleaned = input.value.replace(/[^\d.]/g, '');
            const [whole, ...decimalParts] = cleaned.split('.');
            cleaned = decimalParts.length ? `${whole}.${decimalParts.join('').slice(0, 2)}` : whole;
            if (cleaned !== input.value) input.value = cleaned;
        });

        input.addEventListener('blur', () => {
            if (input.value === '' || input.value === '.') return;
            const numeric = parseFloat(input.value);
            if (Number.isNaN(numeric) || numeric < 0) input.value = '0';
        });
    }

    function guardAllNumberFields() {
        document.querySelectorAll('input[name="stock_quantity"]').forEach(guardStockInput);
        document.querySelectorAll('input[name="price"]').forEach(guardPriceInput);
    }

    function bindStockToggle(categorySelectId, stockEditorId) {
        const categorySelect = document.getElementById(categorySelectId);
        const stockEditor = document.getElementById(stockEditorId);
        if (!categorySelect || !stockEditor) return;

        const sync = () => {
            const isService = isServiceCategory(categorySelect);
            stockEditor.hidden = isService;
            const stockInput = stockEditor.querySelector('input[name="stock_quantity"]');
            if (stockInput && isService) {
                stockInput.value = 0;
            }
        };

        categorySelect.addEventListener('change', sync);

        // Some forms (e.g. "Manage item") get their values filled in by
        // other scripts when the modal opens, so re-check visibility then too.
        const modal = categorySelect.closest('.modal-overlay');
        if (modal) {
            new MutationObserver(sync).observe(modal, { attributes: true, attributeFilter: ['hidden'] });
        }

        sync();
    }

    document.addEventListener('DOMContentLoaded', function () {
        bindStockToggle('listing-category', 'add-listing-stock-editor');
        bindStockToggle('manage-category', 'manage-stock-editor');
        bindStockToggle('detail-edit-category', 'detail-edit-stock-editor');
        bindStockToggle('id_category', 'edit-listing-stock-editor');
        guardAllNumberFields();
    });
})();