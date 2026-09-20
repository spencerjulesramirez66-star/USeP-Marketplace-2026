document.addEventListener('DOMContentLoaded', () => {
  const search = document.querySelector('#message-search');
  const conversationList = document.querySelector('#conversation-list');
  const conversationSearchResults = document.querySelector('#conversation-search-results');
  const messagingLayout = document.querySelector('.messaging-layout');
  let conversationSearchTimer = null;
  let conversationSearchController = null;
  const renderConversationSearch = (payload) => {
    if (!conversationSearchResults) return;
    conversationSearchResults.replaceChildren();
    if (!payload.results.length) {
      const empty = document.createElement('p');
      empty.className = 'messaging-search-empty';
      empty.textContent = `No conversations found for “${payload.query}”`;
      conversationSearchResults.append(empty);
      return;
    }
    payload.results.forEach((item) => {
      const result = document.createElement('a');
      result.className = 'conversation-search-result';
      result.href = item.url;
      const avatar = document.createElement('img');
      avatar.src = item.participant_avatar_url;
      avatar.alt = '';
      const copy = document.createElement('span');
      copy.className = 'conversation-search-result-copy';
      const participant = document.createElement('strong');
      participant.textContent = item.participant_name;
      const listing = document.createElement('span');
      listing.textContent = item.listing_title;
      copy.append(participant, listing);
      result.append(avatar, copy);
      if (item.unread_count) {
        const badge = document.createElement('em');
        badge.textContent = item.unread_count > 99 ? '99+' : String(item.unread_count);
        result.append(badge);
      }
      conversationSearchResults.append(result);
    });
  };
  if (search)
    search.addEventListener('input', () => {
      const query = search.value.trim();
      window.clearTimeout(conversationSearchTimer);
      conversationSearchController?.abort();
      if (query.length < 2) {
        conversationSearchResults.hidden = true;
        conversationList.hidden = false;
        return;
      }
      conversationList.hidden = true;
      conversationSearchResults.hidden = false;
      conversationSearchResults.textContent = 'Searching conversations…';
      conversationSearchTimer = window.setTimeout(async () => {
        conversationSearchController = new AbortController();
        try {
          const response = await fetch(
            `${search.dataset.searchUrl}?q=${encodeURIComponent(query)}`,
            {
              headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
              signal: conversationSearchController.signal,
            },
          );
          if (!response.ok || search.value.trim() !== query) return;
          renderConversationSearch(await response.json());
        } catch (error) {
          if (error.name !== 'AbortError')
            conversationSearchResults.textContent = 'Conversation search is unavailable.';
        }
      }, 300);
    });

  const debugMessaging = (...args) => {
    if (window.MESSAGES_DEBUG) console.debug(...args);
  };
  const formatSidebarTime = (value) =>
    new Date(value).toLocaleDateString([], { month: 'short', day: 'numeric' });
  const setText = (element, value) => {
    if (element && element.textContent !== value) element.textContent = value;
  };
  const patchUnreadBadge = (parent, count, before = null) => {
    let badge = parent.querySelector(':scope > .conversation-unread-badge');
    if (!count) {
      badge?.remove();
      return;
    }
    if (!badge) {
      badge = document.createElement('span');
      badge.className = 'conversation-unread-badge';
      parent.insertBefore(badge, before);
    }
    setText(badge, String(count));
  };
  const createConversationRow = (item, participant, activeConversationId) => {
    const wrap = document.createElement('div');
    wrap.className = 'conversation-row-wrap';
    const row = document.createElement('a');
    row.className = `conversation-row${Number(item.id) === activeConversationId ? ' active' : ''}${item.unread_count ? ' has-unread' : ''}`;
    row.href = item.url;
    row.dataset.conversationId = String(item.id);
    row.dataset.conversationSearch = `${item.listing_title} ${participant.name}`;
    const image = document.createElement('img');
    image.className = 'conversation-avatar';
    image.src = item.listing_image;
    image.alt = '';
    const copy = document.createElement('span');
    copy.className = 'conversation-row-copy';
    const title = document.createElement('strong');
    title.textContent = item.listing_title;
    const preview = document.createElement('span');
    preview.textContent = item.preview || 'Listing conversation';
    copy.append(title, preview);
    row.append(image, copy);
    patchUnreadBadge(row, item.unread_count);
    const time = document.createElement('time');
    time.dateTime = item.updated_at;
    time.textContent = formatSidebarTime(item.updated_at);
    row.append(time);
    const options = document.createElement('button');
    options.type = 'button';
    options.className = 'conversation-delete-menu';
    options.dataset.conversationOptions = String(item.id);
    options.setAttribute('aria-label', 'Conversation options');
    options.title = 'Conversation options';
    options.innerHTML = '<i class="bi bi-three-dots" aria-hidden="true"></i>';
    wrap.append(row, options);
    return wrap;
  };
  const enableGroupToggleAnimation = (groupElement) => {
    if (groupElement.dataset.toggleAnimationBound) return;
    groupElement.dataset.toggleAnimationBound = 'true';
    groupElement.addEventListener('toggle', () => {
      groupElement.classList.toggle('is-expanding', groupElement.open);
      window.setTimeout(() => groupElement.classList.remove('is-expanding'), 220);
    });
  };
  const createConversationGroup = (group) => {
    const groupElement = document.createElement('details');
    groupElement.className = 'conversation-group is-new-participant';
    groupElement.dataset.participantId = String(group.participant.id);
    const summary = document.createElement('summary');
    const avatar = document.createElement('img');
    avatar.className = 'conversation-avatar';
    avatar.alt = '';
    const copy = document.createElement('span');
    copy.className = 'conversation-row-copy';
    copy.append(document.createElement('strong'), document.createElement('span'));
    const chevron = document.createElement('i');
    chevron.className = 'bi bi-chevron-down';
    chevron.setAttribute('aria-hidden', 'true');
    summary.append(avatar, copy, chevron);
    groupElement.append(summary);
    groupElement.addEventListener(
      'animationend',
      () => groupElement.classList.remove('is-new-participant'),
      { once: true },
    );
    enableGroupToggleAnimation(groupElement);
    return groupElement;
  };
  const patchConversationRow = (wrap, item, participant, activeConversationId) => {
    const row = wrap.querySelector('.conversation-row');
    row.href = item.url;
    row.dataset.conversationId = String(item.id);
    row.dataset.conversationSearch = `${item.listing_title} ${participant.name}`;
    row.classList.toggle('active', Number(item.id) === activeConversationId);
    row.classList.toggle('has-unread', Boolean(item.unread_count));
    const image = row.querySelector('.conversation-avatar');
    if (image.src !== new URL(item.listing_image, window.location.origin).href)
      image.src = item.listing_image;
    const copy = row.querySelector('.conversation-row-copy');
    setText(copy.querySelector('strong'), item.listing_title);
    setText(copy.querySelector('span'), item.preview || 'Listing conversation');
    const time = row.querySelector('time');
    if (time.dateTime !== item.updated_at) {
      time.dateTime = item.updated_at;
      setText(time, formatSidebarTime(item.updated_at));
    }
    patchUnreadBadge(row, item.unread_count, time);
  };
  const patchConversationGroup = (groupElement, group, activeConversationId) => {
    enableGroupToggleAnimation(groupElement);
    groupElement.dataset.participantId = String(group.participant.id);
    const summary = groupElement.querySelector(':scope > summary');
    const avatar = summary.querySelector('.conversation-avatar');
    if (avatar.src !== new URL(group.participant.avatar, window.location.origin).href)
      avatar.src = group.participant.avatar;
    const copy = summary.querySelector('.conversation-row-copy');
    setText(copy.querySelector('strong'), group.participant.name);
    setText(
      copy.querySelector('span'),
      `${group.conversations.length} ${group.conversations.length === 1 ? 'inquiry' : 'inquiries'}`,
    );
    summary.classList.toggle('has-unread', Boolean(group.unread_count));
    patchUnreadBadge(summary, group.unread_count, summary.querySelector('.bi-chevron-down'));

    let reference = summary.nextElementSibling;
    const incomingIds = new Set(group.conversations.map((item) => String(item.id)));
    group.conversations.forEach((item) => {
      let row = groupElement.querySelector(`.conversation-row[data-conversation-id="${item.id}"]`);
      let wrap = row?.closest('.conversation-row-wrap');
      if (!wrap) {
        wrap = createConversationRow(item, group.participant, activeConversationId);
        wrap.classList.add('is-new-conversation');
        wrap.addEventListener('animationend', () => wrap.classList.remove('is-new-conversation'), {
          once: true,
        });
        debugMessaging('[sidebar] insert conversation', item.id);
      } else {
        patchConversationRow(wrap, item, group.participant, activeConversationId);
      }
      if (wrap !== reference) {
        groupElement.insertBefore(wrap, reference);
        if (row) debugMessaging('[sidebar] move conversation', item.id);
      }
      reference = wrap.nextElementSibling;
    });
    groupElement.querySelectorAll('.conversation-row').forEach((row) => {
      if (!incomingIds.has(row.dataset.conversationId)) {
        debugMessaging('[sidebar] remove conversation', row.dataset.conversationId);
        row.closest('.conversation-row-wrap')?.remove();
      }
    });
    debugMessaging('[sidebar] patch participant', group.participant.id);
  };
  let sidebarPollTimer = null;
  let sidebarPollInFlight = false;
  const refreshConversationSidebar = async () => {
    const stateUrl = messagingLayout?.dataset.conversationSidebarStateUrl;
    if (!conversationList || !stateUrl || sidebarPollInFlight) return;
    sidebarPollInFlight = true;
    try {
      const response = await fetch(stateUrl, {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      });
      if (!response.ok) return;
      const payload = await response.json();
      document.dispatchEvent(
        new CustomEvent('messages:unread-count', {
          detail: { count: payload.total_unread_count },
        }),
      );
      const activeConversationId = Number(
        document.querySelector('.conversation-row.active')?.dataset.conversationId || 0,
      );
      conversationList.querySelector('.conversation-empty')?.remove();
      let groupReference = conversationList.firstElementChild;
      (payload.groups || []).forEach((group) => {
        let groupElement = conversationList.querySelector(
          `[data-participant-id="${group.participant.id}"]`,
        );
        if (!groupElement) {
          groupElement = createConversationGroup(group);
          debugMessaging('[sidebar] insert participant', group.participant.id);
        }
        patchConversationGroup(groupElement, group, activeConversationId);
        if (groupElement !== groupReference)
          conversationList.insertBefore(groupElement, groupReference);
        groupReference = groupElement.nextElementSibling;
      });
      const participantIds = new Set(
        (payload.groups || []).map((group) => String(group.participant.id)),
      );
      conversationList.querySelectorAll('.conversation-group').forEach((group) => {
        if (!participantIds.has(group.dataset.participantId)) group.remove();
      });
      if (!(payload.groups || []).length) {
        const empty = document.createElement('div');
        empty.className = 'conversation-empty';
        empty.innerHTML =
          '<i class="bi bi-chat-square-text" aria-hidden="true"></i><strong>No conversations yet</strong><span>Message a seller from a marketplace listing to start chatting.</span>';
        conversationList.append(empty);
      }
    } catch (_) {
      // Keep the existing sidebar usable and try again on the next cycle.
    } finally {
      sidebarPollInFlight = false;
    }
  };
  const pollConversationSidebar = async () => {
    await refreshConversationSidebar();
    sidebarPollTimer = window.setTimeout(pollConversationSidebar, document.hidden ? 5000 : 2000);
  };
  if (conversationList && messagingLayout?.dataset.conversationSidebarStateUrl) {
    refreshConversationSidebar();
    sidebarPollTimer = window.setTimeout(pollConversationSidebar, 2000);
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) refreshConversationSidebar();
    });
    window.addEventListener('pagehide', () => window.clearTimeout(sidebarPollTimer), {
      once: true,
    });
  }

  const thread = document.querySelector('.messaging-thread');
  const composeForm = document.querySelector('.messaging-compose-form');
  const messagingPage = document.querySelector('.messaging-page');
  const mobileBack = document.querySelector('.messaging-mobile-back');
  const mobileBreakpoint = window.matchMedia('(max-width: 760px)');
  let chatIsActuallyVisible =
    !mobileBreakpoint.matches || messagingPage?.classList.contains('messaging-page-chat-open');
  const canMarkConversationRead = () =>
    Boolean(
      !document.hidden &&
      thread &&
      (!mobileBreakpoint.matches || chatIsActuallyVisible) &&
      (!mobileBreakpoint.matches || messagingPage?.classList.contains('messaging-page-chat-open')),
    );
  mobileBreakpoint.addEventListener?.('change', (event) => {
    chatIsActuallyVisible =
      !event.matches || messagingPage?.classList.contains('messaging-page-chat-open');
  });
  const lightbox = document.querySelector('#messaging-lightbox');
  let lightboxIndex = 0;
  let lightboxInThread = false;
  const lightboxImages = () =>
    [...document.querySelectorAll('[data-media-url]')].filter(
      (element) => Boolean(element.closest('.messaging-thread')) === lightboxInThread,
    );
  const renderLightbox = () => {
    const images = lightboxImages();
    const item = images[lightboxIndex];
    if (!item) return;
    lightbox.querySelector('img').src = item.dataset.mediaUrl;
    lightbox.querySelector('img').alt = item.dataset.mediaName || '';
    lightbox.querySelector('.messaging-lightbox-count').textContent =
      `${lightboxIndex + 1} / ${images.length}`;
    lightbox.querySelector('.messaging-lightbox-prev').disabled = lightboxIndex === 0;
    lightbox.querySelector('.messaging-lightbox-next').disabled =
      lightboxIndex === images.length - 1;
  };
  document.addEventListener('click', (event) => {
    const item = event.target.closest('[data-media-url]');
    if (!item) return;
    lightboxInThread = Boolean(item.closest('.messaging-thread'));
    lightboxIndex = lightboxImages().indexOf(item);
    renderLightbox();
    lightbox.showModal();
  });
  lightbox
    ?.querySelector('.messaging-lightbox-close')
    ?.addEventListener('click', () => lightbox.close());
  lightbox?.querySelector('.messaging-lightbox-prev')?.addEventListener('click', () => {
    lightboxIndex--;
    renderLightbox();
  });
  lightbox?.querySelector('.messaging-lightbox-next')?.addEventListener('click', () => {
    lightboxIndex++;
    renderLightbox();
  });
  document.addEventListener('keydown', (event) => {
    if (!lightbox?.open) return;
    if (event.key === 'ArrowLeft' && lightboxIndex) {
      lightboxIndex--;
      renderLightbox();
    }
    if (event.key === 'ArrowRight' && lightboxIndex < lightboxImages().length - 1) {
      lightboxIndex++;
      renderLightbox();
    }
  });
  const details = document.querySelector('#messaging-details');
  const detailsToggle = document.querySelector('#messaging-details-toggle');
  const detailsClose = document.querySelector('.messaging-details-close');
  const sharedLinks = document.querySelector('[data-shared-links]');
  const sharedLinksCount = document.querySelector('[data-shared-links-count]');
  let linksRefreshInFlight = false;
  const renderSharedLinks = (links) => {
    if (!sharedLinks || !sharedLinksCount) return;
    sharedLinks.replaceChildren();
    sharedLinksCount.textContent = String(links.length);
    if (!links.length) {
      const empty = document.createElement('p');
      empty.className = 'messaging-details-empty';
      empty.textContent = 'No links shared yet.';
      sharedLinks.append(empty);
      return;
    }
    links.forEach((item) => {
      const link = document.createElement('a');
      link.className = 'messaging-link-card';
      link.href = item.url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer nofollow';
      const visual = document.createElement('span');
      visual.className = `messaging-link-card-visual${item.image ? '' : ' placeholder'}`;
      if (item.image) {
        const image = document.createElement('img');
        image.src = item.image;
        image.alt = '';
        image.addEventListener(
          'error',
          () => {
            visual.replaceChildren();
            visual.classList.add('placeholder');
            const icon = document.createElement('i');
            icon.className = `bi ${item.is_drive ? 'bi-folder-fill' : 'bi-link-45deg'}`;
            icon.setAttribute('aria-hidden', 'true');
            visual.append(icon);
          },
          { once: true },
        );
        visual.append(image);
      } else {
        const icon = document.createElement('i');
        icon.className = `bi ${item.is_drive ? 'bi-folder-fill' : 'bi-link-45deg'}`;
        icon.setAttribute('aria-hidden', 'true');
        visual.append(icon);
      }
      const copy = document.createElement('span');
      copy.className = 'messaging-link-card-copy';
      const title = document.createElement('strong');
      title.title = item.title || item.domain || item.url;
      title.textContent = item.title || item.domain || item.url;
      const domain = document.createElement('span');
      domain.textContent = item.domain || item.url;
      copy.append(title, domain);
      link.append(visual, copy);
      sharedLinks.append(link);
    });
  };
  const refreshSharedLinks = async () => {
    if (!thread?.dataset.linksUrl || linksRefreshInFlight) return;
    linksRefreshInFlight = true;
    try {
      const response = await fetch(thread.dataset.linksUrl, {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      });
      if (!response.ok) return;
      const payload = await response.json();
      renderSharedLinks(Array.isArray(payload.links) ? payload.links : []);
    } catch (_) {
      // Keep the server-rendered links visible if the refresh fails.
    } finally {
      linksRefreshInFlight = false;
    }
  };
  const setDetailsOpen = (open) => {
    if (!details || !detailsToggle) return;
    details.hidden = !open;
    detailsToggle.setAttribute('aria-expanded', String(open));
    if (open) {
      stopTyping?.();
      refreshSharedLinks();
    }
  };
  detailsToggle?.addEventListener('click', () => {
    if (messageSearchModeActive) {
      showMessageSearch();
      return;
    }
    setDetailsOpen(details.hidden);
  });
  detailsClose?.addEventListener('click', () => setDetailsOpen(false));
  document.addEventListener('click', (event) => {
    if (
      !details ||
      details.hidden ||
      details.contains(event.target) ||
      detailsToggle?.contains(event.target)
    )
      return;
    setDetailsOpen(false);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') setDetailsOpen(false);
  });

  mobileBack?.addEventListener('click', () => {
    if (!mobileBreakpoint.matches) return;
    stopTyping?.();
    cancelEditing?.();
    chatIsActuallyVisible = false;
    messagingPage.classList.remove('messaging-page-chat-open');
    const listUrl = messagingLayout?.dataset.conversationListUrl;
    if (listUrl && window.location.pathname !== listUrl) {
      window.history.replaceState({ messagingPanel: 'list' }, '', listUrl);
    }
    const activeConversation = document.querySelector('.conversation-row.active');
    activeConversation?.focus({ preventScroll: true });
  });
  const conversationActionsDialog = document.querySelector('#conversation-actions-dialog');
  const conversationClearDialog = document.querySelector('#conversation-clear-dialog');
  const clearConversationConfirm = conversationClearDialog?.querySelector('[data-clear-confirm]');
  let pendingConversationId = null;
  const csrfToken = () =>
    document.cookie
      .split('; ')
      .find((item) => item.startsWith('csrftoken='))
      ?.split('=')
      .slice(1)
      .join('') || '';
  const clearConversationUrl = (conversationId) => {
    const template = messagingLayout?.dataset.clearConversationUrlTemplate;
    return template ? template.replace('/0/', `/${conversationId}/`) : '';
  };
  document.addEventListener('click', (event) => {
    const options = event.target.closest('[data-conversation-options]');
    if (!options) return;
    event.preventDefault();
    event.stopPropagation();
    pendingConversationId = Number(options.dataset.conversationOptions);
    conversationActionsDialog?.showModal();
  });
  conversationActionsDialog
    ?.querySelector('[data-action-clear-conversation]')
    ?.addEventListener('click', () => {
      conversationActionsDialog.close();
      if (pendingConversationId) conversationClearDialog?.showModal();
    });
  conversationActionsDialog
    ?.querySelector('[data-action-cancel-conversation]')
    ?.addEventListener('click', () => conversationActionsDialog.close());
  conversationClearDialog
    ?.querySelector('[data-clear-cancel]')
    ?.addEventListener('click', () => conversationClearDialog.close());
  clearConversationConfirm?.addEventListener('click', async () => {
    if (!pendingConversationId || clearConversationConfirm.disabled) return;
    clearConversationConfirm.disabled = true;
    try {
      const response = await fetch(clearConversationUrl(pendingConversationId), {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': decodeURIComponent(csrfToken()),
        },
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Conversation could not be deleted.');
      conversationClearDialog.close();
      const activeId = Number(
        document.querySelector('.conversation-row.active')?.dataset.conversationId || 0,
      );
      await refreshConversationSidebar();
      document.dispatchEvent(new CustomEvent('messages:unread-changed'));
      if (activeId === pendingConversationId)
        window.location.assign(messagingLayout.dataset.conversationListUrl);
      pendingConversationId = null;
    } catch (error) {
      window.alert(error.message);
    } finally {
      clearConversationConfirm.disabled = false;
    }
  });
  const attachmentInput = document.querySelector('#message-attachment');
  const mediaAttachmentInput = document.querySelector('#message-media-attachment');
  const attachmentToggle = document.querySelector('#messaging-attachment-toggle');
  const attachmentMenu = document.querySelector('#messaging-attachment-menu');
  const attachmentPreview = document.querySelector('#messaging-attachment-preview');
  const attachmentWarning = document.querySelector('#messaging-attachment-warning');
  const messageInput = composeForm?.querySelector('textarea[name="body"]');
  const maxAttachmentSize = Number(composeForm?.dataset.maxAttachmentSize) || 0;
  const threadBottom = thread?.querySelector('.messaging-thread-bottom');
  let pendingAttachments = [];
  let isSubmitting = false;
  const scrollToLatest = () => {
    if (!thread) return;
    threadBottom?.scrollIntoView({ block: 'end', inline: 'nearest' });
    thread.scrollTop = thread.scrollHeight;
    requestAnimationFrame(() => {
      threadBottom?.scrollIntoView({ block: 'end', inline: 'nearest' });
      thread.scrollTop = thread.scrollHeight;
    });
  };
  const targetMessageId = new URLSearchParams(window.location.search).get('target_message');
  const focusMessage = (messageId) => {
    const row = thread?.querySelector(`[data-message-id="${messageId}"]`);
    if (!row) return false;
    row.scrollIntoView({ block: 'center', behavior: 'smooth' });
    row.classList.remove('messaging-message-target');
    requestAnimationFrame(() => row.classList.add('messaging-message-target'));
    window.setTimeout(() => row.classList.remove('messaging-message-target'), 2000);
    return true;
  };
  if (targetMessageId) requestAnimationFrame(() => focusMessage(targetMessageId));
  else {
    scrollToLatest();
    requestAnimationFrame(() => requestAnimationFrame(scrollToLatest));
    if (thread)
      thread.querySelectorAll('img').forEach((image) => {
        if (!image.complete) image.addEventListener('load', scrollToLatest, { once: true });
      });
  }

  const resizeMessageInput = () => {
    if (!messageInput) return;
    messageInput.style.height = 'auto';
    messageInput.style.height = `${Math.min(messageInput.scrollHeight, 120)}px`;
  };

  // On mobile, the on-screen keyboard shrinks the visible area without the
  // layout viewport (and 100dvh) reliably following it, which clips the
  // compose bar under the keyboard. Track the real visible height instead.
  if (window.visualViewport) {
    const setVisibleHeight = () => {
      document.documentElement.style.setProperty(
        '--messaging-vvh',
        `${window.visualViewport.height}px`,
      );
    };
    window.visualViewport.addEventListener('resize', setVisibleHeight);
    window.visualViewport.addEventListener('scroll', setVisibleHeight);
    setVisibleHeight();
  }
  messageInput?.addEventListener('focus', () => {
    // Give the keyboard time to open before re-measuring and scrolling.
    window.setTimeout(() => {
      messageInput.scrollIntoView({ block: 'end' });
      scrollToLatest();
    }, 250);
  });
  const messageSearchToggle = document.querySelector('#messaging-message-search-toggle');
  const messageSearchHeader = document.querySelector('#messaging-message-search-header');
  const normalChatHeader = document.querySelector('#messaging-chat-header-content');
  const messageSearchPanel = document.querySelector('#messaging-message-search-panel');
  const messageSearchInput = document.querySelector('#messaging-message-search-input');
  const messageSearchClose = document.querySelector('#messaging-message-search-close');
  const messageSearchPrevious = document.querySelector('#messaging-message-search-previous');
  const messageSearchNext = document.querySelector('#messaging-message-search-next');
  const messageSearchCounter = document.querySelector('#messaging-message-search-counter');
  const messageSearchStatus = document.querySelector('#messaging-message-search-status');
  const messageSearchResults = document.querySelector('#messaging-message-search-results');
  let messageSearchTimer = null;
  let messageSearchController = null;
  let messageSearchModeActive = false;
  let messageSearchResultsVisible = false;
  let selectedMessageSearchResultId = null;
  let messageSearchMatchIds = [];
  let currentMatchIndex = -1;
  let messageSearchResultsScrollTop = 0;
  const appendHighlightedText = (container, value, query) => {
    const lowerValue = value.toLowerCase();
    const lowerQuery = query.toLowerCase();
    let cursor = 0;
    let match = lowerValue.indexOf(lowerQuery);
    while (match !== -1) {
      container.append(document.createTextNode(value.slice(cursor, match)));
      const mark = document.createElement('mark');
      mark.textContent = value.slice(match, match + query.length);
      container.append(mark);
      cursor = match + query.length;
      match = lowerValue.indexOf(lowerQuery, cursor);
    }
    container.append(document.createTextNode(value.slice(cursor)));
  };
  const updateMessageSearchNavigation = () => {
    const hasMatches = messageSearchMatchIds.length > 0;
    const hasSelection = currentMatchIndex >= 0;
    messageSearchCounter.hidden = !hasMatches;
    messageSearchPrevious.hidden = !hasMatches;
    messageSearchNext.hidden = !hasMatches;
    messageSearchCounter.textContent = hasSelection
      ? `${currentMatchIndex + 1}/${messageSearchMatchIds.length}`
      : `${messageSearchMatchIds.length} results`;
    messageSearchPrevious.disabled =
      !hasSelection || currentMatchIndex >= messageSearchMatchIds.length - 1;
    messageSearchNext.disabled = !hasSelection || currentMatchIndex <= 0;
  };
  const renderMessageSearch = (payload) => {
    messageSearchMatchIds = payload.match_ids || payload.results.map((item) => item.id);
    if (!messageSearchMatchIds.includes(selectedMessageSearchResultId)) {
      selectedMessageSearchResultId = null;
      currentMatchIndex = -1;
    }
    updateMessageSearchNavigation();
    messageSearchResults.replaceChildren();
    messageSearchStatus.textContent = payload.count
      ? `${payload.count} match${payload.count === 1 ? '' : 'es'}`
      : `No messages found for “${payload.query}”`;
    payload.results.forEach((item) => {
      const result = document.createElement('button');
      result.type = 'button';
      result.className = 'messaging-message-search-result';
      const sender = document.createElement('strong');
      sender.textContent = item.sender_name;
      const snippet = document.createElement('span');
      appendHighlightedText(snippet, item.snippet, payload.query);
      const time = document.createElement('time');
      time.dateTime = item.created_at;
      time.textContent = new Date(item.created_at).toLocaleString([], {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      });
      if (item.id === selectedMessageSearchResultId) result.classList.add('is-selected');
      result.append(sender, snippet, time);
      result.addEventListener('click', () => selectMessageSearchResult(item.id));
      messageSearchResults.append(result);
    });
  };
  const showMessageSearchResults = () => {
    if (!messageSearchModeActive || !messageSearchPanel || messageSearchResultsVisible) return;
    messageSearchResultsVisible = true;
    messageSearchPanel.hidden = false;
    requestAnimationFrame(() => {
      messageSearchResults.scrollTop = messageSearchResultsScrollTop;
    });
  };
  const showMessageSearch = () => {
    if (!messageSearchPanel || !messageSearchHeader || !normalChatHeader) return;
    setDetailsOpen(false);
    messageSearchModeActive = true;
    messageSearchResultsVisible = true;
    normalChatHeader.hidden = true;
    messageSearchHeader.hidden = false;
    messageSearchPanel.hidden = false;
    messageSearchToggle?.setAttribute('aria-expanded', 'true');
    requestAnimationFrame(() => {
      messageSearchResults.scrollTop = messageSearchResultsScrollTop;
      messageSearchInput?.focus();
    });
  };
  const selectMessageSearchResult = (messageId) => {
    if (!messageSearchPanel || messageSearchPanel.hidden) return;
    selectedMessageSearchResultId = messageId;
    currentMatchIndex = messageSearchMatchIds.indexOf(messageId);
    updateMessageSearchNavigation();
    messageSearchResultsScrollTop = messageSearchResults.scrollTop;
    messageSearchInput?.blur();
    messageSearchPanel.classList.add('is-closing');
    window.setTimeout(() => {
      messageSearchPanel.hidden = true;
      messageSearchPanel.classList.remove('is-closing');
      messageSearchResultsVisible = false;
      focusMessage(messageId);
    }, 180);
  };
  const navigateMessageSearchMatch = (direction) => {
    const targetIndex = currentMatchIndex + direction;
    if (targetIndex < 0 || targetIndex >= messageSearchMatchIds.length) return;
    currentMatchIndex = targetIndex;
    selectedMessageSearchResultId = messageSearchMatchIds[targetIndex];
    updateMessageSearchNavigation();
    focusMessage(selectedMessageSearchResultId);
  };
  const closeMessageSearch = () => {
    if (!messageSearchModeActive || !messageSearchHeader || !normalChatHeader) return;
    if (!messageSearchPanel.hidden) messageSearchPanel.classList.add('is-closing');
    messageSearchHeader.classList.add('is-closing');
    window.setTimeout(() => {
      messageSearchPanel.hidden = true;
      messageSearchPanel.classList.remove('is-closing');
      messageSearchHeader.hidden = true;
      messageSearchHeader.classList.remove('is-closing');
      normalChatHeader.hidden = false;
      messageSearchModeActive = false;
      messageSearchResultsVisible = false;
      selectedMessageSearchResultId = null;
      messageSearchMatchIds = [];
      currentMatchIndex = -1;
      messageSearchResultsScrollTop = 0;
      messageSearchController?.abort();
      messageSearchInput.value = '';
      messageSearchResults.replaceChildren();
      messageSearchStatus.textContent = 'Type at least 2 characters to search.';
      updateMessageSearchNavigation();
      messageSearchToggle?.setAttribute('aria-expanded', 'false');
    }, 180);
  };
  messageSearchToggle?.addEventListener('click', showMessageSearch);
  messageSearchClose?.addEventListener('click', closeMessageSearch);
  messageSearchPrevious?.addEventListener('click', () => navigateMessageSearchMatch(1));
  messageSearchNext?.addEventListener('click', () => navigateMessageSearchMatch(-1));
  messageSearchInput?.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeMessageSearch();
  });
  messageSearchInput?.addEventListener('focus', () => {
    showMessageSearchResults();
  });
  messageSearchInput?.addEventListener('input', () => {
    const query = messageSearchInput.value.trim();
    window.clearTimeout(messageSearchTimer);
    messageSearchController?.abort();
    showMessageSearchResults();
    selectedMessageSearchResultId = null;
    messageSearchMatchIds = [];
    currentMatchIndex = -1;
    updateMessageSearchNavigation();
    if (query.length < 2) {
      messageSearchResults.replaceChildren();
      messageSearchStatus.textContent = 'Type at least 2 characters to search.';
      return;
    }
    messageSearchStatus.textContent = 'Searching messages…';
    messageSearchTimer = window.setTimeout(async () => {
      messageSearchController = new AbortController();
      try {
        const response = await fetch(
          `${messageSearchPanel.dataset.searchUrl}?q=${encodeURIComponent(query)}`,
          {
            headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            signal: messageSearchController.signal,
          },
        );
        if (!response.ok || messageSearchInput.value.trim() !== query) return;
        renderMessageSearch(await response.json());
      } catch (error) {
        if (error.name !== 'AbortError')
          messageSearchStatus.textContent = 'Message search is unavailable.';
      }
    }, 300);
  });
  const renderAttachmentPreviews = () => {
    attachmentPreview.replaceChildren();
    attachmentPreview.hidden = !pendingAttachments.length;
    pendingAttachments.forEach((file, index) => {
      const preview = document.createElement('div');
      preview.className = 'messaging-attachment-preview-card';
      if (file.type.startsWith('image/')) {
        const image = document.createElement('img');
        image.className = 'messaging-attachment-preview-image';
        image.alt = file.name;
        image.src = URL.createObjectURL(file);
        preview.append(image);
      } else {
        const icon = document.createElement('i');
        icon.className = `bi ${file.type.startsWith('video/') ? 'bi-play-circle' : 'bi-file-earmark-text'} messaging-attachment-preview-icon`;
        icon.setAttribute('aria-hidden', 'true');
        preview.append(icon);
      }
      const name = document.createElement('span');
      name.className = 'messaging-attachment-preview-name';
      name.textContent = file.name;
      preview.append(name);
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'messaging-attachment-preview-remove';
      remove.setAttribute('aria-label', `Remove ${file.name}`);
      remove.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>';
      remove.addEventListener('click', () => {
        pendingAttachments.splice(index, 1);
        renderAttachmentPreviews();
      });
      preview.append(remove);
      attachmentPreview.append(preview);
    });
  };
  const clearAttachmentPreview = () => {
    pendingAttachments = [];
    renderAttachmentPreviews();
  };
  const clearAttachmentWarning = () => {
    if (!attachmentWarning) return;
    attachmentWarning.replaceChildren();
    attachmentWarning.hidden = true;
  };
  const showAttachmentWarning = (messages) => {
    if (!attachmentWarning) return;
    attachmentWarning.replaceChildren();
    messages.forEach((message) => {
      const line = document.createElement('span');
      line.textContent = message;
      attachmentWarning.appendChild(line);
    });
    attachmentWarning.hidden = !messages.length;
  };
  const maxAttachmentSizeLabel = () => `${Math.round(maxAttachmentSize / (1024 * 1024))} MB`;

  if (!attachmentInput || !attachmentPreview) return;

  resizeMessageInput();
  const typingIndicator = thread?.parentElement?.querySelector('.messaging-typing');
  const typingConversationId =
    thread?.dataset.pollUrl?.match(/messages\/(\d+)\/new/)?.[1] || 'unknown';
  const typingElementState = () => {
    if (!typingIndicator) return { exists: false };
    const style = window.getComputedStyle(typingIndicator);
    return {
      exists: true,
      hidden: typingIndicator.hidden,
      hasHiddenAttribute: typingIndicator.hasAttribute('hidden'),
      display: style.display,
      visibility: style.visibility,
      opacity: style.opacity,
    };
  };
  const typingLog = (prefix, event, details = {}) => {
    console.log(`${prefix} ${event}`, {
      conversation: typingConversationId,
      time: new Date().toISOString(),
      ...details,
    });
  };
  if (typingIndicator) {
    new MutationObserver((mutations) => {
      mutations.forEach((mutation) =>
        typingLog('[TYPE-DOM-MUTATION]', 'ATTRIBUTE', {
          attribute: mutation.attributeName,
          oldValue: mutation.oldValue,
          state: typingElementState(),
        }),
      );
    }).observe(typingIndicator, {
      attributes: true,
      attributeOldValue: true,
      attributeFilter: ['hidden', 'class', 'style'],
    });
  }
  const TYPING_THROTTLE_MS = 1000;
  const TYPING_IDLE_MS = 2500;
  const OTHER_TYPING_UI_TIMEOUT_MS = 4000;
  let typingTimer = null;
  let otherTypingExpiryTimer = null;
  let lastTypingActivityPost = 0;
  let typingSequence = 0;
  const createTypingClientSessionId = () => {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
    const bytes = new Uint8Array(16);
    if (window.crypto?.getRandomValues) window.crypto.getRandomValues(bytes);
    else
      for (let index = 0; index < bytes.length; index += 1)
        bytes[index] = Math.floor(Math.random() * 256);
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = [...bytes].map((byte) => byte.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  };
  const typingClientSessionId = createTypingClientSessionId();
  let typingActive = false;
  let typingRequestQueue = Promise.resolve();
  let debugLastTypingTrueAt = null;
  const queueTypingState = (typing, reason) => {
    if (!thread?.dataset.typingUrl) return Promise.resolve();
    const sequence = ++typingSequence;
    const body = `typing=${typing ? '1' : '0'}&sequence=${sequence}&client_session_id=${encodeURIComponent(typingClientSessionId)}`;
    typingLog('[TYPE-SENDER]', 'QUEUE', {
      typing,
      reason,
      sequence,
      clientSession: typingClientSessionId,
    });
    typingRequestQueue = typingRequestQueue
      .catch(() => {})
      .then(async () => {
        debugMessaging(`[typing] ${typing ? 'ACTIVITY' : 'STOP'} POST`, { sequence, reason });
        try {
          typingLog('[TYPE-SENDER]', 'REQUEST', { typing, reason, sequence });
          const response = await fetch(thread.dataset.typingUrl, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
              'X-CSRFToken': composeForm.querySelector('[name=csrfmiddlewaretoken]').value,
              'X-Requested-With': 'XMLHttpRequest',
              'Content-Type': 'application/x-www-form-urlencoded',
            },
            body,
          });
          typingLog('[TYPE-SENDER]', 'RESPONSE', {
            typingSent: typing,
            reason,
            sequence,
            status: response.status,
            ok: response.ok,
          });
        } catch (error) {
          typingLog('[TYPE-SENDER]', 'ERROR', {
            typingSent: typing,
            reason,
            sequence,
            error: String(error),
          });
          // Freshness remains authoritative even when an explicit stop cannot be delivered.
        }
      });
    return typingRequestQueue;
  };
  const stopTyping = (reason = 'stop') => {
    window.clearTimeout(typingTimer);
    typingTimer = null;
    typingLog('[TYPE-SENDER]', 'STOP', {
      reason,
      wasActive: typingActive,
      nextSequence: typingSequence + 1,
    });
    if (!typingActive) return;
    typingActive = false;
    lastTypingActivityPost = 0;
    queueTypingState(false, reason);
  };
  const setOtherTyping = (typing) => {
    if (!typingIndicator) return;
    const hadExpiryTimer = Boolean(otherTypingExpiryTimer);
    typingLog('[TYPE-UI]', 'BEFORE', {
      requestedState: typing,
      expiryTimerExists: hadExpiryTimer,
      state: typingElementState(),
    });
    const changed = typingIndicator.hidden === Boolean(typing);
    typingIndicator.hidden = !typing;
    if (hadExpiryTimer) {
      typingLog('[TYPE-EXPIRY]', 'CLEAR', {
        reason: typing ? 'new-true-confirmation' : 'server-false',
      });
    }
    window.clearTimeout(otherTypingExpiryTimer);
    otherTypingExpiryTimer = null;
    if (typing) {
      const previousTrueConfirmation = debugLastTypingTrueAt;
      debugLastTypingTrueAt = Date.now();
      typingLog('[TYPE-UI]', 'TRUE CONFIRMATION', {
        previousTrueConfirmation,
        elapsedSincePreviousMs: previousTrueConfirmation
          ? debugLastTypingTrueAt - previousTrueConfirmation
          : null,
      });
      const scheduledAt = new Date().toISOString();
      typingLog('[TYPE-EXPIRY]', 'SCHEDULE', {
        delay: OTHER_TYPING_UI_TIMEOUT_MS,
        trigger: 'server-true',
        previousTimerExisted: hadExpiryTimer,
      });
      // A failed chat poll must not leave a previously visible
      // indicator on screen forever. Successful true responses
      // renew this UI deadline while the other user is active.
      otherTypingExpiryTimer = window.setTimeout(() => {
        typingLog('[TYPE-EXPIRY]', 'FIRED', {
          scheduledAt,
          currentConversation: typingConversationId,
          stateBefore: typingElementState(),
        });
        typingIndicator.hidden = true;
        typingLog('[TYPE-EXPIRY]', 'AFTER HIDE', { state: typingElementState() });
        debugMessaging('[typing] UI expiry');
      }, OTHER_TYPING_UI_TIMEOUT_MS);
    }
    debugMessaging('[typing] POLL RESULT', typing);
    typingLog('[TYPE-UI]', 'AFTER', {
      requestedState: typing,
      expiryTimerExists: Boolean(otherTypingExpiryTimer),
      state: typingElementState(),
    });
    if (typing && changed && thread.scrollHeight - thread.scrollTop - thread.clientHeight < 96)
      scrollToLatest();
  };
  messageInput?.addEventListener('input', () => {
    resizeMessageInput();
    typingLog('[TYPE-SENDER]', 'INPUT', {
      valueLength: messageInput.value.length,
      editing: Boolean(editingMessageId),
    });
    if (editingMessageId) {
      stopTyping('editing');
      return;
    }
    const hasText = Boolean(messageInput.value.trim());
    window.clearTimeout(typingTimer);
    if (!hasText) {
      stopTyping('empty input');
      return;
    }
    debugMessaging('[typing] INPUT');
    const now = Date.now();
    if (!typingActive || now - lastTypingActivityPost >= TYPING_THROTTLE_MS) {
      typingActive = true;
      lastTypingActivityPost = now;
      queueTypingState(true, 'input');
    }
    typingLog('[TYPE-SENDER]', 'IDLE TIMER SCHEDULED', { delay: TYPING_IDLE_MS });
    typingTimer = window.setTimeout(() => {
      typingLog('[TYPE-SENDER]', 'IDLE TIMER FIRED');
      stopTyping('idle');
    }, TYPING_IDLE_MS);
  });
  messageInput?.addEventListener('blur', () => stopTyping('blur'));
  messageInput?.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return;
    event.preventDefault();
    if (!isSubmitting) composeForm.requestSubmit();
  });

  const addPickedAttachments = (input) => {
    const selectedFiles = [...input.files];
    const oversizedFiles = maxAttachmentSize
      ? selectedFiles.filter((file) => file.size > maxAttachmentSize)
      : [];
    const acceptedFiles = maxAttachmentSize
      ? selectedFiles.filter((file) => file.size <= maxAttachmentSize)
      : selectedFiles;
    pendingAttachments.push(...acceptedFiles);
    renderAttachmentPreviews();
    if (oversizedFiles.length) {
      showAttachmentWarning(
        oversizedFiles.map(
          (file) => `${file.name} is too large. Maximum file size is ${maxAttachmentSizeLabel()}.`,
        ),
      );
    } else {
      clearAttachmentWarning();
    }
    input.value = '';
  };
  attachmentInput.addEventListener('change', () => addPickedAttachments(attachmentInput));
  mediaAttachmentInput?.addEventListener('change', () =>
    addPickedAttachments(mediaAttachmentInput),
  );
  const closeAttachmentMenu = () => {
    attachmentMenu.hidden = true;
    attachmentToggle.setAttribute('aria-expanded', 'false');
  };
  attachmentToggle?.addEventListener('click', () => {
    stopTyping('attachment menu');
    const open = attachmentMenu.hidden;
    attachmentMenu.hidden = !open;
    attachmentToggle.setAttribute('aria-expanded', String(open));
  });
  attachmentMenu?.addEventListener('click', (event) => {
    const option = event.target.closest('[data-attachment-picker]');
    if (!option) return;
    closeAttachmentMenu();
    (option.dataset.attachmentPicker === 'media' ? mediaAttachmentInput : attachmentInput).click();
  });
  document.addEventListener('click', (event) => {
    if (!attachmentMenu?.hidden && !event.target.closest('.messaging-attachment-menu-wrap'))
      closeAttachmentMenu();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeAttachmentMenu();
  });
  document.addEventListener('click', (event) => {
    if (event.target.closest('.conversation-row')) stopTyping('conversation switch');
  });

  const appendLinkedText = (container, text) => {
    const urlPattern =
      /\b(?:https?:\/\/|www\.|(?:[a-z0-9-]+\.)+(?:com|org|net|edu|gov|io|co|uk|ph|dev|app|info|me|tv|gg|ai|us|ca|de|jp|fr|au|news|site|online|store))[^\s<]*/gi;
    const trailingPunctuation = /[.,!?;:]+$/;
    const trimUrlPunctuation = (url) => {
      let trimmed = url.replace(trailingPunctuation, '');
      for (const [opening, closing] of [
        ['(', ')'],
        ['[', ']'],
      ]) {
        while (
          trimmed.endsWith(closing) &&
          [...trimmed].filter((character) => character === closing).length >
            [...trimmed].filter((character) => character === opening).length
        ) {
          trimmed = trimmed.slice(0, -1);
        }
      }
      return trimmed;
    };
    let cursor = 0;
    for (const match of text.matchAll(urlPattern)) {
      const matchedUrl = match[0];
      const urlText = trimUrlPunctuation(matchedUrl);
      const index = match.index;
      if (!urlText) continue;
      container.append(document.createTextNode(text.slice(cursor, index)));
      const href = /^https?:\/\//i.test(urlText) ? urlText : `https://${urlText}`;
      try {
        const parsedUrl = new URL(href);
        if (!['http:', 'https:'].includes(parsedUrl.protocol))
          throw new Error('Unsupported URL protocol');
        const link = document.createElement('a');
        link.href = parsedUrl.href;
        link.target = '_blank';
        link.rel = 'noopener noreferrer nofollow';
        link.textContent = urlText;
        container.append(link);
      } catch (_) {
        container.append(document.createTextNode(urlText));
      }
      cursor = index + urlText.length;
    }
    container.append(document.createTextNode(text.slice(cursor)));
  };

  const firstPreviewUrl = (text) => {
    const urls = [
      ...text.matchAll(
        /\b(?:https?:\/\/|www\.|(?:[a-z0-9-]+\.)+(?:com|org|net|edu|gov|io|co|uk|ph|dev|app|info|me|tv|gg|ai|us|ca|de|jp|fr|au|news|site|online|store))[^\s<]*/gi,
      ),
    ]
      .map((match) => match[0].replace(/[.,!?;:)\]]+$/, ''))
      .map((url) => (/^https?:\/\//i.test(url) ? url : `https://${url}`));
    const isAssetUrl = (url) => {
      try {
        const parsed = new URL(url);
        return (
          /\.(?:png|jpe?g|gif|webp|svg|ico)$/i.test(parsed.pathname) ||
          /\/(?:emoji|emoticons?)\//i.test(parsed.pathname) ||
          /(?:fbcdn|static|cdn|doubleclick)/i.test(parsed.hostname)
        );
      } catch (_) {
        return true;
      }
    };
    return urls.find((url) => !isAssetUrl(url)) || urls[0] || '';
  };
  const renderLinkPreview = (messageRow, preview) => {
    if (!preview || messageRow.querySelector('.messaging-link-preview')) return;
    const bubble = messageRow.querySelector('.messaging-bubble');
    if (!bubble) return;
    bubble.classList.add('messaging-bubble-has-preview');
    const card = document.createElement('a');
    card.className = 'messaging-link-preview';
    card.href = preview.url;
    card.target = '_blank';
    card.rel = 'noopener noreferrer nofollow';
    const media = document.createElement('span');
    media.className = 'messaging-link-preview-media';
    const renderPreviewFallback = () => {
      media.replaceChildren();
      media.classList.add('placeholder');
      if (preview.favicon) {
        const favicon = document.createElement('img');
        favicon.className = 'messaging-link-preview-fallback-icon';
        favicon.src = preview.favicon;
        favicon.alt = '';
        favicon.addEventListener('error', () => favicon.remove(), { once: true });
        media.appendChild(favicon);
      } else {
        const icon = document.createElement('i');
        icon.className = 'bi bi-link-45deg';
        icon.setAttribute('aria-hidden', 'true');
        media.appendChild(icon);
      }
    };
    if (preview.image) {
      const image = document.createElement('img');
      image.className = 'messaging-link-preview-image';
      image.src = preview.image;
      image.alt = '';
      image.addEventListener('error', renderPreviewFallback, { once: true });
      media.appendChild(image);
    } else {
      renderPreviewFallback();
    }
    card.appendChild(media);
    const copy = document.createElement('span');
    copy.className = 'messaging-link-preview-copy';
    const title = document.createElement('strong');
    title.textContent = preview.title;
    copy.appendChild(title);
    const site = document.createElement('span');
    site.className = 'messaging-link-preview-site';
    site.textContent = preview.site_name;
    copy.appendChild(site);
    if (preview.description) {
      const description = document.createElement('span');
      description.className = 'messaging-link-preview-description';
      description.textContent = preview.description;
      copy.appendChild(description);
    }
    card.appendChild(copy);
    bubble.appendChild(card);
  };
  const loadLinkPreview = async (messageRow, text) => {
    const url = firstPreviewUrl(text);
    if (!url || messageRow.dataset.previewRequested) return;
    const shouldKeepAtLatest =
      !targetMessageId && thread.scrollHeight - thread.scrollTop - thread.clientHeight < 96;
    messageRow.dataset.previewRequested = 'true';
    try {
      const response = await fetch(
        `${thread.dataset.linkPreviewUrl}?url=${encodeURIComponent(url)}`,
      );
      if (!response.ok) return;
      const payload = await response.json();
      renderLinkPreview(messageRow, payload.preview);
      if (shouldKeepAtLatest) scrollToLatest();
    } catch (_) {
      // Leave the normal clickable URL in place when metadata is unavailable.
    }
  };

  const currentUserId = Number(composeForm?.dataset.currentUser);
  const renderedMessageIds = new Set(
    [...thread.querySelectorAll('[data-message-id]')].map((row) => Number(row.dataset.messageId)),
  );
  let lastMessageId = Math.max(0, ...renderedMessageIds);
  let messageRevisionCursor = Number(thread.dataset.revisionCursor) || 0;
  let lastSentReadMessageId = 0;
  let seenMarker = thread.querySelector('.messaging-seen-avatar') || null;
  let currentSeenMessageId =
    Number(seenMarker?.closest('[data-message-id]')?.dataset.messageId) || 0;
  const updateSeenMarker = (cursorId) => {
    const rows = [...thread.querySelectorAll('.messaging-message-row.own[data-message-id]')];
    const target = rows.filter((row) => Number(row.dataset.messageId) <= Number(cursorId)).at(-1);
    if (!target) return;
    const targetId = Number(target.dataset.messageId);
    if (targetId < currentSeenMessageId) return;
    if (targetId === currentSeenMessageId && seenMarker?.parentElement === target) return;
    const moved = currentSeenMessageId > 0 && targetId !== currentSeenMessageId;
    if (!seenMarker) {
      seenMarker = document.createElement('img');
      seenMarker.className = 'messaging-seen-avatar';
      seenMarker.src = thread.dataset.otherAvatar;
      seenMarker.alt = 'Seen';
      seenMarker.title = 'Seen';
    }
    target.appendChild(seenMarker);
    currentSeenMessageId = targetId;
    if (moved) {
      seenMarker.classList.remove('is-seen-enter');
      void seenMarker.offsetWidth;
      seenMarker.classList.add('is-seen-enter');
    }
  };
  thread.addEventListener('animationend', (event) => {
    if (event.target === seenMarker && event.animationName === 'messaging-reply-in') {
      seenMarker.classList.remove('is-seen-enter');
    }
  });
  const markVisibleRead = async () => {
    if (!canMarkConversationRead() || !thread.dataset.readUrl) return;
    const newest = [...thread.querySelectorAll('.messaging-message-row[data-message-id]')].at(-1);
    const id = Number(newest?.dataset.messageId);
    if (!id || id <= lastSentReadMessageId) return;
    lastSentReadMessageId = id;
    try {
      await fetch(thread.dataset.readUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': composeForm.querySelector('[name=csrfmiddlewaretoken]').value,
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `last_read_message_id=${encodeURIComponent(id)}`,
      });
    } catch (_) {
      lastSentReadMessageId = 0;
    }
  };
  const unsendDialog = document.querySelector('#messaging-unsend-dialog');
  const actionsDialog = document.querySelector('#messaging-actions-dialog');
  const unsendConfirm = unsendDialog?.querySelector('.messaging-unsend-confirm');
  const unsendCancel = unsendDialog?.querySelector('button[value="cancel"]');
  let pendingDeleteMessageId = null;
  let deleteTrigger = null;
  let actionMessageId = null;
  let editingMessageId = null;
  const editState = document.querySelector('#messaging-edit-state');
  const cancelEdit = document.querySelector('#messaging-cancel-edit');
  const replyState = document.querySelector('#messaging-reply-state');
  const replyInput = document.querySelector('#messaging-reply-to-message-id');
  const replyName = document.querySelector('#messaging-reply-name');
  const replyPreview = document.querySelector('#messaging-reply-preview');
  const replyPreviewThumb = document.querySelector('#messaging-reply-preview-thumb');
  const cancelReply = document.querySelector('#messaging-cancel-reply');
  const clearReply = () => {
    if (replyInput) replyInput.value = '';
    if (replyState) replyState.hidden = true;
    if (replyPreviewThumb) replyPreviewThumb.hidden = true;
  };
  const selectReply = (row) => {
    if (!row || !replyInput) return;
    replyInput.value = row.dataset.messageId;
    replyName.textContent = `Replying to ${row.dataset.senderName || 'message'}`;
    const bodyText = row.querySelector('.messaging-bubble p')?.textContent?.trim();
    const imageAttachment = row.querySelector('.messaging-image-attachment img');
    if (replyPreviewThumb) {
      replyPreviewThumb.hidden = !imageAttachment;
      replyPreviewThumb.src = imageAttachment ? imageAttachment.src : '';
    }
    replyPreview.textContent =
      bodyText ||
      (imageAttachment
        ? 'Photo'
        : row.querySelector('.messaging-attachment-bubble')
          ? 'Attachment'
          : 'Message');
    replyState.hidden = false;
    messageInput?.focus();
  };
  cancelReply?.addEventListener('click', clearReply);
  const senderDeletedText = (payload) => `${payload.sender_name || 'This user'} deleted a message`;
  const setEditActionVisibility = (hasBody) => {
    const editAction = actionsDialog?.querySelector('[data-action-edit]');
    if (editAction) editAction.hidden = !hasBody;
  };
  const setMobileActionVisibility = (row) => {
    const isOwn = row?.classList.contains('own');
    const hasBody = row?.dataset.messageHasBody === 'true';
    actionsDialog?.querySelector('[data-action-copy]') &&
      (actionsDialog.querySelector('[data-action-copy]').hidden = !hasBody);
    actionsDialog?.querySelector('[data-action-edit]') &&
      (actionsDialog.querySelector('[data-action-edit]').hidden = !isOwn || !hasBody);
    actionsDialog?.querySelector('[data-action-unsend]') &&
      (actionsDialog.querySelector('[data-action-unsend]').hidden = !isOwn);
  };
  const renderDeletedMessage = (payload) => {
    const messageRow = thread.querySelector(`[data-message-id="${payload.id}"]`);
    const content = messageRow?.querySelector('.messaging-message-content');
    if (!messageRow || !content) return false;
    content.replaceChildren();
    const bubble = document.createElement('article');
    bubble.className = `messaging-bubble${messageRow.classList.contains('own') ? ' own' : ''} messaging-bubble-deleted`;
    const notice = document.createElement('p');
    notice.className = 'messaging-deleted-notice';
    notice.textContent = senderDeletedText(payload);
    bubble.appendChild(notice);
    content.appendChild(bubble);
    messageRow.dataset.messageHasBody = 'false';
    messageRow.querySelector('.messaging-message-action')?.remove();
    delete messageRow.dataset.previewRequested;
    return true;
  };
  const addDeleteAction = (messageRow, messageId, hasBody) => {
    const action = document.createElement('button');
    action.type = 'button';
    action.className = 'messaging-message-action';
    action.dataset.messageOptions = String(messageId);
    action.dataset.messageHasBody = String(hasBody);
    action.setAttribute('aria-label', 'Message options');
    action.title = 'Message options';
    action.innerHTML = '<i class="bi bi-three-dots" aria-hidden="true"></i>';
    messageRow.appendChild(action);
  };
  const createAttachmentBubble = (attachment, wasNearBottom) => {
    const attachmentLink = document.createElement('a');
    attachmentLink.href = attachment.url;
    attachmentLink.target = '_blank';
    attachmentLink.rel = 'noopener noreferrer';
    if (attachment.is_image) {
      attachmentLink.className = 'messaging-attachment-bubble messaging-image-attachment';
      attachmentLink.dataset.mediaUrl = attachment.url;
      attachmentLink.dataset.mediaName = attachment.name || '';
      const image = document.createElement('img');
      image.src = attachment.url;
      image.alt = attachment.name || 'Attachment';
      if (wasNearBottom) image.addEventListener('load', scrollToLatest, { once: true });
      attachmentLink.appendChild(image);
      return attachmentLink;
    }
    attachmentLink.className = 'messaging-attachment-bubble messaging-file-attachment';
    const icon = document.createElement('i');
    icon.className = `bi ${attachment.is_video ? 'bi-play-circle' : 'bi-paperclip'}`;
    icon.setAttribute('aria-hidden', 'true');
    const name = document.createElement('span');
    name.textContent = attachment.name || 'Attachment';
    attachmentLink.append(icon, name);
    return attachmentLink;
  };
  const appendMessage = (payload, forceScroll = false) => {
    const messageId = Number(payload.id);
    if (!messageId) return false;
    if (renderedMessageIds.has(messageId)) {
      if (payload.is_deleted) renderDeletedMessage(payload);
      return false;
    }

    const isOwnMessage = Number(payload.sender_id) === currentUserId;
    const wasNearBottom =
      forceScroll || thread.scrollHeight - thread.scrollTop - thread.clientHeight < 96;
    const messageRow = document.createElement('div');
    messageRow.className = `messaging-message-row${isOwnMessage ? ' own' : ''}`;
    messageRow.dataset.messageId = String(messageId);
    messageRow.dataset.messageHasBody = String(Boolean(payload.body));
    messageRow.dataset.senderName = payload.sender_name || 'message';
    if (!isOwnMessage) {
      const avatar = document.createElement('img');
      avatar.className = 'messaging-message-avatar';
      avatar.src = payload.sender_avatar_url;
      avatar.alt = '';
      messageRow.appendChild(avatar);
    }
    const content = document.createElement('div');
    content.className = 'messaging-message-content';
    if (payload.is_deleted) {
      const bubble = document.createElement('article');
      bubble.className = `messaging-bubble${isOwnMessage ? ' own' : ''} messaging-bubble-deleted`;
      bubble.classList.add('messaging-bubble-deleted');
      const notice = document.createElement('p');
      notice.className = 'messaging-deleted-notice';
      notice.textContent = senderDeletedText(payload);
      bubble.appendChild(notice);
      content.appendChild(bubble);
    } else if (payload.reply) {
      const quote = document.createElement('button');
      quote.type = 'button';
      quote.className = `messaging-reply-quote${payload.reply.unavailable ? ' unavailable' : ''}`;
      if (!payload.reply.unavailable) quote.dataset.replyJump = String(payload.reply.message_id);
      if (
        !payload.reply.unavailable &&
        payload.reply.attachment_is_image &&
        payload.reply.attachment_url
      ) {
        const thumb = document.createElement('img');
        thumb.className = 'messaging-reply-quote-thumb';
        thumb.src = payload.reply.attachment_url;
        thumb.alt = '';
        quote.appendChild(thumb);
      }
      const text = document.createElement('span');
      text.className = 'messaging-reply-quote-text';
      const title = document.createElement('strong');
      title.textContent = payload.reply.unavailable
        ? 'Message unavailable'
        : payload.reply.sender_name;
      text.appendChild(title);
      if (!payload.reply.unavailable) {
        const snippet = document.createElement('span');
        snippet.textContent =
          payload.reply.body ||
          (payload.reply.attachment_is_image
            ? 'Photo'
            : payload.reply.attachment_count
              ? 'Attachment'
              : 'Message');
        text.appendChild(snippet);
      }
      quote.appendChild(text);
      content.appendChild(quote);
    }
    if (!payload.is_deleted && payload.body) {
      const bubble = document.createElement('article');
      bubble.className = `messaging-bubble${isOwnMessage ? ' own' : ''}`;
      const body = document.createElement('p');
      appendLinkedText(body, payload.body);
      bubble.appendChild(body);
      content.appendChild(bubble);
    }
    const attachments = payload.attachments?.length
      ? payload.attachments
      : payload.attachment_url
        ? [
            {
              url: payload.attachment_url,
              name: payload.attachment_name,
              is_image: payload.attachment_is_image,
            },
          ]
        : [];
    if (!payload.is_deleted && attachments.length) {
      const attachmentBubbles = document.createElement('div');
      attachmentBubbles.className = 'messaging-attachment-bubbles';
      attachments.forEach((attachment) =>
        attachmentBubbles.appendChild(createAttachmentBubble(attachment, wasNearBottom)),
      );
      content.appendChild(attachmentBubbles);
    }
    messageRow.appendChild(content);
    const meta = document.createElement('span');
    meta.className = 'messaging-message-meta';
    const time = document.createElement('time');
    time.dateTime = payload.created_at;
    time.textContent = new Date(payload.created_at).toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
    meta.appendChild(time);
    if (payload.is_edited) {
      meta.append(' · ');
      const edited = document.createElement('button');
      edited.type = 'button';
      edited.className = 'messaging-edited-indicator';
      edited.dataset.historyMessage = String(messageId);
      edited.textContent = 'Edited';
      meta.appendChild(edited);
    }
    messageRow.appendChild(meta);
    if (!payload.is_deleted) {
      const reply = document.createElement('button');
      reply.type = 'button';
      reply.className = 'messaging-reply-action';
      reply.dataset.replyMessage = String(messageId);
      reply.setAttribute('aria-label', 'Reply to message');
      reply.innerHTML = '<i class="bi bi-reply-fill" aria-hidden="true"></i>';
      messageRow.appendChild(reply);
    }
    thread.appendChild(messageRow);
    renderedMessageIds.add(messageId);
    lastMessageId = Math.max(lastMessageId, messageId);
    if (isOwnMessage && !payload.is_deleted)
      addDeleteAction(messageRow, messageId, Boolean(payload.body));
    if (!payload.is_deleted) loadLinkPreview(messageRow, payload.body || '');
    if (wasNearBottom) scrollToLatest();
    return true;
  };
  const patchUpdatedMessage = (payload) => {
    const messageRow = thread.querySelector(`[data-message-id="${payload.id}"]`);
    const content = messageRow?.querySelector('.messaging-message-content');
    if (!messageRow || !content || payload.is_deleted) return false;

    let bubble = [...content.children].find((element) =>
      element.classList.contains('messaging-bubble'),
    );
    if (!bubble) {
      bubble = document.createElement('article');
      bubble.className = `messaging-bubble${messageRow.classList.contains('own') ? ' own' : ''}`;
      content.insertBefore(bubble, content.firstChild);
    }
    let body = bubble.querySelector('p');
    if (!body) {
      body = document.createElement('p');
      bubble.prepend(body);
    }
    body.replaceChildren();
    appendLinkedText(body, payload.body || '');
    bubble.querySelectorAll('.messaging-link-preview').forEach((preview) => preview.remove());
    delete messageRow.dataset.previewRequested;
    messageRow.dataset.messageHasBody = String(Boolean(payload.body));

    const meta = messageRow.querySelector('.messaging-message-meta');
    if (payload.is_edited && meta && !meta.querySelector('.messaging-edited-indicator')) {
      meta.append(document.createTextNode(' · '));
      const edited = document.createElement('button');
      edited.type = 'button';
      edited.className = 'messaging-edited-indicator';
      edited.dataset.historyMessage = String(payload.id);
      edited.textContent = 'Edited';
      meta.appendChild(edited);
    }
    loadLinkPreview(messageRow, payload.body || '');
    return true;
  };

  thread.addEventListener('click', (event) => {
    const replyJump = event.target.closest('[data-reply-jump]');
    if (replyJump) {
      const target = thread.querySelector(`[data-message-id="${replyJump.dataset.replyJump}"]`);
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        target.classList.add('messaging-message-target');
        window.setTimeout(() => target.classList.remove('messaging-message-target'), 1800);
      }
      return;
    }
    const replyAction = event.target.closest('[data-reply-message]');
    if (replyAction) {
      selectReply(replyAction.closest('.messaging-message-row'));
      return;
    }
    const history = event.target.closest('[data-history-message]');
    if (history) {
      const url = thread.dataset.historyUrlTemplate.replace(
        '/0/',
        `/${history.dataset.historyMessage}/`,
      );
      fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then((response) => response.json())
        .then((payload) => {
          thread.querySelectorAll('.messaging-inline-history').forEach((item) => item.remove());
          const row = history.closest('.messaging-message-row');
          const stack = document.createElement('div');
          stack.className = 'messaging-inline-history';
          const hide = document.createElement('button');
          hide.type = 'button';
          hide.className = 'messaging-hide-edits';
          hide.textContent = 'Hide edits';
          hide.addEventListener('click', () => stack.remove());
          stack.appendChild(hide);
          payload.history.slice(0, -1).forEach((body) => {
            const bubble = document.createElement('p');
            bubble.className = 'messaging-history-bubble';
            bubble.textContent = body;
            stack.appendChild(bubble);
          });
          row.insertBefore(stack, row.querySelector('.messaging-message-content'));
        });
      return;
    }
    const options = event.target.closest('[data-message-options]');
    if (options) {
      actionMessageId = Number(options.dataset.messageOptions);
      deleteTrigger = options;
      setEditActionVisibility(options.dataset.messageHasBody === 'true');
      actionsDialog?.showModal();
      return;
    }
    const action = event.target.closest('[data-delete-message]');
    if (!action) return;
    pendingDeleteMessageId = Number(action.dataset.deleteMessage);
    deleteTrigger = action;
    if (unsendDialog?.showModal) {
      unsendDialog.showModal();
      unsendCancel?.focus();
    } else if (window.confirm('Unsend this message for everyone?')) unsendConfirm?.click();
  });
  let longPressTimer = null;
  let touchStart = null;
  let suppressAttachmentClick = false;
  thread.addEventListener(
    'click',
    (event) => {
      const attachment = event.target.closest('.messaging-attachment-bubble');
      if (!attachment) return;
      if (suppressAttachmentClick) {
        event.preventDefault();
        event.stopPropagation();
      } else if (attachment.classList.contains('messaging-image-attachment')) {
        // Images open in the in-page viewer instead of leaving the chat; files still open normally.
        event.preventDefault();
      }
    },
    true,
  );
  thread.addEventListener('contextmenu', (event) => {
    if (mobileBreakpoint.matches && event.target.closest('.messaging-attachment-bubble'))
      event.preventDefault();
  });
  thread.addEventListener('pointerdown', (event) => {
    const control = event.target.closest('a, button');
    if (
      !mobileBreakpoint.matches ||
      event.pointerType !== 'touch' ||
      (control && !control.classList.contains('messaging-attachment-bubble'))
    )
      return;
    suppressAttachmentClick = false;
    const row = event.target.closest('.messaging-message-row[data-message-id]');
    if (!row) return;
    row.classList.add('is-held');
    touchStart = {
      x: event.clientX,
      y: event.clientY,
      id: row.dataset.messageId,
      row,
      swiping: false,
      armed: false,
    };
    longPressTimer = window.setTimeout(() => {
      actionMessageId = Number(touchStart.id);
      setMobileActionVisibility(row);
      actionsDialog?.showModal();
      suppressAttachmentClick = true;
      longPressTimer = null;
    }, 450);
  });
  thread.addEventListener('pointermove', (event) => {
    if (!touchStart) return;
    const dx = event.clientX - touchStart.x,
      dy = event.clientY - touchStart.y;
    if (!touchStart.swiping && Math.hypot(dx, dy) > 10) {
      clearTimeout(longPressTimer);
      longPressTimer = null;
    }
    if (dx > 8 && Math.abs(dx) > Math.abs(dy)) {
      touchStart.swiping = true;
      suppressAttachmentClick = true;
      const move = Math.min(68, dx * 0.72);
      touchStart.row.classList.add('is-reply-swiping');
      touchStart.row.querySelector('.messaging-message-content').style.transform =
        `translateX(${move}px)`;
      touchStart.armed = move >= 50;
    }
  });
  ['pointerup', 'pointercancel'].forEach((type) =>
    thread.addEventListener(type, () => {
      if (touchStart) {
        const state = touchStart;
        state.row.classList.remove('is-held', 'is-reply-swiping');
        state.row.querySelector('.messaging-message-content').style.transform = '';
        if (state.swiping && state.armed) selectReply(state.row);
      }
      clearTimeout(longPressTimer);
      longPressTimer = null;
      touchStart = null;
      if (suppressAttachmentClick) window.setTimeout(() => (suppressAttachmentClick = false), 400);
    }),
  );
  actionsDialog?.querySelector('[data-action-copy]')?.addEventListener('click', async () => {
    const text =
      thread.querySelector(`[data-message-id="${actionMessageId}"] .messaging-bubble > p`)
        ?.textContent || '';
    try {
      await navigator.clipboard.writeText(text);
    } catch (_) {
      const input = document.createElement('textarea');
      input.value = text;
      document.body.append(input);
      input.select();
      document.execCommand('copy');
      input.remove();
    }
    actionsDialog.close();
  });
  const cancelEditing = () => {
    stopTyping('cancel edit');
    editingMessageId = null;
    if (editState) editState.hidden = true;
    composeForm?.reset();
    clearAttachmentPreview();
    resizeMessageInput();
  };
  cancelEdit?.addEventListener('click', cancelEditing);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && editingMessageId) cancelEditing();
  });
  actionsDialog?.querySelector('[data-action-unsend]')?.addEventListener('click', () => {
    actionsDialog.close();
    pendingDeleteMessageId = actionMessageId;
    unsendDialog?.showModal();
    unsendCancel?.focus();
  });
  actionsDialog?.querySelector('[data-action-reply]')?.addEventListener('click', () => {
    selectReply(thread.querySelector(`[data-message-id="${actionMessageId}"]`));
    actionsDialog.close();
  });
  actionsDialog?.querySelector('[data-action-edit]')?.addEventListener('click', () => {
    const row = thread.querySelector(`[data-message-id="${actionMessageId}"]`);
    const text = row?.querySelector('.messaging-bubble > p')?.textContent?.trim();
    if (!text || !messageInput) return;
    stopTyping('edit message');
    actionsDialog.close();
    editingMessageId = actionMessageId;
    messageInput.value = text;
    editState.hidden = false;
    resizeMessageInput();
    messageInput.focus();
  });
  actionsDialog
    ?.querySelector('[data-action-cancel]')
    ?.addEventListener('click', () => actionsDialog.close());
  unsendDialog?.addEventListener('close', () => {
    pendingDeleteMessageId = null;
    if (deleteTrigger?.isConnected) deleteTrigger.focus({ preventScroll: true });
    deleteTrigger = null;
  });
  unsendConfirm?.addEventListener('click', async () => {
    if (!pendingDeleteMessageId || unsendConfirm.disabled) return;
    unsendConfirm.disabled = true;
    try {
      const csrfToken = composeForm?.querySelector('[name=csrfmiddlewaretoken]')?.value;
      const deleteUrl = thread.dataset.deleteUrlTemplate.replace(
        '/0/',
        `/${pendingDeleteMessageId}/`,
      );
      const response = await fetch(deleteUrl, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': csrfToken,
        },
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Message could not be unsent.');
      renderDeletedMessage(payload);
      refreshSharedLinks();
      unsendDialog?.close();
      pendingDeleteMessageId = null;
    } catch (error) {
      window.alert(error.message);
    } finally {
      unsendConfirm.disabled = false;
    }
  });

  thread.querySelectorAll('.messaging-message-row[data-message-id]').forEach((row) => {
    loadLinkPreview(row, row.querySelector('.messaging-bubble p')?.textContent || '');
  });

  if (composeForm && thread)
    composeForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (isSubmitting) return;
      const hasMessage = Boolean(messageInput?.value.trim());
      const hasAttachment = pendingAttachments.length > 0;
      if (!hasMessage && !hasAttachment) {
        messageInput?.focus();
        return;
      }
      isSubmitting = true;
      stopTyping('send');
      const sendButton = composeForm.querySelector('button[type="submit"]');
      sendButton.disabled = true;
      try {
        const messageData = new FormData(composeForm);
        // The pending array is the source of truth.  Building the
        // multipart field explicitly avoids assigning a synthetic
        // FileList to an input, which is unreliable across browsers.
        messageData.delete('attachments');
        pendingAttachments.forEach((file) => messageData.append('attachments', file, file.name));
        const response = await fetch(
          editingMessageId
            ? thread.dataset.editUrlTemplate.replace('/0/', `/${editingMessageId}/`)
            : composeForm.action || window.location.href,
          {
            method: 'POST',
            body: editingMessageId
              ? new URLSearchParams({ body: messageInput.value })
              : messageData,
            headers: editingMessageId
              ? {
                  'X-Requested-With': 'XMLHttpRequest',
                  'X-CSRFToken': composeForm.querySelector('[name=csrfmiddlewaretoken]').value,
                }
              : { 'X-Requested-With': 'XMLHttpRequest' },
          },
        );
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || 'Message could not be sent.');
        if (editingMessageId) {
          editingMessageId = null;
          editState.hidden = true;
          patchUpdatedMessage(payload);
          if (
            Number.isInteger(payload.revision_cursor) &&
            payload.revision_cursor > messageRevisionCursor
          ) {
            messageRevisionCursor = payload.revision_cursor;
          }
          refreshSharedLinks();
        } else {
          appendMessage(payload, true);
          refreshSharedLinks();
          clearReply();
        }
        composeForm.reset();
        clearAttachmentPreview();
        clearAttachmentWarning();
        resizeMessageInput();
        messageInput?.focus();
        scrollToLatest();
      } catch (error) {
        showAttachmentWarning([error.message || 'Message could not be sent.']);
      } finally {
        isSubmitting = false;
        sendButton.disabled = false;
      }
    });

  const ACTIVE_CHAT_POLL_INTERVAL_MS = 1000;
  let pollTimer = null;
  let pollInFlight = false;
  const schedulePoll = (delay = ACTIVE_CHAT_POLL_INTERVAL_MS) => {
    window.clearTimeout(pollTimer);
    pollTimer = window.setTimeout(pollForMessages, delay);
  };
  const pollForMessages = async () => {
    if (pollInFlight || document.hidden) {
      schedulePoll(document.hidden ? 5000 : ACTIVE_CHAT_POLL_INTERVAL_MS);
      return;
    }
    pollInFlight = true;
    try {
      const response = await fetch(
        `${thread.dataset.pollUrl}?after=${encodeURIComponent(lastMessageId)}&revision_after=${encodeURIComponent(messageRevisionCursor)}`,
        {
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
        },
      );
      if (!response.ok) {
        typingLog('[TYPE-RECEIVER-POLL]', 'FAILED', {
          status: response.status,
          statusText: response.statusText,
        });
        return;
      }
      const payload = await response.json();
      typingLog('[TYPE-RECEIVER-POLL]', 'RESPONSE', {
        status: response.status,
        typing: Boolean(payload.other_user_typing),
        messageCount: payload.messages?.length || 0,
      });
      setOtherTyping(Boolean(payload.other_user_typing));
      payload.messages.forEach((message) => appendMessage(message));
      payload.deleted_messages?.forEach((message) => renderDeletedMessage(message));
      const updatedMessages = payload.updated_messages || [];
      updatedMessages.forEach((message) => patchUpdatedMessage(message));
      if (
        Number.isInteger(payload.revision_cursor) &&
        payload.revision_cursor >= messageRevisionCursor
      ) {
        messageRevisionCursor = payload.revision_cursor;
      }
      if (payload.messages.length || payload.deleted_messages?.length || updatedMessages.length)
        refreshSharedLinks();
      if (payload.other_read_message_id) updateSeenMarker(payload.other_read_message_id);
      if (payload.messages.length) markVisibleRead();
      if (payload.messages.some((message) => message.sender_id !== currentUserId)) {
        document.dispatchEvent(new CustomEvent('messages:unread-changed'));
      }
    } catch (error) {
      typingLog('[TYPE-RECEIVER-POLL]', 'FAILED', { error: String(error) });
      // Keep the existing conversation intact and retry on the next interval.
    } finally {
      pollInFlight = false;
      schedulePoll();
    }
  };
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stopTyping('hidden');
    if (!document.hidden) {
      window.clearTimeout(pollTimer);
      pollForMessages();
      markVisibleRead();
    }
  });
  window.addEventListener(
    'pagehide',
    () => {
      if (otherTypingExpiryTimer) typingLog('[TYPE-EXPIRY]', 'CLEAR', { reason: 'pagehide' });
      window.clearTimeout(pollTimer);
      window.clearTimeout(otherTypingExpiryTimer);
      stopTyping('pagehide');
    },
    { once: true },
  );
  schedulePoll();
});