import { postForm } from './api.js';

// Sends this user's typing state (throttled + auto-stop) and shows/hides the
// "X is typing" indicator based on what polling.js reports.

const SEND_THROTTLE_MS = 2000;
const AUTO_STOP_MS = 4000;

export function initTyping({ typingUrl, textarea, indicatorEl }) {
    if (!typingUrl || !textarea) return { setOtherTyping() {} };

    const sessionId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
    let sequence = 0;
    let lastSentAt = 0;
    let stopTimer = null;

    function send(isTyping) {
        sequence += 1;
        const body = new FormData();
        body.append('is_typing', isTyping ? 'true' : 'false');
        body.append('session_id', sessionId);
        body.append('sequence', String(sequence));
        postForm(typingUrl, body).catch(() => {});
    }

    textarea.addEventListener('input', () => {
        const now = Date.now();
        clearTimeout(stopTimer);
        if (now - lastSentAt > SEND_THROTTLE_MS) {
            lastSentAt = now;
            send(true);
        }
        stopTimer = setTimeout(() => send(false), AUTO_STOP_MS);
    });

    textarea.addEventListener('blur', () => { clearTimeout(stopTimer); send(false); });

    function setOtherTyping(isTyping) {
        if (!indicatorEl) return;
        indicatorEl.hidden = !isTyping;
    }

    return { setOtherTyping };
}
