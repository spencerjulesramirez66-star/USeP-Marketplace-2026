export function openDialog(dialog) {
    if (dialog && typeof dialog.showModal === 'function' && !dialog.open) dialog.showModal();
}

export function closeDialog(dialog) {
    if (dialog && dialog.open) dialog.close();
}

export function confirmDialog(dialog, confirmSelector) {
    return new Promise((resolve) => {
        const confirmButton = dialog.querySelector(confirmSelector);
        const onConfirm = () => { cleanup(); dialog.close(); resolve(true); };
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
