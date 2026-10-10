// ---------- Avatar upload ----------
const avatarInput = document.getElementById("avatar-input");
const avatarForm = document.getElementById("avatar-form");

if (avatarInput && avatarForm) {
    avatarInput.addEventListener("change", () => {
        if (avatarInput.files.length > 0) {
            avatarForm.submit();
        }
    });
}

// ---------- Inline field editing (AJAX) ----------
const fieldsContainer = document.getElementById("editable-fields");

if (fieldsContainer) {
    function setIcon(fieldDiv, editing) {
        const icon = fieldDiv.querySelector(".button-toggle-icon");
        icon.classList.toggle("bi-pen", !editing);
        icon.classList.toggle("bi-check-lg", editing);
    }

    // Update the visible text next to the input.
    // Change ".field-value" to whatever element shows the value in your markup.
    function setDisplayValue(fieldDiv, value) {
        const field = fieldDiv.dataset.field;

        // The field's own visible text
        const own = fieldDiv.querySelector(".field-value");
        if (own) own.textContent = value;

        // Everything else on the page that shows this field (hero, navbar, etc.)
        document.querySelectorAll(`[data-display="${field}"]`).forEach((el) => {
            el.textContent = value;
        });
    }
    
    function enterEditMode(fieldDiv) {
        document.querySelectorAll(".profile-field.is-editing").forEach((el) => {
            if (el !== fieldDiv) exitEditMode(el, true);
        });

        const input = fieldDiv.querySelector(".toggle-input");

        input.dataset.originalValue = input.value;
        fieldDiv.classList.add("is-editing");
        input.hidden = false;
        setIcon(fieldDiv, true);
        input.focus();
        input.select();
    }

    function exitEditMode(fieldDiv, revert) {
        const input = fieldDiv.querySelector(".toggle-input");

        if (revert) {
            input.value = input.dataset.originalValue;
        }

        // Remove the class first so the focusout handler ignores the blur
        // triggered by hiding the input.
        fieldDiv.classList.remove("is-editing");
        input.hidden = true;
        setIcon(fieldDiv, false);
    }

    function showFieldError(fieldDiv, message) {
        fieldDiv.classList.add("has-error");
        fieldDiv.title = message;
        setTimeout(() => {
            fieldDiv.classList.remove("has-error");
            fieldDiv.removeAttribute("title");
        }, 3000);
    }

    // Send the value in the background. Guarded so it can't fire twice.
    async function submitField(fieldDiv) {
        if (fieldDiv.dataset.submitting === "true") return;

        const form = fieldDiv.querySelector("form");
        const input = form.querySelector(".toggle-input");
        const newValue = input.value.trim();

        if (newValue === input.dataset.originalValue) {
            exitEditMode(fieldDiv, false);
            return;
        }

        input.value = newValue;
        fieldDiv.dataset.submitting = "true";
        fieldDiv.classList.add("is-saving");

        try {
            // FormData picks up every input in the form, including a hidden
            // CSRF token if you have one.
            const response = await fetch(form.action, {
                method: (form.method || "POST").toUpperCase(),
                body: new FormData(form),
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json",
                },
                credentials: "same-origin",
            });

            if (!response.ok) {
                let message = "Could not save changes.";
                try {
                    const err = await response.json();
                    if (err && (err.error || err.message)) message = err.error || err.message;
                } catch (_) { /* response wasn't JSON */ }
                throw new Error(message);
            }

            // Prefer the value the server returns (it may normalise it),
            // otherwise fall back to what the user typed.
            let savedValue = newValue;
            const contentType = response.headers.get("content-type") || "";
            if (contentType.includes("application/json")) {
                const data = await response.json();
                if (data && typeof data.value === "string") savedValue = data.value;
            }

            input.value = savedValue;
            input.dataset.originalValue = savedValue;
            setDisplayValue(fieldDiv, savedValue);
            exitEditMode(fieldDiv, false);
        } catch (error) {
            exitEditMode(fieldDiv, true); // put the old value back
            showFieldError(fieldDiv, error.message || "Network error.");
        } finally {
            fieldDiv.classList.remove("is-saving");
            delete fieldDiv.dataset.submitting;
        }
    }

    // Keep focus in the input when the check/pencil icon is pressed, so the
    // click handler (not the blur handler) decides what happens.
    fieldsContainer.addEventListener("mousedown", (event) => {
        if (event.target.closest(".button-toggle-icon")) {
            event.preventDefault();
        }
    });

    // Pencil icon: open the editor, or save if already editing
    fieldsContainer.addEventListener("click", (event) => {
        const icon = event.target.closest(".button-toggle-icon");
        if (!icon) return;

        const fieldDiv = icon.closest(".profile-field");
        if (!fieldDiv || !fieldDiv.dataset.field) return;

        if (fieldDiv.classList.contains("is-editing")) {
            submitField(fieldDiv);
        } else {
            enterEditMode(fieldDiv);
        }
    });

    // Leaving the input (click elsewhere, Tab, etc.) saves immediately
    fieldsContainer.addEventListener("focusout", (event) => {
        const input = event.target.closest(".toggle-input");
        if (!input) return;

        const fieldDiv = input.closest(".profile-field");
        if (!fieldDiv || !fieldDiv.classList.contains("is-editing")) return;

        submitField(fieldDiv);
    });

    fieldsContainer.addEventListener("keydown", (event) => {
        const icon = event.target.closest(".button-toggle-icon");
        if (icon && (event.key === "Enter" || event.key === " ")) {
            event.preventDefault();
            icon.click();
            return;
        }

        const input = event.target.closest(".toggle-input");
        if (input && event.key === "Escape") {
            event.preventDefault();
            exitEditMode(input.closest(".profile-field"), true);
        }
    });

    // Enter inside the input triggers a native form submit; intercept it
    fieldsContainer.addEventListener("submit", (event) => {
        event.preventDefault();
        const fieldDiv = event.target.closest(".profile-field");
        if (fieldDiv) submitField(fieldDiv);
    });
}