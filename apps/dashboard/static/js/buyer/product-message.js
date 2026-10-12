(function () {
    'use strict';

    const getDialog = () => document.getElementById('quick-message-dialog');

    function showError(dialog, message) {
        const box = dialog.querySelector('.quick-message__error');
        box.textContent = message;
        box.hidden = !message;
    }

    function openDialog(button) {
        const dialog = getDialog();
        if (!dialog) return;

        const form = dialog.querySelector('form');
        form.action = button.dataset.startUrl;
        form.reset();
        dialog.querySelector('[data-count]').textContent = '0';
        showError(dialog, '');

        dialog.querySelector('.quick-message__item-title').textContent = button.dataset.title || '';
        dialog.querySelector('.quick-message__item-meta').textContent =
            [button.dataset.price, button.dataset.seller].filter(Boolean).join(' \u2022 ');
        dialog.querySelector('.quick-message__thumb').src = button.dataset.image || '';

        dialog.showModal();
        dialog.querySelector('textarea').focus();
    }

    function closeDialog() {
        const dialog = getDialog();
        if (dialog && dialog.open) dialog.close();
    }

    async function submitMessage(form) {
        const dialog = getDialog();
        const textarea = form.querySelector('textarea');
        const sendBtn = form.querySelector('.quick-message__send');

        if (!textarea.value.trim()) {
            showError(dialog, 'Write a message first.');
            textarea.focus();
            return;
        }

        sendBtn.disabled = true;
        sendBtn.textContent = 'Sending...';
        showError(dialog, '');

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json, text/html',
                },
            });

            // Case 1: the view redirects to the conversation page.
            if (response.redirected) {
                window.location.href = response.url;
                return;
            }

            const type = response.headers.get('content-type') || '';
            if (type.includes('application/json')) {
                const data = await response.json();
                if (!response.ok || data.ok === false || data.error) {
                    throw new Error(data.error || data.message || 'Could not send your message.');
                }
                // Case 2: JSON containing a URL to the conversation.
                window.location.href = data.redirect_url || data.url || data.conversation_url || '/messages/';
                return;
            }

            if (!response.ok) throw new Error('Could not send your message.');
            window.location.href = '/messages/';
        } catch (err) {
            showError(dialog, err.message || 'Something went wrong. Please try again.');
            sendBtn.disabled = false;
            sendBtn.textContent = 'Send message';
        }
    }

    document.addEventListener('click', function (event) {
        const openBtn = event.target.closest('[data-message-open]');
        if (openBtn) {
            event.preventDefault();
            openDialog(openBtn);
            return;
        }

        if (event.target.closest('[data-message-close]')) {
            closeDialog();
            return;
        }

        const chip = event.target.closest('[data-chip]');
        if (chip) {
            const textarea = getDialog().querySelector('textarea');
            textarea.value = chip.dataset.chip;
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
            textarea.focus();
            return;
        }

        // Click on the backdrop closes the dialog.
        const dialog = getDialog();
        if (dialog && event.target === dialog) closeDialog();
    });

    document.addEventListener('input', function (event) {
        if (event.target.matches('#quick-message-body')) {
            getDialog().querySelector('[data-count]').textContent = event.target.value.length;
        }
    });

    document.addEventListener('submit', function (event) {
        if (event.target.closest('#quick-message-dialog')) {
            event.preventDefault();
            submitMessage(event.target);
        }
    });

    // Ctrl/Cmd + Enter sends.
    document.addEventListener('keydown', function (event) {
        if (event.target.matches('#quick-message-body') && event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
            event.preventDefault();
            event.target.form.requestSubmit();
        }
    });
})();