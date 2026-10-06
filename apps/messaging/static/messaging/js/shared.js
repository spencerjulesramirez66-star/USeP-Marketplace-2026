import { qs, debounce } from './dom.js';
import { get } from './api.js';

const esc = (value) => String(value ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

function mediaHtml(item) {
    return item.is_video
        ? `<a class="messaging-media-item" href="${esc(item.url)}" target="_blank" rel="noopener"><video muted preload="metadata"><source src="${esc(item.url)}"></video><span>${esc(item.name)}</span></a>`
        : `<button class="messaging-media-item" type="button" data-media-url="${esc(item.url)}" data-media-name="${esc(item.name)}"><img src="${esc(item.url)}" alt="${esc(item.name)}"><span>${esc(item.name)}</span></button>`;
}

function fileHtml(item) {
    return `<a class="messaging-resource" href="${esc(item.url)}" target="_blank" rel="noopener"><i class="bi bi-file-earmark-text" aria-hidden="true"></i><span>${esc(item.name)}</span></a>`;
}

function linkHtml(link) {
    const icon = link.is_drive ? 'bi-folder-fill' : 'bi-link-45deg';
    return `<a class="messaging-link-card" href="${esc(link.url)}" target="_blank" rel="noopener noreferrer nofollow"><span class="messaging-link-card-visual placeholder"><i class="bi ${icon}" aria-hidden="true"></i></span><span class="messaging-link-card-copy"><strong title="${esc(link.title)}">${esc(link.title)}</strong><span>${esc(link.domain)}</span></span></a>`;
}

export function initSharedContent({ panel, sharedUrl, onRendered }) {
    if (!panel || !sharedUrl) return { refresh() {} };

    const mediaEl = qs('[data-shared-media]', panel);
    const filesEl = qs('[data-shared-files]', panel);
    const linksEl = qs('[data-shared-links]', panel);
    const mediaCount = qs('[data-media-count]', panel);
    const filesCount = qs('[data-files-count]', panel);
    const linksCount = qs('[data-shared-links-count]', panel);
    let signature = null;

    function fill(el, items, render, emptyText) {
        if (!el) return;
        el.innerHTML = items.length ? items.map(render).join('') : `<p class="messaging-details-empty">${emptyText}</p>`;
    }

    async function load() {
        try {
            const data = await get(sharedUrl);
            const next = JSON.stringify(data);
            if (next === signature) return; // nothing changed: don't touch the DOM
            signature = next;
            fill(mediaEl, data.media, mediaHtml, 'No images shared yet.');
            fill(filesEl, data.files, fileHtml, 'No files shared yet.');
            fill(linksEl, data.links, linkHtml, 'No links shared yet.');
            if (mediaCount) mediaCount.textContent = data.media.length;
            if (filesCount) filesCount.textContent = data.files.length;
            if (linksCount) linksCount.textContent = data.links.length;
            onRendered?.();
        } catch { /* keep the current panel */ }
    }

    return { refresh: debounce(load, 400) };
}