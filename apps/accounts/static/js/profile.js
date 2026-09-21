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

// ---------- Inline field editing (regular form POST, no AJAX) ----------
const fieldsContainer = document.getElementById("editable-fields");

if (fieldsContainer) {
    function setIcon(fieldDiv, editing) {
        const icon = fieldDiv.querySelector(".button-toggle-icon");
        icon.classList.toggle("bi-pen", !editing);
        icon.classList.toggle("bi-check-lg", editing);
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

        fieldDiv.classList.remove("is-editing");
        input.hidden = true;
        setIcon(fieldDiv, false);
    }

    // Pencil icon: open the editor, or submit the form if already editing
    fieldsContainer.addEventListener("click", (event) => {
        const icon = event.target.closest(".button-toggle-icon");
        if (!icon) return;

        const fieldDiv = icon.closest(".profile-field");
        if (!fieldDiv || !fieldDiv.dataset.field) return;

        if (fieldDiv.classList.contains("is-editing")) {
            const form = fieldDiv.querySelector("form");
            const input = form.querySelector(".toggle-input");
            const newValue = input.value.trim();

            if (newValue === input.dataset.originalValue) {
                exitEditMode(fieldDiv, false);
            } else {
                input.value = newValue;
                form.submit();   // real browser navigation, page reloads after the redirect
            }
        } else {
            enterEditMode(fieldDiv);
        }
    });

    fieldsContainer.addEventListener("keydown", (event) => {
        const icon = event.target.closest(".button-toggle-icon");
        if (icon && (event.key === "Enter" || event.key === " ")) {
            event.preventDefault();
            icon.click();
            return;
        }

        // Enter inside the input submits the form natively
        const input = event.target.closest(".toggle-input");
        if (input && event.key === "Escape") {
            event.preventDefault();
            exitEditMode(input.closest(".profile-field"), true);
        }
    });

    // Skip the request if nothing changed
    fieldsContainer.addEventListener("submit", (event) => {
        const fieldDiv = event.target.closest(".profile-field");
        const input = event.target.querySelector(".toggle-input");
        const newValue = input.value.trim();

        if (newValue === input.dataset.originalValue) {
            event.preventDefault();
            exitEditMode(fieldDiv, false);
            return;
        }

        input.value = newValue;
    });
}