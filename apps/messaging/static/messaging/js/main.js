import { qs } from './dom.js';
import { get } from './api.js';
import { createPoller } from './polling.js';
import { initLightbox } from './lightbox.js';
import { initConversationSearch, initMessageSearch } from './search.js';
import { initSidebar } from './sidebar.js';
import { initAttachments } from './attachments.js';
import { initComposer } from './composer.js';
import { initThread } from './thread.js';
import { initTyping } from './typing.js';
import { initRead } from './read.js';
import { initLinkPreviews } from './link-previews.js';
import { initSharedContent } from './shared.js';

function initPageChrome() {
    // Small, page-level toggles that don't need their own module.
    const detailsToggle = qs('#messaging-details-toggle');
    const detailsPanel = qs('#messaging-details');
    detailsToggle?.addEventListener('click', () => {
        const isOpen = !detailsPanel.hidden;
        detailsPanel.hidden = isOpen;
        detailsToggle.setAttribute('aria-expanded', String(!isOpen));
    });
    qs('.messaging-details-close')?.addEventListener('click', () => {
        detailsPanel.hidden = true;
        detailsToggle?.setAttribute('aria-expanded', 'false');
    });

    qs('.messaging-mobile-back')?.addEventListener('click', () => {
        document.querySelector('.messaging-page').classList.remove('messaging-page-chat-open');
    });
}

function initSidebarFeatures() {
    const layout = qs('.messaging-layout');
    if (!layout) return;
    initSidebar({
        sidebarStateUrl: layout.dataset.conversationSidebarStateUrl,
        clearUrlTemplate: layout.dataset.clearConversationUrlTemplate,
        listEl: qs('#conversation-list'),
    });
    initConversationSearch({
        input: qs('#message-search'),
        resultsEl: qs('#conversation-search-results'),
        searchUrl: layout.dataset.conversationSearchUrl,
        listEl: qs('#conversation-list'),
    });
}

function initConversationFeatures() {
    const threadEl = qs('.messaging-thread');
    if (!threadEl) return; // no conversation open (the welcome screen)

    const urls = {
        pollUrl: threadEl.dataset.pollUrl,
        readUrl: threadEl.dataset.readUrl,
        typingUrl: threadEl.dataset.typingUrl,
        linksUrl: threadEl.dataset.linksUrl,
        linkPreviewUrl: threadEl.dataset.linkPreviewUrl,
        deleteUrlTemplate: threadEl.dataset.deleteUrlTemplate,
        editUrlTemplate: threadEl.dataset.editUrlTemplate,
        historyUrlTemplate: threadEl.dataset.historyUrlTemplate,
    };

    const form = qs('.messaging-compose-form');
    const textarea = qs('#id_body', form) || qs('textarea', form);

    const attachments = initAttachments({
        form,
        fileInput: qs('#message-attachment'),
        mediaInput: qs('#message-media-attachment'),
        toggleButton: qs('#messaging-attachment-toggle'),
        menu: qs('#messaging-attachment-menu'),
        previewEl: qs('#messaging-attachment-preview'),
        warningEl: qs('#messaging-attachment-warning'),
        maxSizeBytes: Number(form.dataset.maxAttachmentSize) || 10 * 1024 * 1024,
    });

    const thread = initThread({
        threadEl,
        urls,
        onEditRequested: (id, body) => composer.startEdit(id, body, urls.editUrlTemplate),
        onReplyRequested: (id, row) => composer.startReply(id, row),
        onMessagesChanged: () => shared.refresh(),
    });

    const composer = initComposer({
        form,
        textarea,
        replyToInput: qs('#messaging-reply-to-message-id'),
        sendUrl: window.location.pathname, // the conversation detail URL also accepts POST
        attachments,
        onSent: (messages) => {
            thread.insertNew(messages);
            lastMessageId = Math.max(lastMessageId, ...messages.map((m) => m.id));
        },
    });

    const typing = initTyping({
        typingUrl: urls.typingUrl,
        textarea,
        indicatorEl: qs('.messaging-typing'),
    });

    const read = initRead({ readUrl: urls.readUrl });

    const linkPreviews = initLinkPreviews({ container: qs('#messaging-details'), previewUrl: urls.linkPreviewUrl });
    const shared = initSharedContent({
        panel: qs('#messaging-details'),
        sharedUrl: threadEl.dataset.sharedUrl,
        onRendered: linkPreviews.enrich,
    });
    
    initMessageSearch({
        toggleButton: qs('#messaging-message-search-toggle'),
        panel: qs('#messaging-message-search-panel'),
        headerEl: qs('#messaging-message-search-header'),
        input: qs('#messaging-message-search-input'),
        statusEl: qs('#messaging-message-search-status'),
        resultsEl: qs('#messaging-message-search-results'),
        prevButton: qs('#messaging-message-search-previous'),
        nextButton: qs('#messaging-message-search-next'),
        counterEl: qs('#messaging-message-search-counter'),
        closeButton: qs('#messaging-message-search-close'),
        searchUrl: qs('#messaging-message-search-panel').dataset.searchUrl,
        onJumpTo: (id) => {
            const row = threadEl.querySelector(`[data-message-id="${id}"]`);
            row?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        },
    });

    // ---- polling: one endpoint for new + changed messages, typing, seen --
    let lastMessageId = Number(threadEl.dataset.lastMessageId) || 0;
    let since = threadEl.dataset.serverTime || '';

    const poller = createPoller(
        (signal) => get(`${urls.pollUrl}?after=${lastMessageId}&since=${encodeURIComponent(since)}`, { signal }),
        (data) => {
            since = data.server_time;
            if (data.new.length) {
                thread.insertNew(data.new);
                lastMessageId = Math.max(lastMessageId, ...data.new.map((m) => m.id));
                read.markRead();
            }
            if (data.changed.length) thread.replaceExisting(data.changed);
            typing.setOtherTyping(data.other_is_typing);
        },
        { intervalMs: 3000, maxIntervalMs: 15000 },
    );
    poller.start();
}

document.addEventListener('DOMContentLoaded', () => {
    initPageChrome();
    initSidebarFeatures();
    initConversationFeatures();
    initLightbox();
});
