/* Seller dashboard page: type tabs, add-listing photos, manage modal, delete, filters. Needs seller-core.js. */

/* ===== listing-type-tabs ===== */
/* "Sell a product" / "Offer a service" tabs on the Add Listing form.
   The model still has one Category field; this only filters which category and
   condition options are shown, using data-slug / data-type the server rendered
   onto each <option>. No listing data is hardcoded here. */
(function (Seller) {
    function setupTabs(formId, categorySelectId, conditionSelectId) {
        const form = document.getElementById(formId);
        const categorySelect = document.getElementById(categorySelectId);
        const conditionSelect = document.getElementById(conditionSelectId);
        if (!form || !categorySelect || !conditionSelect) return;

        const tabs = form.querySelectorAll('.type-tab');
        if (!tabs.length) return;

        // Snapshot the full server-rendered lists once, before swapping subsets in and out.
        const allCategories = Seller.options.read(categorySelect);
        const allConditions = Seller.options.read(conditionSelect);

        function applyTab(type) {
            tabs.forEach((tab) => {
                const isActive = tab.dataset.type === type;
                tab.classList.toggle('active', isActive);
                tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
            });

            if (type === 'service') {
                const services = allCategories.filter((item) => item.value && item.slug === 'services');
                Seller.options.render(
                    categorySelect,
                    services,
                    services.length ? null : 'No "Services" category set up yet'
                );
                categorySelect.disabled = services.length === 0;
            } else {
                const products = allCategories.filter((item) => item.value && item.slug !== 'services');
                Seller.options.render(categorySelect, products, 'Choose a category');
                categorySelect.disabled = false;
            }

            Seller.options.render(conditionSelect, allConditions.filter((item) => item.type === type));

            // Lets stock-editor.js update the stock field for the new category.
            categorySelect.dispatchEvent(new Event('change'));
        }

        tabs.forEach((tab) => tab.addEventListener('click', () => applyTab(tab.dataset.type)));

        // Reset to "product" whenever the modal is reopened.
        const modal = form.closest('.modal-overlay');
        if (modal) {
            new MutationObserver(() => {
                if (!modal.hidden) applyTab('product');
            }).observe(modal, { attributes: true, attributeFilter: ['hidden'] });
        }

        applyTab('product');
    }

    setupTabs('add-listing-form', 'listing-category', 'listing-condition');
})(window.Seller = window.Seller || {});

/* ===== add-listing-photos ===== */
/* Add listing modal: photo picker, drag & drop, main-photo preview, 8-photo limit. */
(function (Seller) {
    const LIMIT = 8;

    const input = document.getElementById('listing-image');
    const preview = document.getElementById('listing-photo-preview');
    const mainImage = document.getElementById('listing-main-image');
    const gallery = document.getElementById('listing-gallery');
    const uploadBox = document.getElementById('listing-upload-box');
    const hint = document.getElementById('listing-photo-hint');
    const addOverlay = document.querySelector('.photo-add-overlay');
    if (!input || !preview || !mainImage || !gallery || !uploadBox) return;

    let objectUrls = [];

    const queue = Seller.fileQueue(input, { limit: LIMIT, onChange: render });

    function render(files) {
        objectUrls.forEach((url) => URL.revokeObjectURL(url));
        objectUrls = files.map((file) => URL.createObjectURL(file));

        gallery.replaceChildren(...files.map((file, index) => Seller.gallery.tile({
            url: objectUrls[index],
            alt: `Selected listing photo ${index + 1}`,
            label: index === 0 ? 'Main photo' : `Photo ${index + 1}`,
            active: index === 0,
            onSelect: (img, url) => {
                mainImage.src = url;
                Seller.gallery.activate(gallery, img);
            },
            onRemove: () => queue.remove(file),
        }).item));

        const hasFiles = files.length > 0;
        preview.hidden = !hasFiles;
        uploadBox.hidden = hasFiles;
        if (hasFiles) mainImage.src = objectUrls[0];

        if (hint) {
            const remaining = LIMIT - files.length;
            hint.textContent = remaining <= 0
                ? 'Photo limit reached. Remove a photo to add another.'
                : `${remaining} photo${remaining === 1 ? '' : 's'} remaining. The first photo is your listing thumbnail.`;
        }
    }

    input.addEventListener('change', () => queue.add(input.files));

    [uploadBox, addOverlay].filter(Boolean).forEach((target) => {
        ['dragenter', 'dragover'].forEach((name) => target.addEventListener(name, (event) => {
            event.preventDefault();
            target.classList.add('drag-over');
        }));
        ['dragleave', 'drop'].forEach((name) => target.addEventListener(name, (event) => {
            event.preventDefault();
            target.classList.remove('drag-over');
        }));
        target.addEventListener('drop', (event) => {
            queue.add(Array.from(event.dataTransfer.files).filter((file) => file.type.startsWith('image/')));
        });
    });
})(window.Seller);

/* ===== manage-listing ===== */
/* Manage item modal: fills the form from a listing card's data-* attributes,
   handles saved/new photo thumbnails, and status colouring. */
(function (Seller) {
    const $ = (selector) => document.querySelector(selector);

    const modal = $('#manage-item-modal');
    const form = $('#manage-listing-form');
    if (!modal || !form) return;

    const el = {
        badge: $('#manage-status-badge'),
        image: $('#manage-image'),
        gallery: $('#manage-gallery'),
        removed: $('#manage-removed-images'),
        views: $('#manage-views'),
        name: $('#manage-name'),
        category: $('#manage-category'),
        price: $('#manage-price'),
        condition: $('#manage-condition'),
        location: $('#manage-location'),
        description: $('#manage-description'),
        status: $('#manage-status'),
        stock: $('#manage-stock-editor'),
        photos: $('#manage-item-image'),
    };

    // Condition options come from the server (data-type = product | service).
    const allConditions = Seller.options.read(el.condition);
    const split = (value) => (value ? value.split('||') : []);

    const queue = Seller.fileQueue(el.photos, { onChange: renderPending });

    function refreshStatus() {
        const status = el.status.value.toLowerCase();
        el.status.className = `status-select status-select-${status}`;
        el.badge.className = `status-pill status-pill-${status}`;
        el.badge.textContent = el.status.options[el.status.selectedIndex].text;
    }

    function selectPhoto(img, url) {
        el.image.src = url;
        Seller.gallery.activate(el.gallery, img);
    }

    function renderSaved(urls, ids) {
        el.gallery.replaceChildren(...urls.filter(Boolean).map((url, index) => {
            const imageId = /^\d+$/.test(ids[index] || '') ? ids[index] : '';
            return Seller.gallery.tile({
                url,
                alt: `Uploaded listing photo ${index + 1}`,
                active: index === 0,
                onSelect: selectPhoto,
                onRemove: () => {
                    const marker = document.createElement('input');
                    marker.type = 'hidden';
                    marker.name = imageId ? 'remove_image_ids' : 'remove_image_urls';
                    marker.value = imageId || url;
                    el.removed.appendChild(marker);
                },
            }).item;
        }));
    }

    function renderPending(files) {
        el.gallery.querySelectorAll('.pending-gallery-item').forEach((item) => item.remove());
        const urls = files.map((file) => URL.createObjectURL(file));
        files.forEach((file, index) => {
            el.gallery.appendChild(Seller.gallery.tile({
                url: urls[index],
                alt: `New listing photo ${index + 1}`,
                pending: true,
                onSelect: selectPhoto,
                onRemove: () => queue.remove(file),
            }).item);
        });
        if (urls.length) el.image.src = urls[0];
    }

    function open(card) {
        const data = card.dataset;
        const isService = data.categorySlug === 'services';

        queue.clear();
        form.action = data.editUrl;
        form.dataset.deleteUrl = data.deleteUrl;
        el.removed.replaceChildren();

        el.image.src = data.image;
        el.image.alt = data.name;
        renderSaved(split(data.gallery), split(data.galleryIds));
        el.views.textContent = data.views;

        el.name.value = data.name;
        el.category.value = data.categoryId;
        el.price.value = data.price;
        el.location.value = data.location;
        el.description.value = data.description;
        el.status.value = data.statusValue;
        el.stock.querySelector('input[type="number"]').value = data.stock || '0';

        Seller.options.render(el.condition, allConditions.filter((item) => item.type === (isService ? 'service' : 'product')));
        el.condition.value = data.condition;

        Seller.stockEditor.sync(el.stock, { fresh: true });
        refreshStatus();
        Seller.modal.open(modal);
    }

    $('#seller-list').addEventListener('click', (event) => {
        if (!event.target.closest('.manage-button')) return;
        open(event.target.closest('.seller-listing'));
    });

    el.status.addEventListener('change', refreshStatus);
    el.photos.addEventListener('change', () => queue.add(el.photos.files));

    // Deep link: ?manage=<id> opens that listing straight away.
    const initialId = $('[data-initial-manage-id]')?.dataset.initialManageId;
    if (initialId) {
        const card = $(`.seller-listing[data-edit-url*="/${initialId}/"]`);
        if (card) open(card);
    }
})(window.Seller);

/* ===== delete-listing ===== */
/* Manage modal -> "Delete listing" opens the confirm modal.
   The delete URL is stored on the manage form by manage-listing.js. */
(function (Seller) {
    const trigger = document.getElementById('delete-listing');
    const manageForm = document.getElementById('manage-listing-form');
    const confirmModal = document.getElementById('delete-confirm-modal');
    const deleteForm = document.getElementById('delete-listing-form');
    if (!trigger || !manageForm || !confirmModal || !deleteForm) return;

    trigger.addEventListener('click', () => {
        deleteForm.action = manageForm.dataset.deleteUrl;
        Seller.modal.open(confirmModal);
    });
})(window.Seller);

/* ===== listing-filters ===== */
/* Seller dashboard: search + status filter over the rendered listing cards. */
(function () {
    const search = document.getElementById('listing-search');
    const status = document.getElementById('listing-status-filter');
    const form = document.getElementById('listing-filters');
    const noResults = document.getElementById('no-filter-results');
    const cards = document.querySelectorAll('.seller-listing');
    if (!search || !status) return;

    function apply() {
        const statusValue = status.value;
        const query = search.value.trim().toLowerCase();
        let visible = 0;

        cards.forEach((card) => {
            const show = (statusValue === 'all' || card.dataset.status === statusValue)
                && (!query || card.dataset.search.includes(query));
            card.hidden = !show;
            if (show) visible += 1;
        });

        // With no listings at all, the "not published yet" message already covers it.
        if (noResults) noResults.hidden = visible > 0 || cards.length === 0;
    }

    search.addEventListener('input', apply);
    status.addEventListener('change', apply);
    if (form) form.addEventListener('submit', (event) => event.preventDefault());
})();
