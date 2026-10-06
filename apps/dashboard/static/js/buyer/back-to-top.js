/** "Back to top" floating button: shows after 400px of scroll. */
(function () {
    'use strict';

    const SHOW_AFTER_PX = 400;

    function init() {
        const button = document.getElementById('back-to-top');
        if (!button) return;

        const toggle = () => button.classList.toggle('visible', window.scrollY > SHOW_AFTER_PX);
        window.addEventListener('scroll', toggle, { passive: true });
        button.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
        toggle();
    }

    document.addEventListener('DOMContentLoaded', init);
})();
