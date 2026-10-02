import { qs, escapeHtml } from './dom.js';
import { postForm, postFormWithProgress } from './api.js';

// The message input: autosize, reply/edit state, and submitting a new
// message or an edit. Delegates file handling to attachments.js and
// rendering of the result to thread.js (via the callbacks passed in).

function autosize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
}

export function initComposer({ form, textarea, replyToInput, sendUrl, onSent, attachments }) {
    const replyState = qs('#messaging-reply-state');
    const replyName = qs('#messaging-reply-name');
    const replyPreview = qs('#messaging-reply-preview');
    const replyThumb = qs('#messaging-reply-preview-thumb');
    const cancelReplyBtn = qs('#messaging-cancel-reply');

    const editState = qs('#messaging-edit-state');
    const cancelEditBtn = qs('#messaging-cancel-edit');

    let editingMessageId = null;
    let editUrlTemplate = null;

    textarea.addEventListener('input', () => autosize(textarea));
    autosize(textarea);

    function startReply(messageId, row) {
        cancelEdit();
        replyToInput.value = messageId;
        replyState.hidden = false;
        const senderName = row?.dataset.senderName || 'this message';
        const bubbleText = row?.querySelector('.messaging-bubble p')?.textContent;
        const thumb = row?.querySelector('.messaging-attachment-bubble img');
        replyName.textContent = `Replying to ${senderName}`;
        replyPreview.textContent = bubbleText || (thumb ? 'Photo' : 'Attachment');
        if (thumb) { replyThumb.src = thumb.src; replyThumb.hidden = false; } else { replyThumb.hidden = true; }
        textarea.focus();
    }

    function cancelReply() {
        replyToInput.value = '';
        replyState.hidden = true;
    }

    function startEdit(messageId, body, urlTemplate) {
        cancelReply();
        editingMessageId = messageId;
        editUrlTemplate = urlTemplate;
        editState.hidden = false;
        textarea.value = body;
        autosize(textarea);
        textarea.focus();
    }

    function cancelEdit() {
        editingMessageId = null;
        editState.hidden = true;
        textarea.value = '';
        autosize(textarea);
    }

    cancelReplyBtn.addEventListener('click', cancelReply);
    cancelEditBtn.addEventListener('click', cancelEdit);

    form.addEventListener('submit', async (evt) => {
        evt.preventDefault();
        const body = textarea.value.trim();
        if (!body && !attachments.hasFiles()) return;

        if (editingMessageId) {
            const url = editUrlTemplate.replace('/0/', `/${editingMessageId}/`);
            try {
                const result = await postForm(url, new URLSearchParams({ body }));
                onSent([result]);
                cancelEdit();
            } catch (error) {
                alert(error.message);
            }
            return;
        }

        const formData = new FormData();
        formData.append('body', body);
        if (replyToInput.value) formData.append('reply_to_message_id', replyToInput.value);
        attachments.getFiles().forEach((file) => formData.append('attachments', file));

        textarea.value = '';
        autosize(textarea);
        const hadReply = Boolean(replyToInput.value);
        cancelReply();

        try {
            const result = await postFormWithProgress(sendUrl, formData);
            attachments.reset();
            onSent([result]);
        } catch (error) {
            textarea.value = body; // give the text back so the user doesn't lose it
            if (hadReply) replyToInput.value = '';
            alert(`Message not sent: ${error.message}`);
        }
    });

    return { startReply, startEdit };
}
