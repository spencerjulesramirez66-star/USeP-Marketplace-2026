"""HTTP layer for messaging.

Views authenticate, parse the request, call a selector or service, and
return a response. Business rules live in services.py, queries in
selectors.py. Views stay short on purpose.
"""
import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.text import Truncator
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.dashboard.models import Listing

from . import link_previews, selectors, services
from .forms import MessageForm

logger = logging.getLogger(__name__)

MESSAGE_PARTIAL = 'messaging/components/message.html'
MIN_SEARCH_LENGTH = 2
MAX_PREVIEW_URL_LENGTH = 2048


# ------------------------------------------------------------------- helpers

def _display_name(user):
    return f'{user.first_name} {user.last_name}'.strip() or user.email


def _json_error(message, status=400):
    return JsonResponse({'ok': False, 'error': message}, status=status)


def _wants_json(request):
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('accept', '')
    )


def _int_param(request, name, default=0):
    try:
        return max(int(request.GET.get(name, default)), 0)
    except (TypeError, ValueError):
        return default


def _form_errors(form):
    return ' '.join(error for errors in form.errors.values() for error in errors)


def _render_message(request, message, participant, seen_message_id=None):
    """The one message partial, shared by the full page and every AJAX response."""
    return render_to_string(
        MESSAGE_PARTIAL,
        {'message': message, 'chat_participant': participant, 'seen_message_id': seen_message_id},
        request=request,
    )


def _conversation_json(conversation, user):
    participant = selectors.other_participant(conversation, user)
    return {
        'id': conversation.id,
        'url': reverse('messaging:conversation', args=[conversation.id]),
        'listing_title': conversation.listing.title,
        'image_url': conversation.listing.conversation_image_url,
        'updated_at': conversation.updated_at.isoformat(),
        'unread_count': getattr(conversation, 'unread_count', 0),
        'participant': {
            'id': participant.id,
            'name': _display_name(participant),
            'avatar_url': participant.avatar_url,
        },
    }


# --------------------------------------------------------------------- pages

@login_required
@require_GET
def conversation_list(request):
    return render(request, 'messaging/messaging.html', {
        'conversation_groups': selectors.sidebar_groups(request.user),
        'conversation': None,
        'selected_conversation': None,
        'message_form': MessageForm(),
    })


@login_required
@require_http_methods(['GET', 'POST'])
def conversation_detail(request, conversation_id):
    conversation = selectors.get_conversation_or_404(request.user, conversation_id)
    participant = selectors.other_participant(conversation, request.user)

    if request.method == 'POST':
        return _handle_send(request, conversation, participant)

    chat_media, chat_files = selectors.shared_attachments(conversation, request.user)
    return render(request, 'messaging/messaging.html', {
        'conversation_groups': selectors.sidebar_groups(request.user),
        'conversation': conversation,
        'selected_conversation': conversation,
        'chat_participant': participant,
        'conversation_messages': list(selectors.thread_messages(conversation, request.user)),
        'seen_message_id': selectors.seen_message_id(conversation, request.user, participant),
        'chat_media': chat_media,
        'chat_files': chat_files,
        'chat_links': selectors.shared_links(conversation, request.user),
        'message_form': MessageForm(),
        'last_message_id': selectors.last_message_id(conversation, request.user),
        'server_time': timezone.now().isoformat(),
    })


def _handle_send(request, conversation, participant):
    wants_json = _wants_json(request)
    detail_url = reverse('messaging:conversation', args=[conversation.id])

    form = MessageForm(request.POST, request.FILES)
    if not form.is_valid():
        return _json_error(_form_errors(form)) if wants_json else redirect(detail_url)

    files = request.FILES.getlist('attachments')
    if form.cleaned_data.get('attachment'):
        files.insert(0, form.cleaned_data['attachment'])

    try:
        message = services.send_message(
            conversation,
            request.user,
            body=form.cleaned_data.get('body', ''),
            files=files,
            reply_to_id=request.POST.get('reply_to_message_id') or None,
        )
    except (ValidationError, ValueError) as error:
        text = ' '.join(getattr(error, 'messages', [str(error)]))
        return _json_error(text) if wants_json else redirect(detail_url)

    if not wants_json:
        return redirect(detail_url)
    return JsonResponse({'ok': True, 'id': message.id, 'html': _render_message(request, message, participant)})


@login_required
@require_POST
def start_conversation(request, item_slug):
    """The 'Message seller' button on a listing page."""
    listing = get_object_or_404(Listing.objects.select_related('seller'), slug=item_slug)
    try:
        conversation = services.start_conversation(request.user, listing)
    except PermissionDenied as error:
        return _json_error(str(error), 403) if _wants_json(request) else redirect(listing.get_absolute_url())
    return redirect('messaging:conversation', conversation_id=conversation.id)


# ------------------------------------------------------------ sidebar / search

@login_required
@require_GET
@never_cache
def sidebar_state(request):
    groups = selectors.sidebar_groups(request.user)
    return JsonResponse({
        'unread_total': sum(group['unread_count'] for group in groups),
        'groups': [
            {
                'participant_id': group['participant'].id,
                'unread_count': group['unread_count'],
                'conversations': [_conversation_json(c, request.user) for c in group['conversations']],
            }
            for group in groups
        ],
    })


@login_required
@require_GET
@never_cache
def unread_message_count(request):
    """A lean endpoint for the navbar badge (context_processors.py supplies
    the number used on first paint; this is for refreshing it without a
    reload, e.g. after a realtime notification arrives)."""
    return JsonResponse({'count': selectors.unread_total(request.user)})


@login_required
@require_GET
def conversation_search(request):
    query = request.GET.get('q', '').strip()
    if len(query) < MIN_SEARCH_LENGTH:
        return JsonResponse({'results': []})
    results = selectors.search_conversations(request.user, query)
    return JsonResponse({'results': [_conversation_json(c, request.user) for c in results]})


@login_required
@require_POST
def clear_conversation(request, conversation_id):
    conversation = selectors.get_conversation_or_404(request.user, conversation_id)
    services.clear_conversation(conversation, request.user)
    return JsonResponse({'ok': True, 'redirect': reverse('messaging:conversation_list')})


# ----------------------------------------------------------- thread endpoints

@login_required
@require_GET
def message_search(request, conversation_id):
    conversation = selectors.get_conversation_or_404(request.user, conversation_id)
    query = request.GET.get('q', '').strip()
    if len(query) < MIN_SEARCH_LENGTH:
        return JsonResponse({'results': []})
    return JsonResponse({'results': [
        {
            'id': message.id,
            'snippet': Truncator(message.body).chars(160),
            'sender': _display_name(message.sender),
            'is_own': message.sender_id == request.user.id,
            'created_at': message.created_at.isoformat(),
        }
        for message in selectors.search_messages(conversation, request.user, query)
    ]})


@login_required
@require_GET
@never_cache
def new_messages(request, conversation_id):
    """Poll endpoint. Query: ?after=<last message id the client has>
    &since=<server_time from the previous poll response, ISO 8601>.
    Returns everything that changed in one response."""
    conversation = selectors.get_conversation_or_404(request.user, conversation_id)
    participant = selectors.other_participant(conversation, request.user)

    since = parse_datetime(request.GET.get('since', '') or '')
    if since is not None and timezone.is_naive(since):
        since = timezone.make_aware(since)
    server_time = timezone.now()

    new, changed = selectors.messages_since(
        conversation, request.user, _int_param(request, 'after'), since,
    )
    return JsonResponse({
        'server_time': server_time.isoformat(),
        'new': [{'id': m.id, 'html': _render_message(request, m, participant)} for m in new],
        'changed': [{'id': m.id, 'html': _render_message(request, m, participant)} for m in changed],
        'seen_message_id': selectors.seen_message_id(conversation, request.user, participant),
        'other_is_typing': selectors.is_typing(conversation, participant),
    })


@login_required
@require_POST
def mark_read(request, conversation_id):
    conversation = selectors.get_conversation_or_404(request.user, conversation_id)
    services.mark_read(conversation, request.user)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def typing(request, conversation_id):
    conversation = selectors.get_conversation_or_404(request.user, conversation_id)
    try:
        sequence = max(int(request.POST.get('sequence', 0)), 0)
    except ValueError:
        return _json_error('Invalid sequence.')
    services.set_typing(
        conversation, request.user,
        is_typing=request.POST.get('is_typing') == 'true',
        session_id=request.POST.get('session_id', '')[:36],
        sequence=sequence,
    )
    return JsonResponse({'ok': True})


@login_required
@require_GET
def conversation_links(request, conversation_id):
    """Refreshes the details panel's shared media/files/links."""
    conversation = selectors.get_conversation_or_404(request.user, conversation_id)
    media, files = selectors.shared_attachments(conversation, request.user)
    return JsonResponse({
        'media': media,
        'files': files,
        'links': selectors.shared_links(conversation, request.user),
    })


# ------------------------------------------------------------ single message

def _get_message(request, conversation_id, message_id):
    conversation = selectors.get_conversation_or_404(request.user, conversation_id)
    message = selectors.get_message_or_404(conversation, message_id)
    participant = selectors.other_participant(conversation, request.user)
    return message, participant


@login_required
@require_POST
def edit_message(request, conversation_id, message_id):
    message, participant = _get_message(request, conversation_id, message_id)
    try:
        services.edit_message(message, request.user, request.POST.get('body', ''))
    except PermissionDenied as error:
        return _json_error(str(error), 403)
    except ValidationError as error:
        return _json_error(' '.join(error.messages))
    return JsonResponse({'ok': True, 'id': message.id, 'html': _render_message(request, message, participant)})


@login_required
@require_POST
def delete_message(request, conversation_id, message_id):
    message, participant = _get_message(request, conversation_id, message_id)
    try:
        services.delete_message(message, request.user)
    except PermissionDenied as error:
        return _json_error(str(error), 403)
    return JsonResponse({'ok': True, 'id': message.id, 'html': _render_message(request, message, participant)})


@login_required
@require_GET
def message_history(request, conversation_id, message_id):
    message, _ = _get_message(request, conversation_id, message_id)
    if message.is_deleted:
        return _json_error('Message unavailable.', 404)
    return JsonResponse({
        'revisions': [{'body': r.body, 'edited_at': r.edited_at.isoformat()} for r in message.revisions.all()],
        'current': {
            'body': message.body,
            'edited_at': message.edited_at.isoformat() if message.edited_at else None,
        },
    })


# ------------------------------------------------------------- link preview

@login_required
@require_GET
def link_preview(request):
    url = request.GET.get('url', '').strip()
    if not url.lower().startswith(('http://', 'https://')) or len(url) > MAX_PREVIEW_URL_LENGTH:
        return _json_error('Invalid URL.')
    try:
        preview = link_previews.get_link_preview(url)
    except Exception:
        logger.exception('Link preview failed for %s', url)
        preview = None
    return JsonResponse({'preview': preview})
