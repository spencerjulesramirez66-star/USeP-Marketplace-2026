/* Accounts page: list, search, details drawer, create/edit form and status actions.
   Talks to the JSON endpoints in administration/account_views.py.

   Sections in this file:
     1. Setup and helpers
     2. List (search, filters, pagination)
     3. Details drawer
     4. Create / edit form
     5. Actions (suspend, delete, ...) with confirmation
     6. Start-up
*/
(() => {
    'use strict';

    // ------------------------------------------------------------------
    // 1. Setup and helpers
    // ------------------------------------------------------------------
    const root = document.getElementById('accounts-app');
    if (!root) return;

    const baseUrl = root.dataset.baseUrl;            // e.g. /administration/accounts/
    const csrfToken = root.dataset.csrf;
    const options = JSON.parse(document.getElementById('account-options').textContent);

    const state = { q: '', type: '', status: 'active', page: 1, requestId: 0, current: null };

    const $ = (selector) => root.querySelector(selector);

    const el = {
        list: $('#acct-list'), empty: $('#acct-empty'), emptyTitle: $('#acct-empty-title'), emptyText: $('#acct-empty-text'),
        pager: $('#acct-pager'), pagerInfo: $('#acct-pager-info'), prev: $('#acct-prev'), next: $('#acct-next'),
        search: $('#acct-search'), typeFilter: $('#acct-type-filter'), tabs: $('#acct-tabs'),
        drawer: $('#acct-drawer'), formDialog: $('#acct-form-dialog'), form: $('#acct-form'),
        confirm: $('#acct-confirm-dialog'),
    };

    /** Build an element without ever putting data into innerHTML. */
    function make(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function icon(name) {
        const node = make('i', `bi bi-${name}`);
        node.setAttribute('aria-hidden', 'true');
        return node;
    }

    function formatDate(iso) {
        return iso ? new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : '';
    }

    // Alerts reuse the markup of templates/.../messages.html, so the site's existing alert styles apply.
    // If your MESSAGE_TAGS differ (for example error -> "danger"), change them here.
    const ALERT_TAGS = { success: 'success', error: 'error' };
    const ALERT_SECONDS = 6;

    function alertContainer() {
        // An open modal <dialog> sits above the rest of the page, so the alert has to live inside it
        // or it would be hidden behind the dark backdrop.
        const dialog = [el.confirm, el.formDialog, el.drawer].find((d) => d.open);
        const parent = dialog || document.body;
        let container = dialog
            ? parent.querySelector(':scope > .messages-container')
            : document.querySelector('.messages-container');
        if (!container) {
            container = make('div', 'messages-container');
            parent.appendChild(container);
        }
        return container;
    }

    function toast(message, isError = false) {
        const alert = make('div', `alert alert-${isError ? ALERT_TAGS.error : ALERT_TAGS.success}`);
        alert.setAttribute('role', 'alert');

        const dismiss = make('button', 'alert-dismiss', 'Dismiss');
        dismiss.type = 'button';
        const content = make('div', 'alert-content');
        content.append(make('span', 'alert-message', message), dismiss);
        const progress = make('div', 'alert-progress');
        alert.append(content, progress);

        const remove = () => { clearTimeout(timer); alert.remove(); };
        const timer = setTimeout(remove, ALERT_SECONDS * 1000);     // fallback if the CSS has no progress animation
        dismiss.addEventListener('click', remove);
        progress.addEventListener('animationend', remove);
        alertContainer().appendChild(alert);
    }

    async function api(path, { method = 'GET', body } = {}) {
        const response = await fetch(baseUrl + path, {
            method,
            body,
            credentials: 'same-origin',
            headers: { 'X-CSRFToken': csrfToken, 'X-Requested-With': 'XMLHttpRequest' },
        });
        let data = {};
        try { data = await response.json(); } catch (_) { /* not JSON */ }
        if (!response.ok) {
            const error = new Error(data.error || 'Something went wrong. Please try again.');
            error.errors = data.errors || {};
            throw error;
        }
        return data;
    }

    function badge(text, extraClass = '') {
        return make('span', `acct-badge ${extraClass}`.trim(), text);
    }

    // Every dialog closes with its X / Cancel buttons, Esc, or a click on the dark backdrop.
    root.querySelectorAll('dialog').forEach((dialog) => {
        dialog.addEventListener('click', (event) => {
            const clickedBackdrop = event.target === dialog && dialog !== el.formDialog;   // the form keeps typed data on stray clicks
            if (clickedBackdrop || event.target.closest('[data-close]')) dialog.close();
        });
    });

    // ------------------------------------------------------------------
    // 2. List
    // ------------------------------------------------------------------
    async function loadList() {
        const requestId = ++state.requestId;       // ignore answers that arrive late
        const params = new URLSearchParams({ q: state.q, type: state.type, status: state.status, page: state.page });
        el.list.classList.add('is-loading');
        try {
            const data = await api(`data/?${params}`);
            if (requestId === state.requestId) renderList(data);
        } catch (error) {
            if (requestId === state.requestId) toast(error.message, true);
        } finally {
            if (requestId === state.requestId) el.list.classList.remove('is-loading');
        }
    }

    function renderList(data) {
        state.page = data.page;

        for (const [status, count] of Object.entries(data.counts)) {
            const badgeEl = $(`[data-count="${status}"]`);
            if (badgeEl) badgeEl.textContent = count;
        }

        el.list.replaceChildren(...data.results.map(buildRow));

        const isEmpty = data.results.length === 0;
        el.empty.hidden = !isEmpty;
        if (isEmpty) {
            const filtering = state.q || state.type;
            el.emptyTitle.textContent = filtering ? 'No matching accounts' : `No ${state.status} accounts`;
            el.emptyText.textContent = filtering
                ? 'Try a different search or clear the filters.'
                : state.status === 'active' ? 'Use "New account" to add the first one.' : '';
        }

        el.pager.hidden = isEmpty;
        el.pagerInfo.textContent = `Showing ${data.start}\u2013${data.end} of ${data.total}`;
        el.prev.disabled = data.page <= 1;
        el.next.disabled = data.page >= data.num_pages;
    }

    function buildRow(account) {
        const row = make('button', 'acct-row account-columns');
        row.type = 'button';

        const person = make('span', 'acct-person');
        const avatar = make('img', 'acct-avatar');
        avatar.src = account.avatar_url;
        avatar.alt = '';
        const text = make('span', 'acct-person-text');
        text.append(make('strong', '', account.full_name));
        text.append(make('small', '', [account.identifier, account.email].filter(Boolean).join('  \u00b7  ')));
        person.append(avatar, text);

        const role = make('span');
        role.append(badge(account.type_label));
        const status = make('span');
        status.append(badge(account.status_label, `status-${account.status}`));

        row.append(person, role, status, make('span', 'acct-date', formatDate(account.date_joined)), icon('chevron-right'));
        row.addEventListener('click', () => openDrawer(account.id));
        return row;
    }

    function setStatusTab(status) {
        state.status = status;
        state.page = 1;
        el.tabs.querySelectorAll('button').forEach((tab) => {
            tab.setAttribute('aria-selected', String(tab.dataset.status === status));
        });
    }

    let searchTimer;
    el.search.addEventListener('input', () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
            state.q = el.search.value.trim();
            state.page = 1;
            loadList();
        }, 300);
    });
    el.typeFilter.addEventListener('change', () => { state.type = el.typeFilter.value; state.page = 1; loadList(); });
    el.tabs.addEventListener('click', (event) => {
        const tab = event.target.closest('button[data-status]');
        if (tab) { setStatusTab(tab.dataset.status); loadList(); }
    });
    el.prev.addEventListener('click', () => { state.page -= 1; loadList(); });
    el.next.addEventListener('click', () => { state.page += 1; loadList(); });

    // ------------------------------------------------------------------
    // 3. Details drawer
    // ------------------------------------------------------------------
    async function openDrawer(id) {
        try {
            const data = await api(`${id}/`);
            renderDrawer(data.account);
            if (!el.drawer.open) el.drawer.showModal();
        } catch (error) {
            toast(error.message, true);
        }
    }

    function detailRows(account) {
        const rows = [
            ['Email', account.email + (account.email_verified ? '' : '  (not verified yet)')],
            ['Mobile', account.contact_num],
            ['Joined', formatDate(account.date_joined)],
        ];
        if (account.student) {
            const s = account.student;
            rows.unshift(['Student ID', s.student_id]);
            rows.push(['College', s.college || '\u2014'], ['Program', s.program || '\u2014'],
                      ['Major', s.major || '\u2014'], ['Year level', s.year_level_label || '\u2014']);
        }
        if (account.staff) {
            const s = account.staff;
            rows.unshift(['Staff ID', s.staff_id]);
            rows.push(['Staff type', s.staff_type_label], ['Campus', s.campus]);
        }
        return rows;
    }

    function statusNote(account) {
        if (account.type === 'admin') return ['Admin accounts are managed outside this page.', ''];
        if (account.protected) return ["This is your own account, so it can't be changed here.", ''];
        if (account.status === 'suspended') return ["Suspended: this person can't sign in. Their data is kept, and you can reactivate them any time.", 'tone-warning'];
        if (account.status === 'deleted') return [`Deleted on ${formatDate(account.deleted_at)}: hidden and unable to sign in, but nothing is erased. Restoring brings it back as suspended.`, 'tone-danger'];
        return ['', ''];
    }

    function renderDrawer(account) {
        state.current = account;
        $('#acct-drawer-avatar').src = account.avatar_url;
        $('#acct-drawer-name').textContent = account.full_name;
        $('#acct-drawer-badges').replaceChildren(badge(account.type_label), badge(account.status_label, `status-${account.status}`));

        const [noteText, noteTone] = statusNote(account);
        const note = $('#acct-drawer-note');
        note.hidden = !noteText;
        note.textContent = noteText;
        note.className = `acct-note ${noteTone}`.trim();

        $('#acct-drawer-details').replaceChildren(...detailRows(account).map(([label, value]) => {
            const group = make('div');
            group.append(make('dt', '', label), make('dd', '', value));
            return group;
        }));

        const actions = $('#acct-drawer-actions');
        actions.replaceChildren();
        actions.hidden = account.protected;
        if (account.protected) return;

        const button = (label, iconName, className, handler) => {
            const node = make('button', `acct-btn ${className}`.trim());
            node.type = 'button';
            node.append(icon(iconName), label);
            node.addEventListener('click', handler);
            return node;
        };

        if (account.status === 'deleted') {
            actions.append(button('Restore account', 'arrow-counterclockwise', 'acct-btn-primary', () => runAction('restore')));
            return;
        }
        actions.append(button('Edit', 'pencil', '', () => openForm(account)));
        if (account.status === 'suspended') {
            actions.append(button('Reactivate', 'play-circle', 'acct-btn-primary', () => runAction('reactivate')));
        } else {
            actions.append(button('Suspend', 'pause-circle', 'acct-btn-warning', () => runAction('suspend')));
        }
        actions.append(button('Delete', 'trash', 'acct-btn-danger', () => runAction('delete')));
    }

    // ------------------------------------------------------------------
    // 4. Create / edit form
    // ------------------------------------------------------------------
    const field = (name) => el.form.elements[name];
    const collegeSelect = $('#f-college');

    function fillSelect(select, items, placeholder, valueKey = 'id', labelKey = 'name') {
        const choices = items.map((item) => {
            const option = make('option', '', item[labelKey]);
            option.value = item[valueKey];
            return option;
        });
        const first = make('option', '', placeholder);
        first.value = '';
        select.replaceChildren(first, ...choices);
    }

    function selectedCollege() {
        return options.colleges.find((c) => String(c.id) === collegeSelect.value);
    }

    function updatePrograms() {
        const college = selectedCollege();
        fillSelect(field('program'), college ? college.programs : [], college ? 'Choose a program' : 'Choose a college first');
        updateMajors();
    }

    function updateMajors() {
        const college = selectedCollege();
        const program = college && college.programs.find((p) => String(p.id) === field('program').value);
        fillSelect(field('major'), program ? program.majors : [], program ? (program.majors.length ? 'No major' : 'No majors for this program') : 'Choose a program first');
    }

    function setType(type) {
        el.form.querySelectorAll('[data-type-section]').forEach((section) => {
            section.disabled = section.dataset.typeSection !== type;     // disabled fields are not sent or validated
        });
        const radio = el.form.querySelector(`input[name="account_type"][value="${type}"]`);
        if (radio) radio.checked = true;
        $('#acct-id-note').textContent = state.editing ? '' :
            type === 'student'
                ? `The student ID is assigned automatically, like ${field('enrollment_year').value || options.current_year}-00001.`
                : 'The staff ID is assigned automatically, like 4821-' + (options.campuses[0] ? options.campuses[0].name.slice(0, 2) : 'AA') + '.';
    }

    function clearErrors() {
        el.form.querySelectorAll('.acct-field').forEach((wrap) => {
            wrap.classList.remove('has-error');
            const message = wrap.querySelector('.acct-error');
            if (message) message.textContent = '';
        });
        const general = $('#acct-form-error');
        general.hidden = true;
        general.textContent = '';
    }

    function showErrors(error) {
        let leftover = error.message;
        for (const [name, messages] of Object.entries(error.errors || {})) {
            const wrap = el.form.querySelector(`.acct-field[data-field="${name}"]`);
            if (wrap) {
                wrap.classList.add('has-error');
                wrap.querySelector('.acct-error').textContent = messages.join(' ');
                if (leftover === error.message && Object.keys(error.errors).length) leftover = '';
            }
        }
        if (leftover) {
            const general = $('#acct-form-error');
            general.textContent = leftover;
            general.hidden = false;
        }
    }

    /** account = null -> create a new account; otherwise edit that account. */
    function openForm(account = null) {
        state.editing = account;
        el.form.reset();
        clearErrors();

        fillSelect(collegeSelect, options.colleges, 'Choose a college');
        fillSelect(field('year_level'), options.year_levels, 'Not set', 'value', 'label');
        fillSelect(field('campus'), options.campuses, 'Choose a campus');
        fillSelect(field('staff_type'), options.staff_types, 'Choose a type', 'value', 'label');
        updatePrograms();

        field('enrollment_year').value = options.current_year;
        field('enrollment_year').max = options.current_year;

        $('#acct-form-title').textContent = account ? 'Edit account' : 'New account';
        $('#acct-form-submit').textContent = account ? 'Save changes' : 'Create account';
        $('#acct-type-switch').hidden = Boolean(account);
        $('#f-year-wrap').hidden = Boolean(account);
        $('#acct-email-note').hidden = Boolean(account);       // only new accounts get a password email

        if (account) {
            for (const name of ['first_name', 'middle_name', 'last_name', 'email', 'contact_num']) field(name).value = account[name];
            if (account.student) {
                const s = account.student;
                if (s.college_id) { collegeSelect.value = s.college_id; updatePrograms(); }
                field('program').value = s.program_id || '';
                updateMajors();
                field('major').value = s.major_id || '';
                field('year_level').value = s.year_level;
            }
            if (account.staff) {
                field('campus').value = account.staff.campus_id;
                field('staff_type').value = account.staff.staff_type;
            }
            setType(account.staff ? 'staff' : 'student');
            $('#acct-id-note').textContent = `ID ${account.identifier} \u2013 the account type and ID can't be changed.`;
        } else {
            setType('student');
        }
        el.formDialog.showModal();
        field('first_name').focus();
    }

    collegeSelect.addEventListener('change', updatePrograms);
    field('program').addEventListener('change', updateMajors);
    field('enrollment_year').addEventListener('input', () => setType('student'));
    el.form.querySelectorAll('input[name="account_type"]').forEach((radio) => {
        radio.addEventListener('change', () => setType(radio.value));
    });

    el.form.addEventListener('submit', async (event) => {
        event.preventDefault();
        clearErrors();

        const submit = $('#acct-form-submit');
        const label = submit.textContent;
        submit.disabled = true;
        submit.textContent = 'Saving\u2026';

        const editing = state.editing;
        try {
            const body = new FormData(el.form);
            const data = await api(editing ? `${editing.id}/update/` : 'create/', { method: 'POST', body });
            el.formDialog.close();
            toast(data.message);

            if (editing) {
                renderDrawer(data.account);
            } else {
                // Jump to where the new account is visible.
                el.search.value = ''; state.q = '';
                el.typeFilter.value = ''; state.type = '';
                setStatusTab('active');
            }
            loadList();
        } catch (error) {
            showErrors(error);
        } finally {
            submit.disabled = false;
            submit.textContent = label;
        }
    });

    $('#acct-new').addEventListener('click', () => openForm());

    // ------------------------------------------------------------------
    // 5. Actions
    // ------------------------------------------------------------------
    // What each action says in the confirmation pop-up. Reactivate and restore
    // are low-risk, so the pop-up still appears but is short and needs no reason.
    const ACTIONS = {
        'suspend': {
            title: (a) => `Suspend ${a.full_name}?`,
            text: () => "They won't be able to sign in until you reactivate them. Nothing is deleted.",
            ok: 'Suspend account', style: 'acct-btn-warning', reason: true,
        },
        'delete': {
            title: (a) => `Delete ${a.full_name}?`,
            text: () => "The account will be hidden and unable to sign in. Nothing is erased, and you can restore it later from the Deleted tab.",
            ok: 'Delete account', style: 'acct-btn-danger is-solid', reason: true,
        },
        'reactivate': {
            title: (a) => `Reactivate ${a.full_name}?`,
            text: () => 'They will be able to sign in again.',
            ok: 'Reactivate', style: 'acct-btn-primary', reason: false,
        },
        'restore': {
            title: (a) => `Restore ${a.full_name}?`,
            text: () => 'The account comes back as suspended. Reactivate it afterwards so they can sign in.',
            ok: 'Restore account', style: 'acct-btn-primary', reason: false,
        },
    };

    /** Shows the confirmation pop-up. Resolves to the reason text, or null if cancelled. */
    function confirmAction(action, account) {
        const config = ACTIONS[action];
        const reason = $('#acct-confirm-reason');
        const ok = $('#acct-confirm-ok');

        $('#acct-confirm-title').textContent = config.title(account);
        $('#acct-confirm-text').textContent = config.text(account);
        $('#acct-confirm-reason-wrap').hidden = !config.reason;
        reason.disabled = !config.reason;      // a disabled field is skipped by validation
        reason.value = '';
        ok.textContent = config.ok;
        ok.className = `acct-btn ${config.style}`;

        el.confirm.returnValue = '';
        return new Promise((resolve) => {
            el.confirm.addEventListener('close', () => {
                resolve(el.confirm.returnValue === 'confirm' ? reason.value.trim() : null);
            }, { once: true });
            el.confirm.showModal();
            if (config.reason) reason.focus();
        });
    }

    async function runAction(action) {
        const account = state.current;
        const reason = await confirmAction(action, account);
        if (reason === null) return;

        const buttons = $('#acct-drawer-actions').querySelectorAll('button');
        buttons.forEach((b) => { b.disabled = true; });
        try {
            const body = new FormData();
            if (reason) body.set('reason', reason);
            const data = await api(`${account.id}/${action}/`, { method: 'POST', body });

            toast(data.message);
            renderDrawer(data.account);
            // The account may now belong on another tab, so follow it there.
            if (data.account.status !== state.status) setStatusTab(data.account.status);
            loadList();
        } catch (error) {
            toast(error.message, true);
            buttons.forEach((b) => { b.disabled = false; });
        }
    }

    // ------------------------------------------------------------------
    // 6. Start-up
    // ------------------------------------------------------------------
    loadList();
})();