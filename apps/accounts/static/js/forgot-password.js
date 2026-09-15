// Prevent double submission — a double-click or slow response can
// fire two POSTs, and the second one invalidates the code the first
// one just sent, making a perfectly valid code look like it "doesn't
// exist" by the time you try to use it.

document.querySelectorAll('#form-container form').forEach((form) => {
    form.addEventListener('submit', () => {
        const button = form.querySelector('button[type="submit"]');
        if (button) {
            button.disabled = true;
        }
    });
});