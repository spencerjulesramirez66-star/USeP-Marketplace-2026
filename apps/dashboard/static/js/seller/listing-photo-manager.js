/* Add-listing photo picker, preview grid, drag-and-drop, and 8-photo limit.
   Loaded after seller-core.js, which provides Seller.fileQueue and Seller.gallery. */
(function (Seller) {
    const LIMIT = 8;
    const input = document.getElementById('listing-image');
    const preview = document.getElementById('listing-photo-preview');
    const gallery = document.getElementById('listing-gallery');
    const uploadBox = document.getElementById('listing-upload-box');
    const hint = document.getElementById('listing-photo-hint');
    if (!input || !preview || !gallery || !uploadBox) return;

    let objectUrls = [];
    const queue = Seller.fileQueue(input, { limit: LIMIT, onChange: render });

    function render(files) {
        objectUrls.forEach((url) => URL.revokeObjectURL(url));
        objectUrls = files.map((file) => URL.createObjectURL(file));
        gallery.replaceChildren(...files.map((file, index) => Seller.gallery.tile({
            url: objectUrls[index],
            alt: `Selected listing photo ${index + 1}`,
            label: index === 0 ? 'Listing thumbnail' : `Photo ${index + 1}`,
            active: index === 0,
            onRemove: () => queue.remove(file),
        }).item));

        const hasFiles = files.length > 0;
        preview.hidden = !hasFiles;
        uploadBox.hidden = hasFiles;
        if (hint) {
            const remaining = LIMIT - files.length;
            hint.textContent = remaining <= 0
                ? 'Photo limit reached. Remove a photo to add another.'
                : `${files.length} of ${LIMIT} selected. The first photo is your listing thumbnail.`;
        }
    }

    input.addEventListener('change', () => queue.add(input.files));
    [uploadBox].forEach((target) => {
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
