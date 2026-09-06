const PRODUCT_CONDITIONS = ['Like new', 'Barely used', 'Good condition', 'For parts'];
const SERVICE_CONDITIONS = ['Available by appointment', 'On-site service', 'Currently unavailable'];

document.querySelectorAll('input[name="price"]').forEach((input) => {
    input.addEventListener('input', () => {
        const cleaned = input.value.replace(/[^0-9.]/g, '');
        const [whole, ...decimalParts] = cleaned.split('.');
        input.value = decimalParts.length ? `${whole}.${decimalParts.join('').slice(0, 2)}` : whole;
    });
});

function openModal(modal) {
    if (modal) modal.hidden = false;
}

function closeModal(modal) {
    if (modal) modal.hidden = true;
}

document.querySelectorAll('[data-close-modal]').forEach((button) => {
    button.addEventListener('click', () => closeModal(document.querySelector(`#${button.dataset.closeModal}`)));
});

const addListingModal = document.querySelector('#add-listing-modal');
const openAddListing = document.querySelector('#open-add-listing');
if (openAddListing) openAddListing.addEventListener('click', () => openModal(addListingModal));

const listingCategory = document.querySelector('#listing-category');
const listingCondition = document.querySelector('#listing-condition');
if (listingCategory && listingCondition) {
    listingCategory.addEventListener('change', () => {
        const conditions = listingCategory.options[listingCategory.selectedIndex].text === 'Services' ? SERVICE_CONDITIONS : PRODUCT_CONDITIONS;
        listingCondition.replaceChildren(...conditions.map((condition) => new Option(condition, condition)));
    });
}

const listingImageInput = document.querySelector('#listing-image');
const listingPhotoPreview = document.querySelector('#listing-photo-preview');
const listingMainImage = document.querySelector('#listing-main-image');
const listingGallery = document.querySelector('#listing-gallery');
const listingUploadBox = document.querySelector('#listing-upload-box');
const listingAddOverlay = document.querySelector('.photo-add-overlay');
const listingPhotoHint = document.querySelector('#listing-photo-hint');
const LISTING_IMAGE_LIMIT = 8;
let listingSelectedFiles = [];
function setFiles(input, files) {
    const dataTransfer = new DataTransfer();
    files.forEach((file) => dataTransfer.items.add(file));
    input.files = dataTransfer.files;
}
function renderListingPhotoPreview() {
    if (!listingImageInput || !listingPhotoPreview || !listingMainImage || !listingGallery || !listingUploadBox) return;
    const files = listingSelectedFiles;
    listingGallery.replaceChildren(...files.map((file, index) => {
        const item = document.createElement('div');
        item.className = 'manage-gallery-item';
        item.innerHTML = `<img alt="Selected listing photo ${index + 1}"><span class="photo-tile-label">${index === 0 ? 'Main photo' : `Photo ${index + 1}`}</span><button type="button" class="remove-gallery-image" aria-label="Remove selected photo" title="Remove selected photo"><i class="bi bi-trash3" aria-hidden="true"></i></button>`;
        const image = item.querySelector('img');
        const url = URL.createObjectURL(file);
        image.src = url;
        image.className = index === 0 ? 'manage-gallery-image active' : 'manage-gallery-image';
        image.addEventListener('click', () => {
            listingMainImage.src = url;
            listingGallery.querySelectorAll('img').forEach((entry) => entry.classList.remove('active'));
            image.classList.add('active');
        });
        item.querySelector('.remove-gallery-image').addEventListener('click', () => {
            listingSelectedFiles = files.filter((selectedFile) => selectedFile !== file);
            setFiles(listingImageInput, listingSelectedFiles);
            renderListingPhotoPreview();
        });
        return item;
    }));
    const hasFiles = files.length > 0;
    listingPhotoPreview.hidden = !hasFiles;
    listingUploadBox.hidden = hasFiles;
    if (listingPhotoHint) listingPhotoHint.textContent = files.length >= LISTING_IMAGE_LIMIT
        ? 'Photo limit reached. Remove a photo to add another.'
        : `${LISTING_IMAGE_LIMIT - files.length} photo${LISTING_IMAGE_LIMIT - files.length === 1 ? '' : 's'} remaining. The first photo is your listing thumbnail.`;
    if (hasFiles) listingMainImage.src = URL.createObjectURL(files[0]);
}

if (listingImageInput && listingPhotoPreview && listingGallery && listingUploadBox) {
    listingImageInput.addEventListener('change', () => {
        const availableFiles = [...listingImageInput.files].slice(0, LISTING_IMAGE_LIMIT - listingSelectedFiles.length);
        listingSelectedFiles = [...listingSelectedFiles, ...availableFiles];
        setFiles(listingImageInput, listingSelectedFiles);
        renderListingPhotoPreview();
    });
    [listingUploadBox, listingAddOverlay].filter(Boolean).forEach((dropTarget) => {
        ['dragenter', 'dragover'].forEach((eventName) => dropTarget.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropTarget.classList.add('drag-over');
        }));
        ['dragleave', 'drop'].forEach((eventName) => dropTarget.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropTarget.classList.remove('drag-over');
        }));
        dropTarget.addEventListener('drop', (event) => {
            const availableFiles = [...event.dataTransfer.files].filter((file) => file.type.startsWith('image/')).slice(0, LISTING_IMAGE_LIMIT - listingSelectedFiles.length);
            listingSelectedFiles = [...listingSelectedFiles, ...availableFiles];
            setFiles(listingImageInput, listingSelectedFiles);
            renderListingPhotoPreview();
        });
    });
}

const manageModal = document.querySelector('#manage-item-modal');
const manageForm = document.querySelector('#manage-listing-form');
const manageStatusBadge = document.querySelector('#manage-status-badge');
const manageImage = document.querySelector('#manage-image');
const manageGallery = document.querySelector('#manage-gallery');
const manageRemovedImages = document.querySelector('#manage-removed-images');
const manageViews = document.querySelector('#manage-views');
const manageName = document.querySelector('#manage-name');
const manageCategory = document.querySelector('#manage-category');
const managePrice = document.querySelector('#manage-price');
const manageCondition = document.querySelector('#manage-condition');
const manageLocation = document.querySelector('#manage-location');
const manageDescription = document.querySelector('#manage-description');
const manageStatus = document.querySelector('#manage-status');
const manageImageInput = document.querySelector('#manage-item-image');
let manageSelectedFiles = [];
let activeListingCard = null;

function refreshStatusAppearance() {
    if (!manageStatus || !manageStatusBadge) return;
    const status = manageStatus.value.toLowerCase();
    const label = manageStatus.options[manageStatus.selectedIndex].text;
    manageStatus.className = `status-select status-select-${status}`;
    manageStatusBadge.className = `status-pill status-pill-${status}`;
    manageStatusBadge.textContent = label;
}

function renderManageGallery(urls, ids = []) {
    if (!manageGallery) return;
    manageGallery.replaceChildren(...urls.filter(Boolean).map((url, index) => {
        const item = document.createElement('div');
        item.className = 'manage-gallery-item';
        const imageId = ids[index] && /^\d+$/.test(ids[index]) ? ids[index] : '';
        item.innerHTML = `<img alt="Uploaded listing photo ${index + 1}"><button type="button" class="remove-gallery-image" data-image-id="${imageId}" data-image-url="${url}" aria-label="Remove photo" title="Remove photo"><i class="bi bi-trash3" aria-hidden="true"></i></button>`;
        const image = item.querySelector('img');
        image.src = url;
        image.className = index === 0 ? 'manage-gallery-image active' : 'manage-gallery-image';
        image.addEventListener('click', () => {
            manageImage.src = url;
            manageGallery.querySelectorAll('img').forEach((entry) => entry.classList.remove('active'));
            image.classList.add('active');
        });
        return item;
    }));
}

function addManagePreview(url, label, onRemove) {
    const item = document.createElement('div');
    item.className = 'manage-gallery-item pending-gallery-item';
    item.innerHTML = `<img alt="${label}"><button type="button" class="remove-gallery-image" aria-label="Remove selected photo" title="Remove selected photo"><i class="bi bi-trash3" aria-hidden="true"></i></button>`;
    const image = item.querySelector('img');
    image.src = url;
    image.addEventListener('click', () => {
        manageImage.src = url;
        manageGallery.querySelectorAll('img').forEach((entry) => entry.classList.remove('active'));
        image.classList.add('active');
    });
    item.querySelector('.remove-gallery-image').addEventListener('click', (event) => {
        event.stopPropagation();
        onRemove();
        item.remove();
    });
    manageGallery.appendChild(item);
}

if (manageGallery) {
    manageGallery.addEventListener('click', (event) => {
        const removeButton = event.target.closest('.remove-gallery-image');
        if (!removeButton || !manageRemovedImages) return;
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = removeButton.dataset.imageId ? 'remove_image_ids' : 'remove_image_urls';
        input.value = removeButton.dataset.imageId || removeButton.dataset.imageUrl;
        manageRemovedImages.appendChild(input);
        removeButton.closest('.manage-gallery-item').remove();
        event.preventDefault();
        event.stopPropagation();
    });
}

document.querySelectorAll('.manage-button').forEach((button) => {
    button.addEventListener('click', () => {
        const card = button.closest('.seller-listing');
        if (!card || !manageForm) return;
        manageSelectedFiles = [];
        if (manageImageInput) manageImageInput.value = '';
        activeListingCard = card;
        manageForm.action = card.dataset.editUrl;
        if (manageRemovedImages) manageRemovedImages.replaceChildren();
        manageImage.src = card.dataset.image;
        manageImage.alt = card.dataset.name;
        renderManageGallery(
            card.dataset.gallery ? card.dataset.gallery.split('||') : [],
            card.dataset.galleryIds ? card.dataset.galleryIds.split('||') : [],
        );
        manageViews.textContent = card.dataset.views;
        manageName.value = card.dataset.name;
        manageCategory.value = card.dataset.categoryId;
        managePrice.value = card.dataset.price;
        manageLocation.value = card.dataset.location;
        manageDescription.value = card.dataset.description;
        manageStatus.value = card.dataset.statusValue;
        const conditions = card.dataset.category === 'Services' ? SERVICE_CONDITIONS : PRODUCT_CONDITIONS;
        manageCondition.replaceChildren(...conditions.map((condition) => new Option(condition, condition)));
        manageCondition.value = card.dataset.condition;
        refreshStatusAppearance();
        openModal(manageModal);
    });
});

if (window.initialManageListingId) {
    const initialCard = document.querySelector(`.seller-listing[data-edit-url*="/${window.initialManageListingId}/"]`);
    const initialButton = initialCard ? initialCard.querySelector('.manage-button') : null;
    if (initialButton) initialButton.click();
}

if (manageStatus) manageStatus.addEventListener('change', refreshStatusAppearance);
if (manageImageInput && manageImage) {
    manageImageInput.addEventListener('change', () => {
        manageSelectedFiles = [...manageSelectedFiles, ...manageImageInput.files];
        setFiles(manageImageInput, manageSelectedFiles);
        const files = manageSelectedFiles;
        if (!files.length) return;
        const urls = files.map((file) => URL.createObjectURL(file));
        urls.forEach((url, index) => {
            addManagePreview(url, `New listing photo ${index + 1}`, () => {
                manageSelectedFiles = manageSelectedFiles.filter((selectedFile) => selectedFile !== files[index]);
                setFiles(manageImageInput, manageSelectedFiles);
            });
        });
        manageImage.src = urls[0];
    });
}

const deleteConfirmModal = document.querySelector('#delete-confirm-modal');
const deleteListingButton = document.querySelector('#delete-listing');
const deleteListingForm = document.querySelector('#delete-listing-form');
const cancelDeleteButton = document.querySelector('#cancel-delete');
if (deleteListingButton) {
    deleteListingButton.addEventListener('click', () => {
        if (activeListingCard && deleteListingForm) deleteListingForm.action = activeListingCard.dataset.deleteUrl;
        openModal(deleteConfirmModal);
    });
}
if (cancelDeleteButton) cancelDeleteButton.addEventListener('click', () => closeModal(deleteConfirmModal));

const listingSearch = document.querySelector('#listing-search');
const listingStatusFilter = document.querySelector('#listing-status-filter');
const noResults = document.querySelector('.no-filter-results');
function applyFilters() {
    const status = listingStatusFilter ? listingStatusFilter.value : 'all';
    const search = listingSearch ? listingSearch.value.trim().toLowerCase() : '';
    let visibleCount = 0;
    document.querySelectorAll('.seller-listing').forEach((card) => {
        const visible = (status === 'all' || card.dataset.status === status) && (!search || card.dataset.search.includes(search));
        card.hidden = !visible;
        if (visible) visibleCount += 1;
    });
    if (noResults) noResults.hidden = visibleCount > 0;
}
if (listingSearch) listingSearch.addEventListener('input', applyFilters);
if (listingStatusFilter) listingStatusFilter.addEventListener('change', applyFilters);
const listingFiltersForm = document.querySelector('#listing-filters');
if (listingFiltersForm) listingFiltersForm.addEventListener('submit', (event) => event.preventDefault());
