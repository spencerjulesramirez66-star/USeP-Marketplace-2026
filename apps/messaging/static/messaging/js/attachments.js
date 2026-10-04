import { qs, on, formatBytes } from './dom.js';

// File selection, preview, and (for images) client-side downscaling before
// upload. This is a UX convenience only: the server independently validates
// type and size, since a client can always skip this code entirely.

const MAX_IMAGE_DIMENSION = 1600;
const IMAGE_QUALITY = 0.82;

function isImageFile(file) {
    return file.type.startsWith('image/') && file.type !== 'image/gif'; // GIFs keep their animation
}

/** Downscales a large image in the browser so uploads are smaller and faster. */
function compressImage(file) {
    return new Promise((resolve) => {
        const img = new Image();
        const url = URL.createObjectURL(file);
        img.onload = () => {
            const scale = Math.min(1, MAX_IMAGE_DIMENSION / Math.max(img.width, img.height));
            if (scale === 1) { URL.revokeObjectURL(url); resolve(file); return; }
            const canvas = document.createElement('canvas');
            canvas.width = img.width * scale;
            canvas.height = img.height * scale;
            canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
            canvas.toBlob((blob) => {
                URL.revokeObjectURL(url);
                resolve(blob ? new File([blob], file.name, { type: 'image/jpeg' }) : file);
            }, 'image/jpeg', IMAGE_QUALITY);
        };
        img.onerror = () => { URL.revokeObjectURL(url); resolve(file); };
        img.src = url;
    });
}

export function initAttachments({ form, fileInput, mediaInput, toggleButton, menu, previewEl, warningEl, maxSizeBytes }) {
    let selected = []; // { file, previewUrl }

    function showWarning(message) {
        warningEl.hidden = false;
        warningEl.textContent = message;
    }

    function clearWarning() {
        warningEl.hidden = true;
        warningEl.textContent = '';
    }

    function render() {
        previewEl.hidden = selected.length === 0;
        previewEl.innerHTML = selected.map((item, index) => `
            <div class="messaging-attachment-preview-item" data-index="${index}">
                ${item.previewUrl
                    ? `<img src="${item.previewUrl}" alt="">`
                    : `<span class="messaging-attachment-preview-file"><i class="bi bi-file-earmark"></i>${item.file.name}</span>`}
                <button type="button" data-remove-attachment aria-label="Remove attachment"><i class="bi bi-x"></i></button>
            </div>
        `).join('');
    }

    async function addFiles(fileList) {
        clearWarning();
        for (const file of Array.from(fileList)) {
            if (file.size > maxSizeBytes) {
                showWarning(`${file.name} is larger than ${formatBytes(maxSizeBytes)} and was not added.`);
                continue;
            }
            const finalFile = isImageFile(file) ? await compressImage(file) : file;
            const previewUrl = finalFile.type.startsWith('image/') ? URL.createObjectURL(finalFile) : null;
            selected.push({ file: finalFile, previewUrl });
        }
        render();
    }

    function removeAt(index) {
        const [removed] = selected.splice(index, 1);
        if (removed && removed.previewUrl) URL.revokeObjectURL(removed.previewUrl);
        render();
    }

    fileInput.addEventListener('change', () => { addFiles(fileInput.files); fileInput.value = ''; });
    mediaInput.addEventListener('change', () => { addFiles(mediaInput.files); mediaInput.value = ''; });

    on(previewEl, 'click', '[data-remove-attachment]', (evt, target) => {
        removeAt(Number(target.closest('[data-index]').dataset.index));
    });

    toggleButton.addEventListener('click', () => {
        const isOpen = !menu.hidden;
        menu.hidden = isOpen;
        toggleButton.setAttribute('aria-expanded', String(!isOpen));
    });
    on(menu, 'click', '[data-attachment-picker]', (evt, target) => {
        menu.hidden = true;
        toggleButton.setAttribute('aria-expanded', 'false');
        (target.dataset.attachmentPicker === 'media' ? mediaInput : fileInput).click();
    });
    document.addEventListener('click', (evt) => {
        if (!menu.hidden && !menu.contains(evt.target) && !toggleButton.contains(evt.target)) {
            menu.hidden = true;
            toggleButton.setAttribute('aria-expanded', 'false');
        }
    });

    function getFiles() {
        return selected.map((item) => item.file);
    }

    function reset() {
        selected.forEach((item) => item.previewUrl && URL.revokeObjectURL(item.previewUrl));
        selected = [];
        render();
        clearWarning();
    }

    function hasFiles() {
        return selected.length > 0;
    }

    return { getFiles, reset, hasFiles };
}
