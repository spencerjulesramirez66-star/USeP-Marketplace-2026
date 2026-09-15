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

// ---------- Inline field editing ----------
function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return match ? decodeURIComponent(match[2]) : null;
}

const fieldsContainer = document.getElementById("editable-fields");

if (fieldsContainer) {
    const updateUrl = fieldsContainer.dataset.updateUrl;
    const csrfToken = getCookie("csrftoken");

    function enterEditMode(fieldDiv) {
        document.querySelectorAll(".profile-field.is-editing").forEach((el) => {
            if (el !== fieldDiv) exitEditMode(el, false);
        });

        const input = fieldDiv.querySelector(".toggle-input");
        const valueSpan = fieldDiv.querySelector(".field-value");

        input.dataset.originalValue = valueSpan.textContent.trim();
        fieldDiv.classList.add("is-editing");
        input.hidden = false;
        input.focus();
        input.select();
    }

    function exitEditMode(fieldDiv, revert) {
        const input = fieldDiv.querySelector(".toggle-input");
        const errorEl = fieldDiv.querySelector(".field-error");

        if (revert) {
            input.value = input.dataset.originalValue;
        }

        fieldDiv.classList.remove("is-editing");
        input.hidden = true;
        errorEl.hidden = true;
        errorEl.textContent = "";
    }

    async function saveField(fieldDiv) {
        const fieldName = fieldDiv.dataset.field;
        const input = fieldDiv.querySelector(".toggle-input");
        const valueSpan = fieldDiv.querySelector(".field-value");
        const errorEl = fieldDiv.querySelector(".field-error");
        const newValue = input.value.trim();

        if (newValue === input.dataset.originalValue) {
            exitEditMode(fieldDiv, false);
            return;
        }

        input.disabled = true;

        try {
            const response = await fetch(updateUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": csrfToken,
                },
                body: new URLSearchParams({ field: fieldName, value: newValue }),
            });

            const data = await response.json();

            if (response.ok && data.success) {
                valueSpan.textContent = data.value;
                input.value = data.value;
                exitEditMode(fieldDiv, false);
            } else {
                errorEl.textContent = data.error || "Could not save. Try again.";
                errorEl.hidden = false;
            }
        } catch (err) {
            errorEl.textContent = "Network error. Try again.";
            errorEl.hidden = false;
        } finally {
            input.disabled = false;
        }
    }

    fieldsContainer.addEventListener("click", (event) => {
        const icon = event.target.closest(".button-toggle-icon");
        if (!icon) return;

        const fieldDiv = icon.closest(".profile-field");
        if (!fieldDiv || !fieldDiv.dataset.field) return;

        if (fieldDiv.classList.contains("is-editing")) {
            saveField(fieldDiv);
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

        const input = event.target.closest(".toggle-input");
        if (!input) return;

        const fieldDiv = input.closest(".profile-field");

        if (event.key === "Enter") {
            event.preventDefault();
            saveField(fieldDiv);
        } else if (event.key === "Escape") {
            event.preventDefault();
            exitEditMode(fieldDiv, true);
        }
    });

    fieldsContainer.addEventListener(
        "focusout",
        (event) => {
            const input = event.target.closest(".toggle-input");
            if (!input) return;

            const fieldDiv = input.closest(".profile-field");
            if (fieldDiv.classList.contains("is-editing")) {
                saveField(fieldDiv);
            }
        },
        true
    );
}