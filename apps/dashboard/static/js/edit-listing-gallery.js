document.addEventListener('DOMContentLoaded', () => {
    const gallery = document.querySelector('.edit-gallery');
    const removedImages = document.querySelector('#edit-removed-images');
    const imageInput = document.querySelector('#edit-listing-images');
    let selectedFiles = [];
    if (!gallery || !removedImages || !imageInput) return;

    const setFiles = (files) => {
        const dataTransfer = new DataTransfer();
        files.forEach((file) => dataTransfer.items.add(file));
        imageInput.files = dataTransfer.files;
    };

    gallery.addEventListener('click', (event) => {
        const button = event.target.closest('.remove-gallery-image');
        if (!button) return;
        if (!button.dataset.imageId) {
            button.closest('.manage-gallery-item').remove();
            return;
        }
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'remove_image_ids';
        input.value = button.dataset.imageId;
        removedImages.appendChild(input);
        button.closest('.manage-gallery-item').remove();
    });

    imageInput.addEventListener('change', () => {
        selectedFiles = [...selectedFiles, ...imageInput.files];
        setFiles(selectedFiles);
        gallery.querySelectorAll('.pending-gallery-item').forEach((item) => item.remove());
        selectedFiles.forEach((file, index) => {
            const item = document.createElement('div');
            item.className = 'manage-gallery-item pending-gallery-item';
            item.innerHTML = `<img src="${URL.createObjectURL(file)}" alt="New listing photo ${index + 1}"><button type="button" class="remove-gallery-image" aria-label="Remove selected photo">&times;</button>`;
            item.querySelector('.remove-gallery-image').addEventListener('click', () => {
                selectedFiles = selectedFiles.filter((selectedFile) => selectedFile !== file);
                setFiles(selectedFiles);
                item.remove();
            });
            gallery.appendChild(item);
        });
    });
});