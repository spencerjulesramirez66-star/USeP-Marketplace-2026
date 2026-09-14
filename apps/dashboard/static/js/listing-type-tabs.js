/**
 * Powers the "Sell a product" / "Offer a service" tabs on the Add Listing
 * form. The model still only has one Category field — this just filters
 * which category and condition options are shown, based on data-slug and
 * data-type attributes the server already rendered onto each <option>.
 * No listing data is hardcoded here.
 */
(function () {
    function readOptions(select) {
        return Array.from(select.querySelectorAll('option')).map((option) => ({
            value: option.value,
            label: option.textContent,
            slug: option.dataset.slug || null,
            type: option.dataset.type || null,
        }));
    }

    function renderOptions(select, options, placeholder) {
        select.innerHTML = '';
        if (placeholder) {
            const placeholderOption = document.createElement('option');
            placeholderOption.value = '';
            placeholderOption.textContent = placeholder;
            placeholderOption.disabled = true;
            placeholderOption.selected = true;
            select.appendChild(placeholderOption);
        }
        options.forEach((item) => {
            const option = document.createElement('option');
            option.value = item.value;
            option.textContent = item.label;
            if (item.slug) option.dataset.slug = item.slug;
            if (item.type) option.dataset.type = item.type;
            select.appendChild(option);
        });
    }

    function setupTabs(formId, categorySelectId, conditionSelectId) {
        const form = document.getElementById(formId);
        const categorySelect = document.getElementById(categorySelectId);
        const conditionSelect = document.getElementById(conditionSelectId);
        if (!form || !categorySelect || !conditionSelect) return;

        const tabs = form.querySelectorAll('.type-tab');
        if (!tabs.length) return;

        // Snapshot the full, server-rendered option lists once, before we
        // start swapping the visible subset in and out.
        const allCategories = readOptions(categorySelect);
        const allConditions = readOptions(conditionSelect);

        function applyTab(type) {
            tabs.forEach((tab) => {
                const isActive = tab.dataset.type === type;
                tab.classList.toggle('active', isActive);
                tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
            });

            if (type === 'service') {
                const serviceCategories = allCategories.filter((item) => item.value && item.slug === 'services');
                renderOptions(
                    categorySelect,
                    serviceCategories,
                    serviceCategories.length ? null : 'No "Services" category set up yet'
                );
                categorySelect.disabled = serviceCategories.length === 0;
            } else {
                const productCategories = allCategories.filter((item) => item.value && item.slug !== 'services');
                renderOptions(categorySelect, productCategories, 'Choose a category');
                categorySelect.disabled = false;
            }

            renderOptions(conditionSelect, allConditions.filter((item) => item.type === type));

            // Let stock-toggle.js (and anything else listening) know the
            // category selection changed, so the stock field updates too.
            categorySelect.dispatchEvent(new Event('change'));
        }

        tabs.forEach((tab) => {
            tab.addEventListener('click', () => applyTab(tab.dataset.type));
        });

        // Reset to "product" every time the modal is (re)opened, so a
        // previous session doesn't leave it stuck on "service".
        const modal = form.closest('.modal-overlay');
        if (modal) {
            new MutationObserver(() => {
                if (!modal.hidden) applyTab('product');
            }).observe(modal, { attributes: true, attributeFilter: ['hidden'] });
        }

        applyTab('product');
    }

    document.addEventListener('DOMContentLoaded', function () {
        setupTabs('add-listing-form', 'listing-category', 'listing-condition');
    });
})();