const form = document.querySelector('.listing-review-form');
const input = document.querySelector('#id_photos');
const preview = document.querySelector('#listing-review-photo-preview');
const warning = document.querySelector('[data-review-photo-warning]');
const limitNote = document.querySelector('[data-review-photo-limit]');

if (form && input && preview && warning) {
    const maxPhotos = Number(input.dataset.maxPhotos) || 5;
    const maxSize = Number(input.dataset.maxSize) || 10 * 1024 * 1024;
    const existingCount = Number(form.dataset.existingPhotoCount) || 0;
    const removedExisting = new Set();
    let selected = [];

    function availableSlots() {
        return Math.max(0, maxPhotos - existingCount + removedExisting.size - selected.length);
    }

    function updateLimitNote() {
        const remaining = availableSlots();
        limitNote.textContent = remaining
            ? `Add up to ${remaining} more photo${remaining === 1 ? '' : 's'} (10 MB each).`
            : 'Photo limit reached. Remove an existing or selected photo to add a replacement.';
    }

    function syncInput() {
        const transfer = new DataTransfer();
        selected.forEach(({ file }) => transfer.items.add(file));
        input.files = transfer.files;
    }

    function render() {
        selected.forEach(({ previewUrl }) => URL.revokeObjectURL(previewUrl));
        preview.replaceChildren();
        preview.hidden = selected.length === 0;

        selected = selected.map(({ file }) => ({ file, previewUrl: URL.createObjectURL(file) }));
        selected.forEach(({ file, previewUrl }, index) => {
            const item = document.createElement('div');
            item.className = 'listing-review-photo-preview-item';
            item.dataset.index = index;

            const image = document.createElement('img');
            image.src = previewUrl;
            image.alt = file.name;

            const remove = document.createElement('button');
            remove.type = 'button';
            remove.setAttribute('aria-label', `Remove ${file.name}`);
            const icon = document.createElement('i');
            icon.className = 'bi bi-x-lg';
            icon.setAttribute('aria-hidden', 'true');
            remove.append(icon);

            item.append(image, remove);
            preview.append(item);
        });
        updateLimitNote();
    }

    input.addEventListener('change', () => {
        const incoming = Array.from(input.files || []);
        let warningText = '';

        incoming.forEach((file) => {
            if (!file.type.startsWith('image/')) {
                warningText = 'Choose image files only.';
            } else if (file.size > maxSize) {
                warningText = `${file.name} is larger than 10 MB.`;
            } else if (!selected.some((item) => item.file.name === file.name && item.file.size === file.size)) {
                if (availableSlots() <= 0) {
                    warningText = 'Remove a current or selected photo before adding another.';
                } else {
                    selected.push({ file, previewUrl: '' });
                }
            }
        });

        warning.hidden = !warningText;
        warning.textContent = warningText;
        syncInput();
        render();
    });

    preview.addEventListener('click', (event) => {
        const button = event.target.closest('button');
        if (!button) return;
        const item = button.closest('[data-index]');
        selected.splice(Number(item.dataset.index), 1);
        syncInput();
        render();
    });

    form.addEventListener('click', (event) => {
        const button = event.target.closest('[data-remove-review-photo]');
        if (!button) return;
        const photo = button.closest('[data-existing-review-photo]');
        const photoId = photo?.dataset.photoId;
        if (!photo || !photoId || removedExisting.has(photoId)) return;

        removedExisting.add(photoId);
        photo.hidden = true;

        const removedPhotoInput = document.createElement('input');
        removedPhotoInput.type = 'hidden';
        removedPhotoInput.name = 'remove_photo_ids';
        removedPhotoInput.value = photoId;
        form.append(removedPhotoInput);
        updateLimitNote();
    });

    updateLimitNote();
}