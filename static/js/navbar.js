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

    if (!marketplace.notificationSocketClientInitialized) {
    marketplace.notificationSocketClientInitialized = true;
    const seenNotificationMessageIds = new Set();
    const maxSeenNotificationMessageIds = 150;
    let notificationSocket = null;
    let reconnectTimer = null;
    let reconnectDelay = 1000;
    let pageIsLeaving = false;

    const rememberNotification = (messageId) => {
        const id = String(messageId);
        if (seenNotificationMessageIds.has(id)) return false;
        seenNotificationMessageIds.add(id);
        if (seenNotificationMessageIds.size > maxSeenNotificationMessageIds) {
            seenNotificationMessageIds.delete(seenNotificationMessageIds.values().next().value);
        }
        return true;
    };

    const activeConversationId = () => {
        const pollUrl = document.querySelector('.messaging-thread[data-poll-url]')?.dataset.pollUrl || '';
        return pollUrl.match(/messages\/(\d+)\/new/)?.[1] || null;
    };

    const toastStack = () => {
        let stack = document.querySelector('[data-message-notification-stack]');
        if (!stack) {
            stack = document.createElement('div');
            stack.className = 'message-notification-toast-stack';
            stack.dataset.messageNotificationStack = '';
            stack.setAttribute('aria-live', 'polite');
            stack.setAttribute('aria-relevant', 'additions');
            document.body.appendChild(stack);
        }
        return stack;
    };

    const dismissMessageToast = (toast) => {
        if (!toast || toast.dataset.dismissing === 'true') return;
        toast.dataset.dismissing = 'true';
        toast.classList.add('is-leaving');
        const removeToast = () => toast.remove();
        toast.addEventListener('animationend', removeToast, { once: true });
        window.setTimeout(removeToast, 240);
    };

    const showMessageToast = (payload) => {
        if (document.visibilityState === 'visible' && activeConversationId() === String(payload.conversation_id)) return;

        const stack = toastStack();
        const activeToasts = [...stack.children].filter((toast) => toast.dataset.dismissing !== 'true');
        if (activeToasts.length >= 3) dismissMessageToast(activeToasts[0]);

        const toast = document.createElement('a');
        toast.className = 'message-notification-toast';
        toast.href = payload.conversation_url || messageLink.href;
        const avatar = document.createElement('img');
        avatar.className = 'message-notification-toast-avatar';
        avatar.src = payload.sender?.avatar_url || '';
        avatar.alt = '';
        const copy = document.createElement('span');
        copy.className = 'message-notification-toast-copy';
        const sender = document.createElement('strong');
        sender.textContent = payload.sender?.name || 'New message';
        const description = document.createElement('span');
        description.textContent = 'sent you a message';
        const listing = document.createElement('span');
        listing.className = 'message-notification-toast-listing';
        const listingTitle = payload.listing_title || 'Listing unavailable';
        listing.textContent = `About: ${listingTitle}`;
        listing.title = listingTitle;
        const preview = document.createElement('span');
        preview.className = 'message-notification-toast-preview';
        preview.textContent = payload.preview || 'Sent an attachment';
        copy.append(sender, description, listing, preview);
        const dismiss = document.createElement('button');
        dismiss.type = 'button';
        dismiss.className = 'message-notification-toast-dismiss';
        dismiss.setAttribute('aria-label', 'Dismiss message notification');
        dismiss.textContent = '\u00d7';
        dismiss.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            dismissMessageToast(toast);
        });
        toast.append(avatar, copy, dismiss);
        stack.appendChild(toast);

        let dismissTimer = window.setTimeout(() => dismissMessageToast(toast), 5000);
        const pauseDismiss = () => window.clearTimeout(dismissTimer);
        const resumeDismiss = () => { dismissTimer = window.setTimeout(() => dismissMessageToast(toast), 2500); };
        toast.addEventListener('mouseenter', pauseDismiss);
        toast.addEventListener('mouseleave', resumeDismiss);
        toast.addEventListener('focusin', pauseDismiss);
        toast.addEventListener('focusout', resumeDismiss);
    };

    const scheduleNotificationReconnect = () => {
        if (pageIsLeaving || reconnectTimer) return;
        reconnectTimer = window.setTimeout(() => {
            reconnectTimer = null;
            connectNotificationSocket();
        }, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 16000);
    };

    const connectNotificationSocket = () => {
        if (pageIsLeaving || !window.WebSocket || !messageLink.dataset.notificationSocketPath) return;
        if (notificationSocket && (notificationSocket.readyState === WebSocket.OPEN || notificationSocket.readyState === WebSocket.CONNECTING)) return;
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        notificationSocket = new WebSocket(`${protocol}://${window.location.host}${messageLink.dataset.notificationSocketPath}`);
        marketplace.notificationSocket = notificationSocket;
        notificationSocket.addEventListener('open', () => {
            reconnectDelay = 1000;
            refreshUnreadBadge();
        });
        notificationSocket.addEventListener('message', (event) => {
            let payload;
            try {
                payload = JSON.parse(event.data);
            } catch (_) {
                return;
            }
            if (payload?.type !== 'message_notification' || !payload.message_id || !rememberNotification(payload.message_id)) return;
            marketplace.updateMessageNotificationBadge(payload.unread_count);
            showMessageToast(payload);
        });
        notificationSocket.addEventListener('error', () => {
            // Close is responsible for the single reconnect schedule.
        });
        notificationSocket.addEventListener('close', () => {
            notificationSocket = null;
            marketplace.notificationSocket = null;
            scheduleNotificationReconnect();
        });
    };

    connectNotificationSocket();
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) connectNotificationSocket();
    });
    window.addEventListener('pagehide', () => {
        pageIsLeaving = true;
        window.clearTimeout(reconnectTimer);
        if (notificationSocket?.readyState === WebSocket.OPEN || notificationSocket?.readyState === WebSocket.CONNECTING) {
            notificationSocket.close(1000, 'Page unloading');
        }
    }, { once: true });
    }

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
