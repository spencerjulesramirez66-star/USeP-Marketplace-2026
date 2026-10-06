import { qs, qsa, on } from './dom.js';
import { get, postForm } from './api.js';
import { openDialog, closeDialog, confirmDialog } from './dialogs.js';
import { createPoller } from './polling.js';

// Sidebar badge/ordering refresh (via polling, so it stays correct even for
// conversations the user hasn't opened) and the conversation options ->
// delete-conversation-for-me flow.

export function initSidebar({ sidebarStateUrl, clearUrlTemplate, listEl }) {
    if (sidebarStateUrl) {
        const poller = createPoller(
            (signal) => get(sidebarStateUrl, { signal }),
            (data) => applyBadges(data),
            { intervalMs: 15000, maxIntervalMs: 60000 },
        );
        poller.start();
    }

    function applyBadges(data) {
        data.groups.forEach((group) => {
            const groupEl = listEl.querySelector(`[data-participant-id="${group.participant_id}"]`);
            if (!groupEl) return; // a brand-new conversation partner: picked up on next full page load
            const summary = qs('summary', groupEl);
            summary.classList.toggle('has-unread', group.unread_count > 0);
            let badge = qs('.conversation-unread-badge', summary);
            if (group.unread_count > 0) {
                if (!badge) {
                    badge = document.createElement('span');
                    badge.className = 'conversation-unread-badge';
                    summary.insertBefore(badge, summary.querySelector('.bi-chevron-down'));
                }
                badge.textContent = group.unread_count;
            } else {
                badge?.remove();
            }

            group.conversations.forEach((conversation) => {
                const row = groupEl.querySelector(`[data-conversation-id="${conversation.id}"]`);
                row?.classList.toggle('has-unread', conversation.unread_count > 0);
            });
        });
    }

    // ---- conversation options: delete conversation ---------------------
    const conversationActionsDialog = qs('#conversation-actions-dialog');
    const clearDialog = qs('#conversation-clear-dialog');
    let activeConversationId = null;

    on(document, 'click', '[data-conversation-options]', (evt, target) => {
        activeConversationId = target.dataset.conversationOptions;
        openDialog(conversationActionsDialog);
    });
    qs('[data-action-cancel-conversation]', conversationActionsDialog)?.addEventListener('click', () => closeDialog(conversationActionsDialog));
    qs('[data-action-clear-conversation]', conversationActionsDialog)?.addEventListener('click', async () => {
        closeDialog(conversationActionsDialog);
        const confirmed = await confirmDialog(clearDialog, '[data-clear-confirm]');
        if (!confirmed) return;
        const url = clearUrlTemplate.replace('/0/', `/${activeConversationId}/`);
        try {
            const result = await postForm(url, new FormData());
            window.location.href = result.redirect;
        } catch { /* leave the conversation visible; user can retry */ }
    });
    qs('[data-clear-cancel]', clearDialog)?.addEventListener('click', () => closeDialog(clearDialog));
}
