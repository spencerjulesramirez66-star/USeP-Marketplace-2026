import { qs, qsa, on } from './dom.js';
import { get, postForm } from './api.js';
import { openDialog, closeDialog, confirmDialog } from './dialogs.js';

// Owns the message list DOM: inserting new messages, replacing edited/
// deleted ones, scrolling, time dividers, the typing indicator, and the
// per-message action sheet (reply / copy / edit / unsend) and its history
// dialog. Sending itself lives in composer.js; this module renders the
// result.

const TIME_GAP_MINUTES = 10; // show a time divider when messages are further apart than this

function formatDivider(date) {
    const time = date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    const sameYear = date.getFullYear() === new Date().getFullYear();
    const day = date.toLocaleDateString([], {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        ...(sameYear ? {} : { year: 'numeric' }),
    });
    return `${day}, ${time}`;
}

function template(html) {
    const wrapper = document.createElement('div');
    wrapper.innerHTML = html.trim();
    return wrapper.firstElementChild;
}

export function initThread({ threadEl, urls, onEditRequested, onReplyRequested, onMessagesChanged }) {
    const bottomMarker = qs('.messaging-thread-bottom', threadEl);
    const actionsDialog = qs('#messaging-actions-dialog');
    const unsendDialog = qs('#messaging-unsend-dialog');
    let activeMessageId = null;
    let userIsNearBottom = true;

    threadEl.addEventListener('scroll', () => {
        const distanceFromBottom = threadEl.scrollHeight - threadEl.scrollTop - threadEl.clientHeight;
        userIsNearBottom = distanceFromBottom < 120;
    });

    function scrollToBottom(behavior = 'auto') {
        bottomMarker.scrollIntoView({ behavior, block: 'end' });
    }

    // ---- time dividers (one label per gap, like Messenger) -------------
    function refreshTimeDividers() {
        qsa('.messaging-time-divider', threadEl).forEach((el) => el.remove());
        let previous = null;
        qsa('[data-message-id]', threadEl).forEach((row) => {
            const stamp = row.dataset.createdAt || qs('time[datetime]', row)?.getAttribute('datetime');
            if (!stamp) return;
            const sentAt = new Date(stamp);
            if (Number.isNaN(sentAt.getTime())) return;
            if (!previous || sentAt - previous > TIME_GAP_MINUTES * 60000) {
                const divider = document.createElement('div');
                divider.className = 'messaging-time-divider';
                divider.textContent = formatDivider(sentAt);
                row.before(divider);
            }
            previous = sentAt;
        });
    }

    refreshTimeDividers();
    scrollToBottom();

    function upsertMessage(id, html) {
        const existing = threadEl.querySelector(`[data-message-id="${id}"]`);
        const node = template(html);
        if (existing) {
            existing.replaceWith(node);
        } else {
            threadEl.insertBefore(node, bottomMarker);
        }
        return node;
    }

    function insertNew(messages) {
        if (!messages.length) return;
        messages.forEach((m) => upsertMessage(m.id, m.html));
        refreshTimeDividers();
        onMessagesChanged?.();
        if (userIsNearBottom) scrollToBottom('smooth');
    }

    function replaceExisting(messages) {
        messages.forEach((m) => upsertMessage(m.id, m.html));
        refreshTimeDividers();
        onMessagesChanged?.();
    }

    function updateTyping(isTyping) {
        const indicator = qs('.messaging-typing', threadEl.parentElement.querySelector('.messaging-typing-area') || document);
        if (indicator) indicator.hidden = !isTyping;
    }

    // ---- reply-quote jump -------------------------------------------------
    on(threadEl, 'click', '[data-reply-jump]', (evt, target) => {
        const targetId = target.dataset.replyJump;
        const targetRow = threadEl.querySelector(`[data-message-id="${targetId}"]`);
        if (!targetRow) return;
        targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
        targetRow.classList.add('messaging-highlight');
        setTimeout(() => targetRow.classList.remove('messaging-highlight'), 1500);
    });

    // ---- reply button -------------------------------------------------
    on(threadEl, 'click', '[data-reply-message]', (evt, target) => {
        const id = target.dataset.replyMessage;
        const row = target.closest('[data-message-id]');
        onReplyRequested(id, row);
    });

    // ---- message options action sheet ---------------------------------
    on(threadEl, 'click', '[data-message-options]', (evt, target) => {
        activeMessageId = target.dataset.messageOptions;
        const hasBody = target.dataset.messageHasBody === 'true';
        qs('[data-action-edit]', actionsDialog).hidden = !hasBody;
        openDialog(actionsDialog);
    });

    qs('[data-action-cancel]', actionsDialog)?.addEventListener('click', () => closeDialog(actionsDialog));

    qs('[data-action-copy]', actionsDialog)?.addEventListener('click', () => {
        const row = threadEl.querySelector(`[data-message-id="${activeMessageId}"]`);
        const text = row?.querySelector('.messaging-bubble p')?.textContent || '';
        navigator.clipboard?.writeText(text).catch(() => {});
        closeDialog(actionsDialog);
    });

    qs('[data-action-reply]', actionsDialog)?.addEventListener('click', () => {
        const row = threadEl.querySelector(`[data-message-id="${activeMessageId}"]`);
        closeDialog(actionsDialog);
        onReplyRequested(activeMessageId, row);
    });

    qs('[data-action-edit]', actionsDialog)?.addEventListener('click', () => {
        const row = threadEl.querySelector(`[data-message-id="${activeMessageId}"]`);
        const body = row?.querySelector('.messaging-bubble p')?.textContent || '';
        closeDialog(actionsDialog);
        onEditRequested(activeMessageId, body);
    });

    qs('[data-action-unsend]', actionsDialog)?.addEventListener('click', async () => {
        closeDialog(actionsDialog);
        const confirmed = await confirmDialog(unsendDialog, '.messaging-unsend-confirm');
        if (!confirmed) return;
        try {
            const url = urls.deleteUrlTemplate.replace('/0/', `/${activeMessageId}/`);
            const result = await postForm(url, new FormData());
            replaceExisting([result]);
        } catch { /* the message stays as-is; user can retry */ }
    });

    // ---- edited badge -> history dialog --------------------------------
    on(threadEl, 'click', '[data-history-message]', async (evt, target) => {
        const id = target.dataset.historyMessage;
        const url = urls.historyUrlTemplate.replace('/0/', `/${id}/`);
        try {
            const data = await get(url);
            alert(
                data.revisions.map((r) => `Earlier: ${r.body}`).concat(`Now: ${data.current.body}`).join('\n\n'),
            ); // minimal, dependency-free history viewer
        } catch { /* ignore */ }
    });

    return { insertNew, replaceExisting, updateTyping, scrollToBottom };
}