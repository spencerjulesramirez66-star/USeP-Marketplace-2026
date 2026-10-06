/* Purchase verification page.
 *
 * Client-side checks are a convenience only. The server re-validates the
 * schedule window, overlap, quantity and the payment proof.
 * Needs FullCalendar (global build) for the drag calendar; without it the
 * manual date/time fields still work.
 */
(function () {
    'use strict';

    const root = document.getElementById('pv-root');
    if (!root) return;

    const $ = (selector, ctx = document) => ctx.querySelector(selector);
    const $$ = (selector, ctx = document) => Array.from(ctx.querySelectorAll(selector));

    // ------------------------------------------------------------- config
    const toInt = (value, fallback) => {
        const n = parseInt(value, 10);
        return Number.isNaN(n) ? fallback : n;
    };

    const cfg = {
        openHour: toInt(root.dataset.openHour, 7),
        closeHour: toInt(root.dataset.closeHour, 18),
        isService: root.dataset.isService === 'true',
        unitPrice: parseFloat(root.dataset.unitPrice) || 0,
        maxQty: root.dataset.maxQuantity ? toInt(root.dataset.maxQuantity, null) : null,
        maxBytes: toInt(root.dataset.maxBytes, 10 * 1024 * 1024),
        minMinutes: 15,
        maxMinutes: 240,
        defaultMinutes: 60,
    };

    const PROOF_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // ------------------------------------------------------------ elements
    const form = $('#pv-form');
    const alertEl = $('#pv-alert');
    const startInput = $('#pv-scheduled-start');
    const endInput = $('#pv-scheduled-end');
    const summaryEl = $('#pv-slot-summary');
    const summaryText = $('#pv-slot-text');
    const clearBtn = $('#pv-slot-clear');
    const railWhen = $('#pv-rail-when');
    const manualDate = $('#pv-manual-date');
    const manualTime = $('#pv-manual-time');
    const manualDuration = $('#pv-manual-duration');
    const manualError = $('#pv-manual-error');
    const qtyInput = $('#pv-quantity');

    // ------------------------------------------------------------- helpers
    const pad = (n) => String(n).padStart(2, '0');

    /** "2026-10-08T14:30": what the server's DateTimeField expects (local time). */
    const toLocalString = (d) =>
        `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;

    const dateOnly = (d) => toLocalString(d).slice(0, 10);
    const minutesOfDay = (d) => d.getHours() * 60 + d.getMinutes();
    const sameDay = (a, b) => dateOnly(a) === dateOnly(b);
    const startOfToday = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; };

    const hourLabel = (hour) => {
        const h = hour % 12 === 0 ? 12 : hour % 12;
        return `${h} ${hour < 12 ? 'AM' : 'PM'}`;
    };
    const timeLabel = (d) => d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
    const dayLabel = (d) => d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });

    const durationLabel = (minutes) => {
        if (minutes < 60) return `${minutes} min`;
        const h = Math.floor(minutes / 60);
        const m = minutes % 60;
        return m ? `${h} hr ${m} min` : `${h} hr`;
    };

    const money = (amount) =>
        '\u20b1' + amount.toLocaleString('en-PH', {
            minimumFractionDigits: Number.isInteger(amount) ? 0 : 2,
            maximumFractionDigits: 2,
        });

    const formatBytes = (bytes) => {
        if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    function showAlert(message) {
        alertEl.textContent = message;
        alertEl.hidden = false;
        alertEl.focus({ preventScroll: true });
        alertEl.scrollIntoView({ block: 'center', behavior: reduceMotion ? 'auto' : 'smooth' });
    }

    function clearAlert() {
        alertEl.hidden = true;
        alertEl.textContent = '';
    }

    // -------------------------------------------------------- busy slots
    const busy = (() => {
        try {
            return JSON.parse(root.dataset.busySlots || '[]')
                .map((b) => ({ start: new Date(b.start), end: new Date(b.end) }));
        } catch (e) {
            return [];
        }
    })();

    /** Returns '' when the slot is bookable, otherwise a human-readable reason. */
    function slotProblem(start, end) {
        if (!(start instanceof Date) || !(end instanceof Date) || isNaN(start) || isNaN(end)) {
            return 'Pick a day and time.';
        }
        if (!sameDay(start, end)) return 'A slot has to start and end on the same day.';
        const minutes = (end - start) / 60000;
        if (minutes < cfg.minMinutes) return `Pick at least ${cfg.minMinutes} minutes.`;
        if (minutes > cfg.maxMinutes) return `Pick at most ${cfg.maxMinutes / 60} hours.`;
        if (minutesOfDay(start) < cfg.openHour * 60 || minutesOfDay(end) > cfg.closeHour * 60) {
            return `Choose a time between ${hourLabel(cfg.openHour)} and ${hourLabel(cfg.closeHour)}.`;
        }
        if (start < new Date()) return 'That time has already passed.';
        if (busy.some((b) => start < b.end && end > b.start)) return 'The seller already has something booked then.';
        return '';
    }

    // ------------------------------------------------------ current slot
    let calendar = null;
    let pickupEvent = null;

    function updateSummary(start, end) {
        if (!start) {
            summaryEl.dataset.state = 'empty';
            summaryText.textContent = 'No time picked yet.';
            clearBtn.hidden = true;
            railWhen.textContent = 'Not picked';
            railWhen.dataset.empty = 'true';
            return;
        }
        const minutes = Math.round((end - start) / 60000);
        const text = `${dayLabel(start)}, ${timeLabel(start)} to ${timeLabel(end)} (${durationLabel(minutes)})`;
        summaryEl.dataset.state = 'set';
        summaryText.textContent = text;
        clearBtn.hidden = false;
        railWhen.textContent = `${dayLabel(start)}, ${timeLabel(start)}`;
        railWhen.dataset.empty = 'false';
    }

    function ensureOption(select, value, label) {
        if (!$(`option[value="${value}"]`, select)) {
            const option = new Option(label, value);
            select.add(option);
            const sorted = Array.from(select.options).sort((a, b) => Number(a.value) - Number(b.value));
            sorted.forEach((o) => select.add(o));
        }
    }

    function syncManualFields(start, end) {
        manualDate.value = dateOnly(start);
        manualTime.value = `${pad(start.getHours())}:${pad(start.getMinutes())}`;
        const minutes = Math.round((end - start) / 60000);
        ensureOption(manualDuration, String(minutes), durationLabel(minutes));
        manualDuration.value = String(minutes);
    }

    /** Single source of truth: store the slot, mirror it everywhere. */
    function applySlot(start, end, source) {
        startInput.value = toLocalString(start);
        endInput.value = toLocalString(end);
        updateSummary(start, end);
        if (source !== 'manual') syncManualFields(start, end);
        manualError.hidden = true;
        clearAlert();
    }

    function setPickup(start, end, source) {
        if (calendar) {
            if (pickupEvent) pickupEvent.remove();
            pickupEvent = calendar.addEvent({
                id: 'pickup',
                title: cfg.isService ? 'Your appointment' : 'Your meetup',
                start,
                end,
                editable: true,
                classNames: ['pv-pickup'],
            });
            calendar.unselect();
        }
        applySlot(start, end, source);
    }

    function clearSlot() {
        if (pickupEvent) { pickupEvent.remove(); pickupEvent = null; }
        startInput.value = '';
        endInput.value = '';
        updateSummary(null);
    }

    clearBtn.addEventListener('click', clearSlot);

    // ---------------------------------------------------------- calendar
    function initCalendar() {
        const calEl = $('#pv-calendar');
        if (typeof FullCalendar === 'undefined') {
            $('#pv-cal-missing').hidden = false;
            $('#pv-manual').open = true;
            $$('[data-cal], [data-cal-view]').forEach((b) => { b.disabled = true; });
            return;
        }

        const narrow = window.matchMedia('(max-width: 720px)');
        const hh = (h) => `${pad(h)}:00:00`;

        calendar = new FullCalendar.Calendar(calEl, {
            initialView: narrow.matches ? 'timeGridDay' : 'timeGridWeek',
            headerToolbar: false,          // we render our own, Google-style
            height: 640,
            allDaySlot: false,
            nowIndicator: true,
            slotMinTime: hh(cfg.openHour),
            slotMaxTime: hh(cfg.closeHour),
            scrollTime: hh(cfg.openHour),
            slotDuration: '00:30:00',
            snapDuration: '00:15:00',
            slotLabelInterval: '01:00',
            slotLabelFormat: { hour: 'numeric', hour12: true },
            validRange: { start: startOfToday() },
            dayHeaderContent(arg) {
                const dow = arg.date.toLocaleDateString(undefined, { weekday: 'short' });
                return { html: `<span class="pv-dow">${dow}</span><span class="pv-dom">${arg.date.getDate()}</span>` };
            },

            // Dragging / long-press (touch) behaviour
            selectable: true,
            selectMirror: true,
            unselectAuto: false,
            selectOverlap: false,
            eventOverlap: false,
            eventResizableFromStart: true,
            longPressDelay: 200,
            selectLongPressDelay: 200,
            eventLongPressDelay: 200,

            selectAllow: (info) => !slotProblem(info.start, info.end),
            eventAllow: (dropInfo, draggedEvent) =>
                draggedEvent.id !== 'pickup' || !slotProblem(dropInfo.start, dropInfo.end),

            select(info) {
                let { start, end } = info;
                // A plain tap selects one 30 min slot; like Google Calendar, give it a useful default length.
                if ((end - start) / 60000 === 30) {
                    const longer = new Date(start.getTime() + cfg.defaultMinutes * 60000);
                    if (!slotProblem(start, longer)) end = longer;
                }
                setPickup(start, end, 'calendar');
            },
            eventDrop: (info) => applySlot(info.event.start, info.event.end, 'calendar'),
            eventResize: (info) => applySlot(info.event.start, info.event.end, 'calendar'),

            events: busy.map((b) => ({
                start: b.start,
                end: b.end,
                title: 'Unavailable',
                editable: false,
                classNames: ['pv-busy'],
            })),

            eventContent(arg) {
                const wrap = document.createElement('div');
                wrap.className = 'pv-event';
                const title = document.createElement('strong');
                title.textContent = arg.event.title;
                wrap.appendChild(title);
                if (arg.event.id === 'pickup') {
                    const time = document.createElement('span');
                    time.textContent = `${timeLabel(arg.event.start)} to ${timeLabel(arg.event.end)}`;
                    wrap.appendChild(time);
                }
                return { domNodes: [wrap] };
            },

            datesSet(info) {
                $('#pv-cal-title').textContent = info.view.title;
                $('[data-cal="prev"]').disabled = info.start <= startOfToday();
                $$('[data-cal-view]').forEach((b) =>
                    b.setAttribute('aria-pressed', String(b.dataset.calView === info.view.type)));
            },
        });

        calendar.render();

        $$('[data-cal]').forEach((button) => {
            button.addEventListener('click', () => {
                const action = button.dataset.cal;
                if (action === 'today') calendar.today();
                else if (action === 'prev') calendar.prev();
                else if (action === 'next') calendar.next();
            });
        });
        $$('[data-cal-view]').forEach((button) => {
            button.addEventListener('click', () => calendar.changeView(button.dataset.calView));
        });
        narrow.addEventListener('change', (e) =>
            calendar.changeView(e.matches ? 'timeGridDay' : 'timeGridWeek'));
    }

    // ----------------------------------------------------- manual picker
    function initManualPicker() {
        manualDate.min = dateOnly(new Date());

        for (let m = cfg.openHour * 60; m < cfg.closeHour * 60; m += 15) {
            const value = `${pad(Math.floor(m / 60))}:${pad(m % 60)}`;
            const d = new Date(2000, 0, 1, Math.floor(m / 60), m % 60);
            manualTime.add(new Option(timeLabel(d), value));
        }

        const onChange = () => {
            if (!manualDate.value || !manualTime.value) return;
            const start = new Date(`${manualDate.value}T${manualTime.value}:00`);
            const end = new Date(start.getTime() + Number(manualDuration.value) * 60000);
            const problem = slotProblem(start, end);
            if (problem) {
                manualError.textContent = problem;
                manualError.hidden = false;
                return;
            }
            setPickup(start, end, 'manual');
            if (calendar) calendar.gotoDate(start);
        };
        [manualDate, manualTime, manualDuration].forEach((el) => el.addEventListener('change', onChange));
    }

    // ---------------------------------------------------------- quantity
    function currentQuantity() {
        if (cfg.isService || !qtyInput) return 1;
        return parseInt(qtyInput.value, 10);
    }

    function updateTotals() {
        const qty = currentQuantity();
        const safeQty = Number.isNaN(qty) || qty < 1 ? 1 : qty;
        $$('[data-pv-total]').forEach((el) => { el.textContent = money(cfg.unitPrice * safeQty); });
        $$('[data-pv-qty-label]').forEach((el) => { el.textContent = String(safeQty); });
    }

    function initQuantity() {
        if (cfg.isService || !qtyInput) { updateTotals(); return; }
        const clamp = (n) => {
            let value = Number.isNaN(n) || n < 1 ? 1 : n;
            if (cfg.maxQty !== null) value = Math.min(value, cfg.maxQty);
            return value;
        };
        $('#pv-qty-minus').addEventListener('click', () => {
            qtyInput.value = clamp(currentQuantity() - 1);
            updateTotals();
        });
        $('#pv-qty-plus').addEventListener('click', () => {
            qtyInput.value = clamp((Number.isNaN(currentQuantity()) ? 0 : currentQuantity()) + 1);
            updateTotals();
        });
        qtyInput.addEventListener('input', updateTotals);
        qtyInput.addEventListener('blur', () => { qtyInput.value = clamp(currentQuantity()); updateTotals(); });
        updateTotals();
    }

    // ----------------------------------------------------------- payment
    const gcashPanel = $('#pv-gcash-panel');
    const cashPanel = $('#pv-cash-panel');
    const railPay = $('#pv-rail-pay');
    const methodInputs = $$('input[name="payment_method"]');
    const selectedMethod = () => (methodInputs.find((r) => r.checked) || {}).value || 'gcash';

    function updateMethod() {
        const method = selectedMethod();
        gcashPanel.hidden = method !== 'gcash';
        cashPanel.hidden = method !== 'cash';
        railPay.textContent = method === 'gcash' ? 'GCash' : 'Cash on hand';
    }
    methodInputs.forEach((r) => r.addEventListener('change', updateMethod));

    // ------------------------------------------------------ payment proof
    const proofInput = $('#pv-proof');
    const dropzone = $('#pv-dropzone');
    const proofPreview = $('#pv-proof-preview');
    const proofImg = $('#pv-proof-img');
    const proofName = $('#pv-proof-name');
    const proofSize = $('#pv-proof-size');
    const proofError = $('#pv-proof-error');
    let proofUrl = null;

    function proofProblem(file) {
        if (!PROOF_TYPES.includes(file.type)) return 'Upload a JPG, PNG or WebP screenshot.';
        if (file.size > cfg.maxBytes) return `That file is ${formatBytes(file.size)}. Screenshots must be ${formatBytes(cfg.maxBytes)} or smaller.`;
        return '';
    }

    function clearProof() {
        if (proofUrl) { URL.revokeObjectURL(proofUrl); proofUrl = null; }
        proofInput.value = '';
        proofPreview.hidden = true;
        dropzone.hidden = false;
        proofImg.removeAttribute('src');
    }

    function setProof(file) {
        proofError.hidden = true;
        const problem = proofProblem(file);
        if (problem) {
            clearProof();
            proofError.textContent = problem;
            proofError.hidden = false;
            return;
        }
        if (proofUrl) URL.revokeObjectURL(proofUrl);
        proofUrl = URL.createObjectURL(file);
        proofImg.src = proofUrl;
        proofName.textContent = file.name;
        proofSize.textContent = formatBytes(file.size);
        proofPreview.hidden = false;
        dropzone.hidden = true;
        clearAlert();
    }

    function initProof() {
        proofInput.addEventListener('change', () => {
            if (proofInput.files[0]) setProof(proofInput.files[0]);
        });
        $('#pv-proof-remove').addEventListener('click', () => { clearProof(); proofInput.focus(); });

        ['dragenter', 'dragover'].forEach((type) => dropzone.addEventListener(type, (e) => {
            e.preventDefault();
            dropzone.dataset.dragging = 'true';
        }));
        ['dragleave', 'drop'].forEach((type) => dropzone.addEventListener(type, (e) => {
            e.preventDefault();
            dropzone.dataset.dragging = 'false';
        }));
        dropzone.addEventListener('drop', (e) => {
            const file = e.dataTransfer.files[0];
            if (!file) return;
            const transfer = new DataTransfer();
            transfer.items.add(file);
            proofInput.files = transfer.files;
            setProof(file);
        });
    }

    // ------------------------------------------------------------ submit
    function firstProblem() {
        if (!cfg.isService) {
            const qty = currentQuantity();
            if (Number.isNaN(qty) || qty < 1) return 'Enter how many you want.';
            if (cfg.maxQty !== null && qty > cfg.maxQty) return `Only ${cfg.maxQty} available.`;
        }
        if (!startInput.value || !endInput.value) return 'Pick a day and time on the calendar.';
        const slot = slotProblem(new Date(startInput.value), new Date(endInput.value));
        if (slot) return slot;
        if (selectedMethod() === 'gcash' && !(proofInput.files && proofInput.files[0])) {
            return 'Upload your GCash payment screenshot, or switch to cash on hand.';
        }
        return '';
    }

    function setBusy(isBusy) {
        $$('[data-pv-submit]').forEach((b) => {
            b.disabled = isBusy;
            b.textContent = isBusy ? 'Sending\u2026' : 'Send to seller';
        });
    }

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        clearAlert();

        const problem = firstProblem();
        if (problem) { showAlert(problem); return; }

        const data = new FormData(form);
        if (selectedMethod() === 'cash') {
            data.delete('payment_proof');
            data.delete('payment_reference');
        }

        setBusy(true);
        try {
            const response = await fetch(form.action || window.location.href, {
                method: 'POST',
                body: data,
                credentials: 'same-origin',
                headers: { 'X-Requested-With': 'XMLHttpRequest', Accept: 'application/json' },
            });
            const result = await response.json().catch(() => null);
            if (!response.ok || !result || !result.ok) {
                throw new Error((result && result.error) || 'Something went wrong. Please try again.');
            }
            $$('[data-pv-submit]').forEach((b) => { b.textContent = 'Sent'; });
            window.location.assign(result.redirect);
        } catch (error) {
            setBusy(false);
            showAlert(error.message);
        }
    });

    // -------------------------------------------------------------- boot
    initQuantity();
    initProof();
    initManualPicker();
    updateMethod();
    initCalendar();
})();