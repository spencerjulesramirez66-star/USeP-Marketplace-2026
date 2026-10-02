// Thin wrapper around the native <dialog> element, shared by every
// confirm/option-sheet in the page. Not a framework: just showModal/close.

export function openDialog(dialog) {
    if (dialog && typeof dialog.showModal === 'function' && !dialog.open) dialog.showModal();
}

export function closeDialog(dialog) {
    if (dialog && dialog.open) dialog.close();
}

/** Resolves true/false once the user picks an option in a confirm dialog. */
export function confirmDialog(dialog, confirmSelector) {
    return new Promise((resolve) => {
        const confirmButton = dialog.querySelector(confirmSelector);
        const onConfirm = () => { cleanup(); resolve(true); };
        const onClose = () => { cleanup(); resolve(false); };
        function cleanup() {
            confirmButton.removeEventListener('click', onConfirm);
            dialog.removeEventListener('close', onClose);
        }
        confirmButton.addEventListener('click', onConfirm);
        dialog.addEventListener('close', onClose);
        openDialog(dialog);
    });
}
