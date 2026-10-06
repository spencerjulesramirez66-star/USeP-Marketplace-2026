import { qs, on } from './dom.js';

// Full-screen viewer for images shared in the thread or in the details panel.
// Builds its gallery from whatever [data-media-url] elements are on the page
// at the moment it opens, so it stays correct as new messages arrive.

export function initLightbox() {
    const dialog = qs('#messaging-lightbox');
    if (!dialog) return;
    const img = qs('img', dialog);
    const counter = qs('.messaging-lightbox-count', dialog);
    let gallery = [];
    let index = 0;

    function collectGallery() {
        gallery = Array.from(document.querySelectorAll('[data-media-url]')).map((el) => ({
            url: el.dataset.mediaUrl,
            name: el.dataset.mediaName || '',
        }));
    }

    function show(i) {
        if (!gallery.length) return;
        index = (i + gallery.length) % gallery.length;
        img.src = gallery[index].url;
        img.alt = gallery[index].name;
        counter.textContent = `${index + 1} / ${gallery.length}`;
    }

    function openAt(url) {
        collectGallery();
        const found = gallery.findIndex((item) => item.url === url);
        show(found === -1 ? 0 : found);
        dialog.showModal();
    }

    on(document, 'click', '[data-media-url]', (evt, target) => {
        // Video attachments handle their own <video controls>; only images open the lightbox.
        if (target.tagName === 'VIDEO' || target.querySelector('video')) return;
        evt.preventDefault();
        openAt(target.dataset.mediaUrl);
    });

    qs('.messaging-lightbox-prev', dialog).addEventListener('click', () => show(index - 1));
    qs('.messaging-lightbox-next', dialog).addEventListener('click', () => show(index + 1));
    qs('.messaging-lightbox-close', dialog).addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', (evt) => { if (evt.target === dialog) dialog.close(); });
    dialog.addEventListener('keydown', (evt) => {
        if (evt.key === 'ArrowLeft') show(index - 1);
        if (evt.key === 'ArrowRight') show(index + 1);
    });
}
