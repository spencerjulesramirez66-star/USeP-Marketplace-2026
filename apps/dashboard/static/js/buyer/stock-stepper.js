/**
 * Shared +/- stepper for any `.stepper-control` containing an
 * <input type="number"> and `.stepper-button[data-step]` buttons.
 * One delegated listener replaces the copies in detail-edit-modal.js and
 * edit-listing-gallery.js. If you load this, delete those copies, or the
 * value will change twice per click.
 */
(function () {
    'use strict';

    document.addEventListener('click', (event) => {
        const button = event.target.closest('.stepper-control .stepper-button');
        if (!button) return;
        const input = button.closest('.stepper-control').querySelector('input[type="number"]');
        if (!input) return;

        const current = Number(input.value || 0);
        const step = Number(button.dataset.step || 1);
        input.value = Math.max(0, current + step);
        input.dispatchEvent(new Event('input', { bubbles: true }));
    });
})();
