document.addEventListener('DOMContentLoaded', () => {
    const modal = document.querySelector('#detail-edit-modal');
    const openButton = document.querySelector('#open-detail-edit');
    const closeButtons = document.querySelectorAll('#close-detail-edit, #cancel-detail-edit');
    const gallery = document.querySelector('#detail-edit-gallery');
    const mainImage = document.querySelector('#detail-edit-main-image');
    const removedImages = document.querySelector('#detail-removed-images');
    const imageInput = document.querySelector('#detail-edit-images');
    let selectedFiles = [];
    const setFiles = (files) => {
        const dataTransfer = new DataTransfer();
        files.forEach((file) => dataTransfer.items.add(file));
        imageInput.files = dataTransfer.files;
    };
    if (!modal || !openButton) return;

    const close = () => {
        modal.hidden = true;
    };

    openButton.addEventListener('click', () => {
        selectedFiles = [];
        if (imageInput) imageInput.value = '';
        modal.hidden = false;
    });

    closeButtons.forEach((button) => button.addEventListener('click', close));
    const showImage = (url, image) => {
        if (!mainImage || !gallery) return;
        mainImage.src = url;
        gallery.querySelectorAll('img').forEach((entry) => entry.classList.remove('active'));
        image.classList.add('active');
    };
    if (gallery && mainImage) {
        gallery.querySelectorAll('.manage-gallery-item img').forEach((image) => {
            image.addEventListener('click', () => showImage(image.src, image));
        });
    }
    if (gallery && removedImages) {
        gallery.addEventListener('click', (event) => {
            const button = event.target.closest('.remove-gallery-image');
            if (!button) return;
            const item = button.closest('.manage-gallery-item');
            const image = item ? item.querySelector('img') : null;
            const wasMainImage = mainImage && image && mainImage.src === image.src;
            const imageId = button.dataset.imageId;
            if (!imageId || !/^\d+$/.test(imageId)) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'remove_image_urls';
                input.value = button.dataset.imageUrl;
                removedImages.appendChild(input);
                item.remove();
                if (wasMainImage) {
                    const replacement = gallery.querySelector('.manage-gallery-item img');
                    if (replacement) showImage(replacement.src, replacement);
                }
                return;
            }
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'remove_image_ids';
            input.value = imageId;
            removedImages.appendChild(input);
            item.remove();
            if (wasMainImage) {
                const replacement = gallery.querySelector('.manage-gallery-item img');
                if (replacement) showImage(replacement.src, replacement);
            }
        });
    }
    if (imageInput && gallery) {
        imageInput.addEventListener('change', () => {
            selectedFiles = [...selectedFiles, ...imageInput.files];
            setFiles(selectedFiles);
            gallery.querySelectorAll('.pending-gallery-item').forEach((item) => item.remove());
            selectedFiles.forEach((file, index) => {
                const item = document.createElement('div');
                item.className = 'manage-gallery-item pending-gallery-item';
                const image = document.createElement('img');
                image.alt = `New product photo ${index + 1}`;
                image.src = URL.createObjectURL(file);
                image.className = 'manage-gallery-image';
                image.addEventListener('click', () => showImage(image.src, image));
                const removeButton = document.createElement('button');
                removeButton.type = 'button';
                removeButton.className = 'remove-gallery-image';
                removeButton.setAttribute('aria-label', 'Remove selected photo');
                removeButton.title = 'Remove selected photo';
                removeButton.innerHTML = '<i class="bi bi-trash3" aria-hidden="true"></i>';
                removeButton.addEventListener('click', () => {
                    selectedFiles = selectedFiles.filter((selectedFile) => selectedFile !== file);
                    setFiles(selectedFiles);
                    item.remove();
                    const replacement = gallery.querySelector('.manage-gallery-item img');
                    if (replacement) showImage(replacement.src, replacement);
                });
                item.append(image, removeButton);
                gallery.appendChild(item);
                if (index === 0) showImage(image.src, image);
            });
        });
    }
    modal.addEventListener('click', (event) => {
        if (event.target === modal) close();
    });
});
