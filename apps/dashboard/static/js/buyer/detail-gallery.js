/**
 * Listing detail page: clicking a thumbnail swaps the main image.
 * NOTE: the old version set style.backgroundImage on an <img>, which does nothing.
 * .detail-image is an <img>, so we set its src instead.
 */
(function () {
    'use strict';

    function init() {
        const mainImage = document.querySelector('.detail-image');
        const thumbs = document.querySelectorAll('.thumb');
        if (!mainImage || !thumbs.length) return;

        const show = (thumb) => {
            const src = thumb.dataset.image || thumb.currentSrc || thumb.src;
            mainImage.src = src;
            thumbs.forEach((t) => t.classList.toggle('active', t === thumb));
        };

        thumbs.forEach((thumb) => {
            thumb.addEventListener('click', (event) => {
                // Thumbs may sit inside <a> (no-JS fallback); don't navigate.
                if (thumb.closest('a')) event.preventDefault();
                show(thumb);
            });
        });
    }

    document.addEventListener('DOMContentLoaded', init);
})();
