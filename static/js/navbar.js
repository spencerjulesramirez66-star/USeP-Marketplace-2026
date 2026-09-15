const profileToggle = document.getElementById("profile-toggle");
const profileDropdown = document.getElementById("profile-dropdown");

if (profileToggle && profileDropdown) {
    function closeDropdown() {
        profileDropdown.classList.remove("open");
        profileToggle.setAttribute("aria-expanded", "false");
    }

    function openDropdown() {
        profileDropdown.classList.add("open");
        profileToggle.setAttribute("aria-expanded", "true");
    }

    profileToggle.addEventListener("click", (event) => {
        event.stopPropagation();

        if (profileDropdown.classList.contains("open")) {
            closeDropdown();
        } else {
            openDropdown();
        }
    });

    document.addEventListener("click", (event) => {
        if (!profileDropdown.contains(event.target)) {
            closeDropdown();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeDropdown();
        }
    });
}

// CATEGORIES MENU (HAMBURGER)
const categoriesMenuBtn = document.getElementById("categories-menu-btn");
const categoriesMenu = document.getElementById("categories-menu");
const categoriesMenuContent = document.querySelector(".categories-menu-content");

if (categoriesMenuBtn && categoriesMenu) {
    categoriesMenuBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        const isExpanded = categoriesMenuBtn.getAttribute("aria-expanded") === "true";
        categoriesMenuBtn.setAttribute("aria-expanded", !isExpanded);
        categoriesMenu.classList.toggle("open");
        categoriesMenu.setAttribute("aria-hidden", isExpanded);
    });

    document.addEventListener("click", (event) => {
        const isClickInsideContent = categoriesMenuContent && categoriesMenuContent.contains(event.target);
        const isClickOnButton = categoriesMenuBtn.contains(event.target);
        
        if (!isClickInsideContent && !isClickOnButton) {
            categoriesMenuBtn.setAttribute("aria-expanded", "false");
            categoriesMenu.classList.remove("open");
            categoriesMenu.setAttribute("aria-hidden", "true");
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            categoriesMenuBtn.setAttribute("aria-expanded", "false");
            categoriesMenu.classList.remove("open");
            categoriesMenu.setAttribute("aria-hidden", "true");
        }
    });

    // Close menu when a category link is clicked
    const categoryLinks = categoriesMenu.querySelectorAll(".categories-menu-list a");
    categoryLinks.forEach((link) => {
        link.addEventListener("click", () => {
            categoriesMenuBtn.setAttribute("aria-expanded", "false");
            categoriesMenu.classList.remove("open");
            categoriesMenu.setAttribute("aria-hidden", "true");
        });
    });
}


// PROFILE PICTURE UPLOAD
// Picking a file submits the form immediately — no separate
// "Save" step for a single-field upload.

const profilePictureInput = document.getElementById("profile-picture-input");
const profilePictureForm = document.getElementById("profile-picture-form");

if (profilePictureInput && profilePictureForm) {
    profilePictureInput.addEventListener("change", () => {
        if (profilePictureInput.files.length > 0) {
            profilePictureForm.submit();
        }
    });
}