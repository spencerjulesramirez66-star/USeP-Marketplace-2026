/**
 * Owner-only "Edit listing" modal on the buyer detail page.
 * Handles: open/close, gallery preview, removing existing photos,
 * adding new photos. (Stock +/- is in shared/stock-stepper.js,
 * stock visibility is in shared/stock-toggle.js.)
 */
(function () {
    'use strict';

    function init() {
        const modal = document.querySelector('#detail-edit-modal');
        const openButton = document.querySelector('#open-detail-edit');
        if (!modal || !openButton) return;

        const closeButtons = document.querySelectorAll('#close-detail-edit, #cancel-detail-edit');
        const gallery = document.querySelector('#detail-edit-gallery');
        const mainImage = document.querySelector('#detail-edit-main-image');
        const removedImages = document.querySelector('#detail-removed-images');
        const imageInput = document.querySelector('#detail-edit-images');

        let selectedFiles = [];

        // ---- helpers --------------------------------------------------
        const close = () => { modal.hidden = true; };

        const syncInputFiles = () => {
            if (!imageInput) return;
            const dt = new DataTransfer();
            selectedFiles.forEach((file) => dt.items.add(file));
            imageInput.files = dt.files;
        };

        const showImage = (image) => {
            if (!mainImage || !gallery) return;
            mainImage.src = image.src;
            gallery.querySelectorAll('img').forEach((img) => img.classList.remove('active'));
            image.classList.add('active');
        };

        const showFirstImage = () => {
            const first = gallery && gallery.querySelector('.manage-gallery-item img');
            if (first) showImage(first);
        };

        const markForRemoval = (name, value) => {
            const hidden = document.createElement('input');
            hidden.type = 'hidden';
            hidden.name = name;
            hidden.value = value;
            removedImages.appendChild(hidden);
        };

        const clearPending = () => {
            if (!gallery) return;
            gallery.querySelectorAll('.pending-gallery-item').forEach((item) => {
                const img = item.querySelector('img');
                if (img) URL.revokeObjectURL(img.src);
                item.remove();
            });
        };

        // ---- open / close ---------------------------------------------
        openButton.addEventListener('click', () => {
            selectedFiles = [];
            if (imageInput) imageInput.value = '';
            clearPending();
            modal.hidden = false;
        });

        closeButtons.forEach((button) => button.addEventListener('click', close));
        modal.addEventListener('click', (event) => {
            if (event.target === modal) close();
        });

        if (!gallery) return;

        // ---- gallery: click to preview ---------------------------------
        if (mainImage) {
            gallery.addEventListener('click', (event) => {
                const image = event.target.closest('.manage-gallery-item img');
                if (image) showImage(image);
            });
        }

        // ---- gallery: remove an EXISTING photo -------------------------
        if (removedImages) {
            gallery.addEventListener('click', (event) => {
                const button = event.target.closest('.remove-gallery-image');
                if (!button) return;

                const item = button.closest('.manage-gallery-item');
                // Newly-added photos have their own remove handler (see below).
                // Skipping them here fixes a bug where removing one also wrote a
                // hidden input with value "undefined" into the form.
                if (!item || item.classList.contains('pending-gallery-item')) return;

                const image = item.querySelector('img');
                const wasMain = mainImage && image && mainImage.src === image.src;
                const id = button.dataset.imageId;

                if (id && /^\d+$/.test(id)) markForRemoval('remove_image_ids', id);
                else markForRemoval('remove_image_urls', button.dataset.imageUrl || '');

                item.remove();
                if (wasMain) showFirstImage();
            });
        }

        // ---- gallery: add NEW photos ----------------------------------
        if (imageInput) {
            const buildPendingItem = (file, index) => {
                const item = document.createElement('div');
                item.className = 'manage-gallery-item pending-gallery-item';

                const image = document.createElement('img');
                image.alt = `New product photo ${index + 1}`;
                image.src = URL.createObjectURL(file);
                image.className = 'manage-gallery-image';

                const remove = document.createElement('button');
                remove.type = 'button';
                remove.className = 'remove-gallery-image';
                remove.setAttribute('aria-label', 'Remove selected photo');
                remove.title = 'Remove selected photo';
                remove.innerHTML = '<i class="bi bi-trash3" aria-hidden="true"></i>';
                remove.addEventListener('click', () => {
                    selectedFiles = selectedFiles.filter((f) => f !== file);
                    syncInputFiles();
                    URL.revokeObjectURL(image.src);
                    item.remove();
                    showFirstImage();
                });

                item.append(image, remove);
                return item;
            };

            imageInput.addEventListener('change', () => {
                selectedFiles = [...selectedFiles, ...imageInput.files];
                syncInputFiles();
                clearPending();
                selectedFiles.forEach((file, index) => {
                    const item = buildPendingItem(file, index);
                    gallery.appendChild(item);
                    if (index === 0) showImage(item.querySelector('img'));
                });
            });
        }
    }

    document.addEventListener('DOMContentLoaded', init);
})();
