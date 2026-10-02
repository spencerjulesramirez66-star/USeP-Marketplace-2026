/* Edit listing page: remove saved photos, add and preview new ones. */
(function (Seller) {
    const gallery = document.querySelector('.edit-gallery');
    const removedInputs = document.getElementById('edit-removed-images');
    const input = document.getElementById('edit-listing-images');
    if (!gallery || !removedInputs || !input) return;

    const queue = Seller.fileQueue(input, { onChange: renderPending });

    // Saved photos are rendered by the server; flag them for removal on save.
    gallery.addEventListener('click', (event) => {
        const button = event.target.closest('.remove-gallery-image[data-image-id]');
        if (!button) return;
        const marker = document.createElement('input');
        marker.type = 'hidden';
        marker.name = 'remove_image_ids';
        marker.value = button.dataset.imageId;
        removedInputs.appendChild(marker);
        button.closest('.manage-gallery-item').remove();
    });

    function renderPending(files) {
        gallery.querySelectorAll('.pending-gallery-item').forEach((item) => item.remove());
        files.forEach((file, index) => {
            gallery.appendChild(Seller.gallery.tile({
                url: URL.createObjectURL(file),
                alt: `New listing photo ${index + 1}`,
                pending: true,
                onRemove: () => queue.remove(file),
            }).item);
        });
    }

    input.addEventListener('change', () => queue.add(input.files));
})(window.Seller);
