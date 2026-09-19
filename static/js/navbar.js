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

const messageLink = document.querySelector("[data-unread-count-url]");
const marketplace = window.USePMarketplace = window.USePMarketplace || {};
const debugMessagesBadge = (...args) => {
    if (window.MESSAGES_BADGE_DEBUG) console.debug("[Messages Badge]", ...args);
};

// This is deliberately the only place that changes the Messages badge UI.
marketplace.updateMessageNotificationBadge = (value) => {
    const count = Number.isFinite(Number(value)) ? Math.max(0, Number(value)) : 0;
    const badges = document.querySelectorAll("[data-message-unread-badge]");
    badges.forEach((badge) => {
        badge.hidden = count === 0;
        badge.textContent = count > 99 ? "99+" : (count ? String(count) : "");
    });
    debugMessagesBadge(`updating ${badges.length} badge element(s)`, { count });
};

document.addEventListener("messages:unread-count", (event) => {
    marketplace.updateMessageNotificationBadge(event.detail?.count);
});

if (messageLink) {
    const messagesSidebarIsPresent = Boolean(document.querySelector(".messaging-layout[data-conversation-sidebar-state-url]"));
    let pollTimer = null;
    let pollInFlight = false;
    let pollingStopped = false;

    const refreshUnreadBadge = async () => {
        if (pollInFlight) return;
        pollInFlight = true;
        try {
            const response = await fetch(messageLink.dataset.unreadCountUrl, {
                method: "GET",
                credentials: "same-origin",
                cache: "no-store",
                headers: { "Accept": "application/json", "X-Requested-With": "XMLHttpRequest" },
            });
            if (!response.ok) return;
            const payload = await response.json();
            document.dispatchEvent(new CustomEvent("messages:unread-count", {
                detail: { count: payload.unread_count },
            }));
        } catch (_) {
            // Preserve the last displayed count and retry on the next interval.
        } finally {
            pollInFlight = false;
        }
    };

    const pollUnreadBadge = async () => {
        if (pollingStopped) return;
        await refreshUnreadBadge();
        if (!pollingStopped) pollTimer = window.setTimeout(pollUnreadBadge, document.hidden ? 5000 : 2000);
    };

    // The Messages sidebar already polls the same authoritative state.  It
    // dispatches messages:unread-count above, so do not duplicate requests.
    if (!messagesSidebarIsPresent) {
        refreshUnreadBadge();
        pollTimer = window.setTimeout(pollUnreadBadge, document.hidden ? 5000 : 2000);
        document.addEventListener("visibilitychange", () => { if (!document.hidden) refreshUnreadBadge(); });
        window.addEventListener("focus", refreshUnreadBadge);
        document.addEventListener("messages:unread-changed", refreshUnreadBadge);
        window.addEventListener("pagehide", () => {
            pollingStopped = true;
            window.clearTimeout(pollTimer);
        }, { once: true });
    }
}
