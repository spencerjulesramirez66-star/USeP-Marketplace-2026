(() => {
    const root = document.getElementById('transaction-monitoring');
    if (!root) return;

    const content = root.querySelector('[data-monitoring-content]');
    const dashboard = root.querySelector('[data-dashboard]');
    const skeleton = root.querySelector('[data-skeleton]');
    const errorBanner = root.querySelector('[data-error]');
    const drawer = document.getElementById('transaction-drawer');
    const colorMap = {
        pending: '#d97706',
        in_progress: '#2563eb',
        completed: '#16a34a',
        closed_failed: '#98a2b3',
    };
    let controller = null;
    let paused = false;
    let activeParams = new URLSearchParams(window.location.search);

    const element = (tag, className, text) => {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    };

    const setRangeControls = (params) => {
        const selected = params.get('range') || '7d';
        root.querySelectorAll('[data-range]').forEach((button) => {
            button.setAttribute('aria-pressed', String(button.dataset.range === selected));
        });
        const custom = selected === 'custom';
        root.querySelectorAll('.monitoring-custom-date').forEach((label) => {
            label.hidden = !custom;
        });
        if (custom) {
            root.querySelector('[data-date-from]').value = params.get('date_from') || '';
            root.querySelector('[data-date-to]').value = params.get('date_to') || '';
        }
    };

    const showError = () => {
        errorBanner.hidden = false;
    };

    const formatDelta = (delta) => {
        if (!delta) return '';
        if (delta.percent === null) {
            return `${delta.change > 0 ? '+' : ''}${delta.change} vs previous period`;
        }
        return `${delta.percent > 0 ? '+' : ''}${delta.percent}% vs previous period`;
    };

    const renderKpis = (data) => {
        const kpis = data.kpis;
        root.querySelector('[data-kpi="total"]').textContent = kpis.total;
        root.querySelector('[data-kpi="pending"]').textContent = kpis.pending;
        root.querySelector('[data-kpi="in_progress"]').textContent = kpis.in_progress;
        root.querySelector('[data-kpi="completed_count"]').textContent = kpis.completed_count;
        root.querySelector('[data-kpi="closed_failed"]').textContent = kpis.closed_failed;
        root.querySelector('[data-kpi="average_value"]').textContent = kpis.average_value_display;
        root.querySelector('[data-kpi-sub="completion_rate"]').textContent = `${kpis.completion_rate}% completion rate`;
        root.querySelector('[data-kpi-sub="completed_value"]').textContent = kpis.completed_value_display;
        Object.entries(kpis.deltas).forEach(([key, value]) => {
            const target = root.querySelector(`[data-delta="${key}"]`);
            if (target) target.textContent = formatDelta(value);
        });
        root.querySelector('[data-period-label]').textContent = data.period.label;
        root.querySelector('[data-last-updated]').textContent = `Updated ${data.last_updated}`;
    };

    const renderChart = (data) => {
        const chart = root.querySelector('[data-chart]');
        const table = root.querySelector('[data-chart-table]');
        chart.replaceChildren();
        table.replaceChildren();
        const rowsByDay = new Map(data.daily_series.map((row) => [row.day, row]));
        const start = new Date(`${data.period.start}T00:00:00Z`);
        const end = new Date(`${data.period.end}T00:00:00Z`);
        const tableElement = element('table');
        const head = element('thead');
        const headerRow = element('tr');
        ['Date (PHT)', 'Pending', 'In progress', 'Completed', 'Closed / failed'].forEach((label) => {
            headerRow.append(element('th', '', label));
        });
        head.append(headerRow);
        tableElement.append(head);
        const body = element('tbody');
        const days = [];
        for (const cursor = new Date(start); cursor <= end; cursor.setUTCDate(cursor.getUTCDate() + 1)) {
            const key = cursor.toISOString().slice(0, 10);
            const row = rowsByDay.get(key) || {
                pending: 0,
                in_progress: 0,
                completed: 0,
                closed_failed: 0,
            };
            days.push({ key, row });
            const tr = element('tr');
            tr.append(element('th', '', key));
            ['pending', 'in_progress', 'completed', 'closed_failed'].forEach((bucket) => {
                tr.append(element('td', '', String(row[bucket] || 0)));
            });
            body.append(tr);
        }
        tableElement.append(body);
        table.append(tableElement);
        const maxTotal = Math.max(1, ...days.map(({ row }) =>
            ['pending', 'in_progress', 'completed', 'closed_failed']
                .reduce((sum, key) => sum + (row[key] || 0), 0)));
        days.forEach(({ key, row }) => {
            const column = element('div', 'monitoring-chart-column');
            const stack = element('div', 'monitoring-chart-stack');
            stack.setAttribute('aria-label', `${key}: ${row.pending || 0} pending, ${row.in_progress || 0} in progress, ${row.completed || 0} completed, ${row.closed_failed || 0} closed or failed`);
            ['pending', 'in_progress', 'completed', 'closed_failed'].forEach((bucket) => {
                const count = row[bucket] || 0;
                if (!count) return;
                const segment = element('span', `monitoring-chart-segment monitoring-chart-${bucket}`);
                segment.style.height = `${(count / maxTotal) * 100}%`;
                segment.title = `${bucket.replace('_', ' ')}: ${count}`;
                stack.append(segment);
            });
            column.append(stack, element('span', 'monitoring-chart-date', key.slice(5)));
            chart.append(column);
        });
    };

    const renderStatus = (data) => {
        const totals = { pending: 0, in_progress: 0, completed: 0, closed_failed: 0 };
        data.status_breakdown.forEach((row) => {
            totals[row.bucket] = (totals[row.bucket] || 0) + row.count;
        });
        const total = Object.values(totals).reduce((sum, count) => sum + count, 0);
        let offset = 0;
        const segments = [];
        Object.entries(totals).forEach(([bucket, count]) => {
            const start = total ? (offset / total) * 100 : 0;
            offset += count;
            const end = total ? (offset / total) * 100 : 0;
            segments.push(`${colorMap[bucket]} ${start}% ${end}%`);
        });
        const donut = root.querySelector('[data-donut]');
        donut.style.background = total
            ? `conic-gradient(${segments.join(', ')})`
            : 'conic-gradient(#eaecf0 0% 100%)';
        donut.setAttribute('aria-label', `Status breakdown: ${total} transactions`);
        const legend = root.querySelector('[data-status-legend]');
        legend.replaceChildren();
        data.status_breakdown.forEach((row) => {
            const item = element('li');
            const marker = element('span', `monitoring-status-marker monitoring-marker-${row.bucket}`);
            item.append(marker, element('span', '', row.label), element('strong', '', row.count));
            legend.append(item);
        });
    };

    const renderRanked = (selector, items, nameKey, valueKey) => {
        const list = root.querySelector(selector);
        list.replaceChildren();
        if (!items.length) {
            list.append(element('li', 'monitoring-empty', 'No data in this period.'));
            return;
        }
        items.forEach((item) => {
            const row = element('li');
            row.append(element('span', '', item[nameKey]), element('strong', '', item[valueKey]));
            list.append(row);
        });
    };

    const renderAttention = (data) => {
        const rules = [
            ['stalled_pending', 'Stalled pending'],
            ['stalled_delivery', 'Stalled delivery'],
            ['high_value', 'High value'],
            ['repeat_canceller', 'Repeat canceller'],
        ];
        const counts = root.querySelector('[data-rule-counts]');
        counts.replaceChildren();
        rules.forEach(([key, label]) => {
            const chip = element('span', 'monitoring-rule-chip', `${label}: ${data.attention_counts[key] || 0}`);
            counts.append(chip);
        });
        const list = root.querySelector('[data-attention-items]');
        list.replaceChildren();
        if (!data.attention_items.length) {
            list.append(element('p', 'monitoring-empty', 'No transactions need attention right now.'));
        }
        data.attention_items.forEach((item) => {
            const row = element('article', 'monitoring-attention-row');
            const details = element('div');
            details.append(
                element('strong', '', item.rule_label),
                element('span', '', `${item.transaction.display_id} · ${item.transaction.listing_title}`),
                element('small', '', `${item.transaction.buyer_name} · ${item.transaction.created_display}`),
            );
            const action = element('button', 'transaction-button', 'View');
            action.type = 'button';
            action.dataset.transactionId = item.transaction.id;
            action.setAttribute('aria-label', `View transaction ${item.transaction.display_id}`);
            const history = element('a', '', 'History');
            history.href = item.history_url;
            row.append(details, action, history);
            list.append(row);
        });
    };

    const renderLatest = (data) => {
        const list = root.querySelector('[data-latest]');
        list.replaceChildren();
        if (!data.latest_transactions.length) {
            list.append(element('p', 'monitoring-empty', 'No transactions yet.'));
            return;
        }
        data.latest_transactions.forEach((transaction) => {
            const row = element('article', 'monitoring-recent-row');
            const detail = element('div');
            detail.append(
                element('strong', '', transaction.display_id),
                element('span', '', transaction.listing_title),
                element('small', '', `${transaction.buyer_name} · ${transaction.created_display}`),
            );
            const status = element('span', `transaction-status transaction-status-${transaction.status_bucket}`, transaction.status_bucket_label);
            const total = element('strong', '', transaction.total_display);
            const button = element('button', 'transaction-icon-button', 'View');
            button.type = 'button';
            button.dataset.transactionId = transaction.id;
            button.setAttribute('aria-label', `View transaction ${transaction.display_id}`);
            row.append(detail, status, total, button);
            list.append(row);
        });
    };

    const render = (data) => {
        renderKpis(data);
        renderChart(data);
        renderStatus(data);
        renderRanked('[data-top-sellers]', data.top_sellers, 'name', 'value_display');
        renderRanked('[data-top-categories]', data.top_categories, 'name', 'count');
        renderAttention(data);
        renderLatest(data);
        skeleton.hidden = true;
        dashboard.hidden = false;
    };

    const load = async (params, updateUrl = false) => {
        controller?.abort();
        controller = new AbortController();
        const requestController = controller;
        const requestParams = new URLSearchParams(params);
        requestParams.delete('page');
        const url = new URL(root.dataset.dataUrl, window.location.origin);
        url.search = requestParams.toString();
        content.setAttribute('aria-busy', 'true');
        try {
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                signal: requestController.signal,
            });
            if (!response.ok) throw new Error('Monitoring request failed.');
            const data = await response.json();
            render(data);
            activeParams = requestParams;
            setRangeControls(activeParams);
            errorBanner.hidden = true;
            if (updateUrl) {
                const query = activeParams.toString();
                history.pushState({}, '', `${window.location.pathname}${query ? `?${query}` : ''}`);
            }
        } catch (error) {
            if (error.name !== 'AbortError') showError();
        } finally {
            if (controller === requestController) content.setAttribute('aria-busy', 'false');
        }
    };

    const chooseRange = (range, updateUrl = true) => {
        const params = new URLSearchParams(activeParams);
        params.set('range', range);
        params.delete('date_from');
        params.delete('date_to');
        setRangeControls(params);
        if (range === 'custom') return;
        load(params, updateUrl);
    };

    root.addEventListener('click', (event) => {
        if (event.target.closest('[data-transaction-id]')) {
            controller?.abort();
            content.setAttribute('aria-busy', 'false');
        }
        const rangeButton = event.target.closest('[data-range]');
        if (rangeButton) chooseRange(rangeButton.dataset.range);
        if (event.target.closest('[data-refresh]') || event.target.closest('[data-retry]')) {
            load(activeParams);
        }
        if (event.target.closest('[data-pause]')) {
            paused = !paused;
            event.target.closest('[data-pause]').textContent = paused ? 'Resume' : 'Pause';
            if (!paused) load(activeParams);
        }
    });

    root.querySelectorAll('[data-date-from], [data-date-to]').forEach((input) => {
        input.addEventListener('change', () => {
            const from = root.querySelector('[data-date-from]').value;
            const to = root.querySelector('[data-date-to]').value;
            if (!from || !to || from > to) return;
            const params = new URLSearchParams(activeParams);
            params.set('range', 'custom');
            params.set('date_from', from);
            params.set('date_to', to);
            load(params, true);
        });
    });

    window.addEventListener('popstate', () => {
        const params = new URLSearchParams(window.location.search);
        if (!params.has('range')) params.set('range', '7d');
        setRangeControls(params);
        load(params);
    });

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            controller?.abort();
            content.setAttribute('aria-busy', 'false');
        } else if (!paused && !drawer?.open) {
            load(activeParams);
        }
    });
    if (drawer) {
        drawer.addEventListener('close', () => {
            if (!paused && !document.hidden) load(activeParams);
        });
    }
    window.setInterval(() => {
        if (!paused && !document.hidden && !drawer?.open) load(activeParams);
    }, 30000);
    if (!activeParams.has('range')) activeParams.set('range', '7d');
    setRangeControls(activeParams);
    load(activeParams);
})();
