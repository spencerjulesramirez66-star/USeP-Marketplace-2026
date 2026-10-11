document.querySelectorAll('[data-description-toggle]').forEach((toggle) => {
    const description = document.getElementById(toggle.getAttribute('aria-controls'));
    if (!description) return;

    const update = () => {
        const wasExpanded = description.classList.contains('is-expanded');
        description.classList.add('is-collapsible');
        const needsToggle = description.scrollHeight > description.clientHeight + 1;
        if (!needsToggle) {
            description.classList.remove('is-collapsible', 'is-expanded');
            toggle.hidden = true;
            return;
        }
        description.classList.toggle('is-expanded', wasExpanded);
        toggle.hidden = false;
        toggle.setAttribute('aria-expanded', wasExpanded ? 'true' : 'false');
        toggle.textContent = wasExpanded ? 'Show less' : 'Read more';
    };

    toggle.addEventListener('click', () => {
        const expanding = !description.classList.contains('is-expanded');
        description.classList.toggle('is-expanded', expanding);
        toggle.setAttribute('aria-expanded', expanding ? 'true' : 'false');
        toggle.textContent = expanding ? 'Show less' : 'Read more';
        if (!expanding && toggle.getBoundingClientRect().top < 0) {
            toggle.scrollIntoView({ block: 'nearest' });
        }
    });

    update();
    new ResizeObserver(update).observe(description);
});
