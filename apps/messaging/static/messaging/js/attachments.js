import { qs, on, formatBytes } from './dom.js';

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
        previewEl.innerHTML = selected.map((item, index) => {
            const isImage = Boolean(item.previewUrl);
            return `
            <div class="messaging-attachment-preview-item${isImage ? ' messaging-attachment-preview-item--image' : ''}" data-index="${index}">
                ${item.previewUrl
                    ? `<img class="messaging-pending-attachment-thumbnail" src="${item.previewUrl}" alt="Selected attachment preview" width="80" height="80">`
                    : `<span class="messaging-attachment-preview-file"><i class="bi bi-file-earmark"></i>${item.file.name}</span>`}
                <button type="button" data-remove-attachment aria-label="${isImage ? 'Remove attached image' : 'Remove attachment'}"><i class="bi bi-x" aria-hidden="true"></i></button>
            </div>
        `;
        }).join('');
    }

    function addFiles(fileList) {
        clearWarning();
        for (const file of Array.from(fileList)) {
            if (file.size > maxSizeBytes) {
                showWarning(`${file.name} is larger than ${formatBytes(maxSizeBytes)} and was not added.`);
                continue;
            }
            const previewUrl = file.type.startsWith('image/') ? URL.createObjectURL(file) : null;
            selected.push({ file, previewUrl });
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
