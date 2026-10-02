function initPasswordToggle(inputId, toggleId) {
    const input = document.getElementById(inputId);
    const toggle = document.getElementById(toggleId);

    if (!input || !toggle) return;

    toggle.addEventListener("click", function () {
        if (input.type === "password") {
            input.type = "text";
            toggle.classList.remove("bi-eye-slash");
            toggle.classList.add("bi-eye");
        } else {
            input.type = "password";
            toggle.classList.remove("bi-eye");
            toggle.classList.add("bi-eye-slash");
        }
    });
}

initPasswordToggle("current-password", "show-current-password");
initPasswordToggle("new-password", "show-new-password");
initPasswordToggle("confirm-password", "show-confirm-password");