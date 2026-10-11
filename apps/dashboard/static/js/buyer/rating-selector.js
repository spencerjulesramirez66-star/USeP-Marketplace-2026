document.querySelectorAll('[data-rating-selector]').forEach((selector) => {
    const stars = Array.from(selector.querySelectorAll('[data-rating-star]'));
    const indicator = selector.parentElement.querySelector('[data-rating-indicator]');

    function selectedValue() {
        return Number(selector.querySelector('input:checked')?.value || 0);
    }

    function render(value) {
        stars.forEach((star) => {
            const isActive = Number(star.dataset.ratingValue) <= value;
            star.classList.toggle('is-active', isActive);
            star.querySelector('i').className = `bi ${isActive ? 'bi-star-fill' : 'bi-star'}`;
        });
        indicator.textContent = value ? `${value} out of 5` : 'Select a rating';
    }

    selector.addEventListener('pointerover', (event) => {
        if (event.pointerType === 'touch') return;
        const star = event.target.closest('[data-rating-star]');
        if (star && selector.contains(star)) render(Number(star.dataset.ratingValue));
    });
    selector.addEventListener('pointerleave', () => render(selectedValue()));
    selector.addEventListener('change', () => render(selectedValue()));
    render(selectedValue());
});
