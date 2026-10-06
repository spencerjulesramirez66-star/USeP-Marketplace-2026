/**
 * Mobile navbar search: the search button toggles the expanded search bar.
 * Independent of live-search.js (it only needs the form + input).
 */
(function () {
    'use strict';

    function init() {
        const form = document.querySelector('.navbar-search');
        const input = form ? form.querySelector('input[name="q"]') : null;
        const button = form ? form.querySelector('.navbar-mobile-search-submit') : null;
        if (!form || !input || !button) return;

        const isMobile = window.matchMedia('(max-width: 760px)');

        function setOpen(isOpen) {
            form.classList.toggle('is-mobile-search-open', isOpen);
            const label = isOpen ? 'Close search' : 'Search marketplace';
            button.setAttribute('aria-label', label);
            button.title = label;
            const icon = button.querySelector('i');
            if (icon) icon.className = `bi ${isOpen ? 'bi-x-lg' : 'bi-search'}`;
            if (isOpen) window.setTimeout(() => input.focus(), 0);
        }

        button.addEventListener('click', () => {
            if (!isMobile.matches) return;
            setOpen(!form.classList.contains('is-mobile-search-open'));
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && form.classList.contains('is-mobile-search-open')) setOpen(false);
        });

        isMobile.addEventListener('change', (event) => {
            if (!event.matches) setOpen(false);
        });
    }

    document.addEventListener('DOMContentLoaded', init);
})();
