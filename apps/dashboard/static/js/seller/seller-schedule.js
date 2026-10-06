/**
 * Order schedule: weekly calendar, reschedule negotiation, delivery.
 *
 * The server decides what each person may do (can_propose, can_accept, ...),
 * so this file only draws the data and sends the actions back.
 */
(() => {
  'use strict';

  const root = document.getElementById('sched');
  if (!root) return;

  // ---------------------------------------------------------------- config

  const OPEN_HOUR = Number(root.dataset.open);
  const CLOSE_HOUR = Number(root.dataset.close);
  const HOUR_PX = 56;            // height of one hour on the grid
  const SNAP_HOURS = 0.25;       // dragging snaps to 15 minutes
  const POLL_MS = 30000;
  const HIDDEN_KEY = 'sched-hidden-statuses';

  const STATUS_LABELS = {
    submitted: 'Waiting for seller',
    proposed: 'New time proposed',
    confirmed: 'Confirmed',
    completed: 'Delivered',
  };

  // One place to describe every action the panel can send.
  const ACTIONS = {
    confirm: { done: 'Order confirmed.' },
    accept: { done: 'Time accepted. The order is confirmed.' },
    propose: { done: 'New time sent. Waiting for a reply.' },
    deliver: {
      done: 'Delivered.',
      ask: (order) => order.is_service
        ? 'Mark this order as delivered?'
        : `Mark as delivered and subtract ${order.quantity} from stock?`,
    },
  };

  root.style.setProperty('--row-height', `${HOUR_PX}px`);

  // ----------------------------------------------------------------- state

  const state = {
    orders: [],
    fingerprint: '',
    weekStart: startOfWeek(new Date()),
    selectedId: null,
    hiddenStatuses: new Set(readJson(HIDDEN_KEY, [])),
    firstRender: true,
    focusId: root.dataset.focus,      // order to open from a chat link
    justDragged: false,
  };

  const $ = (id) => document.getElementById(id);
  const el = {
    calendar: $('s-cal'),
    panel: $('s-panel'),
    detail: $('s-detail'),
    todo: $('s-todo'),
    count: $('s-count'),
    range: $('s-range'),
    toast: $('s-toast'),
  };

  const findOrder = (id) => state.orders.find((order) => order.id === id);

  // --------------------------------------------------------------- helpers

  function readJson(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
    catch { return fallback; }
  }

  function startOfWeek(date) {
    const day = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    day.setDate(day.getDate() - day.getDay());
    return day;
  }

  function addDays(date, count) {
    const next = new Date(date);
    next.setDate(next.getDate() + count);
    return next;
  }

  const isSameDay = (a, b) => a.toDateString() === b.toDateString();
  const hoursOf = (date) => date.getHours() + date.getMinutes() / 60;
  const formatTime = (date) => date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  const formatDate = (date) => date.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
  const weekDays = () => Array.from({ length: 7 }, (_, i) => addDays(state.weekStart, i));

  /** Value for <input type="datetime-local">, in local time. */
  function toInputValue(date) {
    const pad = (n) => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }

  function escapeHtml(text) {
    const entities = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
    return String(text ?? '').replace(/[&<>"']/g, (char) => entities[char]);
  }

  function csrfToken() {
    return (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
  }

  /** The window we are currently talking about: the proposal if there is one, else the booked slot. */
  function currentSlot(order) {
    return {
      start: new Date(order.proposed_start || order.start),
      end: new Date(order.proposed_end || order.end),
    };
  }

  let toastTimer;
  function showToast(message, isError = false) {
    el.toast.textContent = message;
    el.toast.className = `sched-toast${isError ? ' err' : ''}`;
    el.toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.toast.hidden = true; }, 4000);
  }

  // ------------------------------------------------------------------- api

  /** Fetch orders. Returns true when something changed since last time. */
  async function loadOrders() {
    const response = await fetch(root.dataset.eventsUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
    const { events } = await response.json();
    const fingerprint = JSON.stringify(events);
    if (fingerprint === state.fingerprint) return false;
    state.fingerprint = fingerprint;
    state.orders = events;
    return true;
  }

  async function sendAction(orderId, action, data = {}) {
    const response = await fetch(`${root.dataset.base}${orderId}/${action}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken(), 'X-Requested-With': 'XMLHttpRequest' },
      body: new URLSearchParams(data),
    });
    const result = await response.json().catch(() => ({ ok: false, error: 'Something went wrong. Try again.' }));
    if (!result.ok) showToast(result.error, true);
    return result.ok;
  }

  async function runAction(order, action, data) {
    const { done, ask } = ACTIONS[action];
    if (ask && !confirm(ask(order))) return;
    if (!(await sendAction(order.id, action, data))) return;
    showToast(done);
    await loadOrders();
    renderAll();
    showPanel(order.id);
  }

  // ------------------------------------------------------------ calendar

  /** Everything drawn on the grid: booked slots, plus a dashed block for each proposed slot. */
  function buildBlocks() {
    const blocks = [];
    for (const order of state.orders) {
      if (state.hiddenStatuses.has(order.status)) continue;
      blocks.push({ order, start: new Date(order.start), end: new Date(order.end), ghost: false });
      if (order.status === 'proposed' && order.proposed_start) {
        blocks.push({ order, start: new Date(order.proposed_start), end: new Date(order.proposed_end), ghost: true });
      }
    }
    return blocks;
  }

  /** Put overlapping blocks side by side. Returns the number of lanes used. */
  function assignLanes(dayBlocks) {
    const laneEnds = [];
    for (const block of dayBlocks) {
      let lane = laneEnds.findIndex((end) => end <= block.start);
      if (lane === -1) lane = laneEnds.length;
      laneEnds[lane] = block.end;
      block.lane = lane;
    }
    return Math.max(laneEnds.length, 1);
  }

  function blockHtml(block, laneCount) {
    const { order, start, end, ghost } = block;
    const top = Math.max(hoursOf(start) - OPEN_HOUR, 0) * HOUR_PX;
    const height = Math.max((hoursOf(end) - Math.max(hoursOf(start), OPEN_HOUR)) * HOUR_PX, 22);
    const classes = [
      'ev', `st-${order.status}`,
      ghost && 'ghost',
      order.id === state.selectedId && 'sel',
      !ghost && order.can_propose && 'draggable',
    ].filter(Boolean).join(' ');

    return `
      <button type="button" class="${classes}" data-id="${order.id}"
              style="top:${top}px; height:${height}px; left:${(block.lane * 100) / laneCount}%; width:calc(${100 / laneCount}% - 4px)">
        <b>${escapeHtml(order.title)}</b>
        ${formatTime(start)} - ${formatTime(end)}${ghost ? ' (proposed)' : ''}
      </button>`;
  }

  function columnHtml(day, blocks, now) {
    const dayBlocks = blocks.filter((block) => isSameDay(block.start, day)).sort((a, b) => a.start - b.start);
    const laneCount = assignLanes(dayBlocks);
    const isToday = isSameDay(day, now);
    const showNow = isToday && hoursOf(now) >= OPEN_HOUR && hoursOf(now) <= CLOSE_HOUR;

    return `
      <div class="cal-col${isToday ? ' today' : ''}" style="height:${(CLOSE_HOUR - OPEN_HOUR) * HOUR_PX}px">
        ${dayBlocks.map((block) => blockHtml(block, laneCount)).join('')}
        ${showNow ? `<div class="cal-now" style="top:${(hoursOf(now) - OPEN_HOUR) * HOUR_PX}px"></div>` : ''}
      </div>`;
  }

  function renderCalendar() {
    const days = weekDays();
    const now = new Date();
    const blocks = buildBlocks();
    const scrollTop = el.calendar.scrollTop;

    const longDate = { month: 'long', day: 'numeric' };
    el.range.textContent = `${days[0].toLocaleDateString([], longDate)} - ${days[6].toLocaleDateString([], { ...longDate, year: 'numeric' })}`;

    const header = days.map((day) => `
      <div class="${isSameDay(day, now) ? 'today' : ''}">
        ${day.toLocaleDateString([], { weekday: 'short' })}<b>${day.getDate()}</b>
      </div>`).join('');

    const hourLabels = Array.from({ length: CLOSE_HOUR - OPEN_HOUR }, (_, i) =>
      `<div>${new Date(2000, 0, 1, OPEN_HOUR + i).toLocaleTimeString([], { hour: 'numeric' })}</div>`).join('');

    const weekEnd = addDays(state.weekStart, 7);
    const hasOrdersThisWeek = blocks.some((block) => block.start >= state.weekStart && block.start < weekEnd);

    el.calendar.innerHTML = `
      <div class="cal-head"><div></div>${header}</div>
      <div class="cal-grid">
        <div class="cal-hours">${hourLabels}</div>
        ${days.map((day) => columnHtml(day, blocks, now)).join('')}
      </div>
      ${hasOrdersThisWeek ? '' : '<p class="cal-empty">No orders this week.</p>'}`;

    // Keep the scroll position; on the very first draw, start near the current time.
    el.calendar.scrollTop = state.firstRender
      ? Math.max((Math.min(hoursOf(now), CLOSE_HOUR) - OPEN_HOUR - 1.5) * HOUR_PX, 0)
      : scrollTop;
    state.firstRender = false;
  }

  // ------------------------------------------------------------ needs action

  function todoReason(order) {
    if (order.can_accept) return 'Review proposed time';
    if (order.can_deliver) return 'Mark delivered when done';
    return 'Confirm or change the time';
  }

  function renderTodo() {
    const todo = state.orders.filter((o) => o.can_accept || o.can_deliver || (o.role === 'seller' && o.status === 'submitted'));

    el.count.hidden = todo.length === 0;
    el.count.textContent = todo.length;
    document.title = `${todo.length ? `(${todo.length}) ` : ''}Order schedule | USeP Marketplace`;

    el.todo.innerHTML = todo.length
      ? todo.map((order) => `
          <li><button type="button" data-id="${order.id}">
            ${escapeHtml(order.title)}<small>${todoReason(order)}</small>
          </button></li>`).join('')
      : '<li class="empty">All caught up.</li>';
  }

  // ------------------------------------------------------------ details panel

  function detailsHtml(order) {
    const isSeller = order.role === 'seller';
    const start = new Date(order.start);
    const end = new Date(order.end);

    return `
      <h4>${escapeHtml(order.title)}</h4>
      <span class="pill st-${order.status}">${STATUS_LABELS[order.status]}</span>
      <dl>
        <dt>${isSeller ? 'Buyer' : 'Seller'}</dt><dd>${escapeHtml(order.with)}</dd>
        <dt>When</dt><dd>${formatDate(start)}, ${formatTime(start)} - ${formatTime(end)}</dd>
        ${order.is_service ? '' : `<dt>Quantity</dt><dd>${order.quantity}${isSeller ? ` (${order.stock} in stock)` : ''}</dd>`}
        <dt>Total</dt><dd>&#8369;${Number(order.total).toLocaleString()}${order.payment ? ` via ${escapeHtml(order.payment)}` : ''}</dd>
        ${order.buyer_note ? `<dt>Buyer note</dt><dd>${escapeHtml(order.buyer_note)}</dd>` : ''}
      </dl>`;
  }

  function proposalHtml(order) {
    if (order.status !== 'proposed') return '';
    const { start, end } = currentSlot(order);
    const title = order.can_accept ? 'New time proposed to you' : 'Waiting for a reply';
    return `
      <div class="callout">
        <b><i class="bi bi-calendar2-event"></i> ${title}</b><br>
        ${formatDate(start)}, ${formatTime(start)} - ${formatTime(end)}
        ${order.proposal_note ? `<br>Reason: ${escapeHtml(order.proposal_note)}` : ''}
      </div>`;
  }

  function proposalFormHtml(order) {
    const isSeller = order.role === 'seller';
    const { start, end } = currentSlot(order);
    return `
      <form id="s-form">
        <b>${order.can_accept ? 'Or suggest another time' : 'Change the time'}</b>
        <label>Start <input type="datetime-local" name="start" value="${toInputValue(start)}" required></label>
        <label>End <input type="datetime-local" name="end" value="${toInputValue(end)}" required></label>
        <label>${isSeller ? 'Reason (sent to the buyer)' : 'Note'}
          <textarea name="note" rows="2" maxlength="500"></textarea></label>
        <button class="btn btn-outline" type="submit">
          <i class="bi bi-send"></i> ${isSeller ? 'Send new time to buyer' : 'Send counter-offer'}
        </button>
      </form>`;
  }

  function actionButton(action, icon, label) {
    return `<div class="acts"><button class="btn btn-primary" type="button" data-do="${action}"><i class="bi ${icon}"></i> ${label}</button></div>`;
  }

  function panelHtml(order) {
    return [
      detailsHtml(order),
      proposalHtml(order),
      order.can_confirm ? actionButton('confirm', 'bi-check2-circle', 'Confirm order') : '',
      order.can_accept ? actionButton('accept', 'bi-check-lg', 'Accept new time') : '',
      order.can_propose ? proposalFormHtml(order) : '',
      order.can_deliver ? `${actionButton('deliver', 'bi-box-seam', 'Mark as delivered')}
        <small>${order.is_service ? 'Marks the service as done.' : `This subtracts ${order.quantity} from your stock.`}</small>` : '',
      `<div class="acts"><a class="btn btn-outline" href="${order.chat_url}"><i class="bi bi-chat-dots"></i> Open chat</a></div>`,
    ].join('');
  }

  function showPanel(orderId) {
    const order = findOrder(orderId);
    if (!order) return closePanel();
    state.selectedId = orderId;
    el.detail.innerHTML = panelHtml(order);
    el.panel.hidden = false;
    el.calendar.querySelectorAll('.ev').forEach((block) => {
      block.classList.toggle('sel', Number(block.dataset.id) === orderId);
    });
  }

  function closePanel() {
    state.selectedId = null;
    el.panel.hidden = true;
    renderCalendar();
  }

  /** True while the person is typing in the form, so a refresh must not wipe it. */
  const isEditingPanel = () =>
    el.detail.contains(document.activeElement) || Boolean(el.detail.querySelector('#s-form[data-dirty]'));

  // ------------------------------------------------------------- drag to move

  /** Drag an order to a new day or time. Nothing is sent; it fills in the proposal form. */
  function startDrag(down) {
    const block = down.target.closest('.ev.draggable');
    if (!block || down.button !== 0) return;

    const order = findOrder(Number(block.dataset.id));
    const columns = [...el.calendar.querySelectorAll('.cal-col')];
    const grabOffset = down.clientY - block.getBoundingClientRect().top;
    const { start, end } = currentSlot(order);
    const durationHours = (end - start) / 3600000;
    let isDragging = false;
    let drop = null;

    const onMove = (move) => {
      const distance = Math.hypot(move.clientX - down.clientX, move.clientY - down.clientY);
      if (!isDragging && distance < 6) return;
      isDragging = true;
      block.classList.add('dragging');

      const index = columns.findIndex((col) => {
        const rect = col.getBoundingClientRect();
        return move.clientX >= rect.left && move.clientX < rect.right;
      });
      if (index === -1) { drop = null; return; }

      const column = columns[index];
      const offsetPx = move.clientY - column.getBoundingClientRect().top - grabOffset;
      const snapped = Math.round((offsetPx / HOUR_PX + OPEN_HOUR) / SNAP_HOURS) * SNAP_HOURS;
      const hour = Math.min(Math.max(snapped, OPEN_HOUR), CLOSE_HOUR - durationHours);

      if (block.parentNode !== column) column.appendChild(block);
      Object.assign(block.style, { top: `${(hour - OPEN_HOUR) * HOUR_PX}px`, left: '0', width: 'calc(100% - 4px)' });
      drop = { dayIndex: index, hour };
    };

    const onUp = () => {
      document.removeEventListener('pointermove', onMove);
      document.removeEventListener('pointerup', onUp);
      if (!isDragging) return;

      state.justDragged = true;                       // swallow the click that follows a drag
      setTimeout(() => { state.justDragged = false; }, 0);

      if (!drop) return renderCalendar();             // dropped outside the grid: snap back

      const newStart = weekDays()[drop.dayIndex];
      newStart.setMinutes(Math.round(drop.hour * 60));
      renderCalendar();
      showPanel(order.id);
      fillProposalForm(newStart, new Date(newStart.getTime() + durationHours * 3600000));
    };

    document.addEventListener('pointermove', onMove);
    document.addEventListener('pointerup', onUp);
  }

  function fillProposalForm(start, end) {
    const form = $('s-form');
    if (!form) return;
    form.elements.start.value = toInputValue(start);
    form.elements.end.value = toInputValue(end);
    form.dataset.dirty = '1';
    form.classList.add('flash');
    form.elements.note.focus();
    showToast('New time filled in. Add a reason and send it.');
  }

  // ------------------------------------------------------------------ wiring

  function renderAll() {
    renderCalendar();
    renderTodo();
  }

  function goToWeekOf(order) {
    state.weekStart = startOfWeek(new Date(order.start));
    renderAll();
    showPanel(order.id);
  }

  function shiftWeek(days) {
    state.weekStart = days === 0 ? startOfWeek(new Date()) : addDays(state.weekStart, days);
    renderCalendar();
  }

  async function refresh() {
    if (!(await loadOrders())) return;               // nothing changed: leave the screen alone
    renderAll();
    if (state.selectedId && !isEditingPanel()) showPanel(state.selectedId);
  }

  // Calendar blocks: click to open, drag to move.
  el.calendar.addEventListener('click', (event) => {
    const block = event.target.closest('.ev');
    if (block && !state.justDragged) showPanel(Number(block.dataset.id));
  });
  el.calendar.addEventListener('pointerdown', startDrag);

  // "Needs action" list.
  el.todo.addEventListener('click', (event) => {
    const item = event.target.closest('button[data-id]');
    if (item) goToWeekOf(findOrder(Number(item.dataset.id)));
  });

  // Panel buttons and form.
  el.detail.addEventListener('click', (event) => {
    const button = event.target.closest('[data-do]');
    const order = findOrder(state.selectedId);
    if (button && order) runAction(order, button.dataset.do);
  });
  el.detail.addEventListener('input', (event) => {
    event.target.closest('form')?.setAttribute('data-dirty', '1');
  });
  el.detail.addEventListener('submit', (event) => {
    event.preventDefault();
    const order = findOrder(state.selectedId);
    if (order) runAction(order, 'propose', Object.fromEntries(new FormData(event.target)));
  });

  // Header controls.
  $('s-prev').addEventListener('click', () => shiftWeek(-7));
  $('s-next').addEventListener('click', () => shiftWeek(7));
  $('s-today').addEventListener('click', () => shiftWeek(0));
  $('s-close').addEventListener('click', closePanel);

  // Status filters (remembered between visits).
  document.querySelectorAll('#s-legend input').forEach((checkbox) => {
    checkbox.checked = !state.hiddenStatuses.has(checkbox.dataset.st);
    checkbox.addEventListener('change', () => {
      const status = checkbox.dataset.st;
      if (checkbox.checked) state.hiddenStatuses.delete(status); else state.hiddenStatuses.add(status);
      localStorage.setItem(HIDDEN_KEY, JSON.stringify([...state.hiddenStatuses]));
      renderCalendar();
    });
  });

  // Keyboard shortcuts: T today, arrows change week, Esc closes the panel.
  const SHORTCUTS = { t: 's-today', ArrowLeft: 's-prev', ArrowRight: 's-next' };
  document.addEventListener('keydown', (event) => {
    if (event.target.closest('input, textarea, select') || event.ctrlKey || event.metaKey) return;
    const target = SHORTCUTS[event.key.length === 1 ? event.key.toLowerCase() : event.key];
    if (target) $(target).click();
    else if (event.key === 'Escape' && !el.panel.hidden) closePanel();
  });

  // ------------------------------------------------------------------- start

  (async function init() {
    await loadOrders();
    renderAll();

    const linked = state.focusId && findOrder(Number(state.focusId));
    if (linked && linked.start) goToWeekOf(linked);

    // Pick up the other person's reply, but not while the tab is in the background.
    setInterval(() => { if (!document.hidden) refresh(); }, POLL_MS);
  })();
})();