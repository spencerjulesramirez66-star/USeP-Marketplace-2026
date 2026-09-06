document.addEventListener('DOMContentLoaded', () => {
    const modal = document.querySelector('#chat-coming-soon-modal');
    if (!modal) return;

    const closeModal = () => {
        modal.hidden = true;
    };

    document.addEventListener('click', (event) => {
        const button = event.target.closest('.chat-coming-soon');
        if (!button) return;
        event.preventDefault();
        event.stopPropagation();
        if (button !== modal) {
            modal.hidden = false;
        }
    });

    document.querySelectorAll('[data-close-chat-modal]').forEach((button) => {
        button.addEventListener('click', closeModal);
    });

    modal.addEventListener('click', (event) => {
        if (event.target === modal) closeModal();
    });
});