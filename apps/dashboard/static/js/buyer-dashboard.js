document.addEventListener('DOMContentLoaded', () => {
    const mainImage = document.querySelector('.detail-image');
    const thumbs = document.querySelectorAll('.thumb');

    if (mainImage && thumbs.length) {
        const updateMainImage = (src) => {
            mainImage.style.backgroundImage = `url('${src}')`;
            thumbs.forEach((thumb) => thumb.classList.toggle('active', thumb.dataset.image === src));
        };

        thumbs.forEach((thumb) => {
            thumb.addEventListener('click', () => updateMainImage(thumb.dataset.image));
        });
    }

    const backToTopButton = document.getElementById('back-to-top');
    if (backToTopButton) {
        const toggleBackToTop = () => backToTopButton.classList.toggle('visible', window.scrollY > 400);
        window.addEventListener('scroll', toggleBackToTop, { passive: true });
        backToTopButton.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
        toggleBackToTop();
    }
});
