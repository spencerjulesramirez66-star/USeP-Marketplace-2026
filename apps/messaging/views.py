
import logging, json

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
from .forms import MessageForm, PurchaseVerificationForm, schedule_hours,MAX_ATTACHMENT_SIZE_BYTES
from .models import PurchaseRequest

logger = logging.getLogger(__name__)

MESSAGE_PARTIAL = 'messaging/components/message.html'
MIN_SEARCH_LENGTH = 2
MAX_PREVIEW_URL_LENGTH = 2048

PURCHASE_TEMPLATE = 'messaging/components/purchase_verification.html'


# ------------------------------------------------------------------- helpers

def _hour_label(hour):
    return f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'}"


def _price_label(amount):
    text = f'\u20b1{amount:,.2f}'
    return text[:-3] if text.endswith('.00') else text



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
def conversation_shared(request, conversation_id):
    conversation = selectors.get_conversation_or_404(request.user, conversation_id)
    media, files = selectors.shared_attachments(conversation, request.user)
    links = selectors.shared_links(conversation, request.user)
    return JsonResponse({'media': media, 'files': files, 'links': links})

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
        'is_listing_seller': conversation.listing.seller_id == request.user.id,
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



# ---------------------------------------------------- seller: send the card
 
@login_required
@require_POST
def send_purchase_request(request, conversation_id):
    conversation = selectors.get_conversation_or_404(request.user, conversation_id)
    participant = selectors.other_participant(conversation, request.user)
    try:
        message = services.request_purchase(conversation, request.user)
    except PermissionDenied as error:
        return _json_error(str(error), 403)
    except ValidationError as error:
        return _json_error(' '.join(error.messages))
    return JsonResponse({'ok': True, 'id': message.id, 'html': _render_message(request, message, participant)})
 
 
# ----------------------------------------------- buyer: verification page
 
def _render_purchase_page(request, purchase, error='', status=200):
    conversation = purchase.conversation
    listing = conversation.listing
    open_hour, close_hour = schedule_hours()
    return render(request, PURCHASE_TEMPLATE, {
        'purchase': purchase,
        'listing': listing,
        'seller_name': _display_name(listing.seller),
        'listing_image_url': listing.conversation_image_url,
        'is_service': purchase.is_service,
        'unit_price_label': _price_label(purchase.unit_price),
        'max_quantity': None,  # TODO(stock): pass listing.stock_quantity once stock rules are settled
        'open_hour': open_hour,
        'close_hour': close_hour,
        'open_label': _hour_label(open_hour),
        'close_label': _hour_label(close_hour),
        'busy_slots_json': json.dumps(services.busy_slots(listing.seller_id, exclude_pk=purchase.pk)),
        'max_proof_bytes': MAX_ATTACHMENT_SIZE_BYTES,
        'max_proof_mb': MAX_ATTACHMENT_SIZE_BYTES // (1024 * 1024),
        'back_url': reverse('messaging:conversation', args=[conversation.id]),
        'error': error,
    }, status=status)
 
 
@login_required
@require_http_methods(['GET', 'POST'])
def purchase_verification(request, purchase_id):
    # 404 (not 403) for anyone who isn't the buyer, so ids can't be probed.
    purchase = get_object_or_404(
        PurchaseRequest.objects.select_related('conversation__listing__seller', 'message'),
        pk=purchase_id,
        conversation__buyer=request.user,
    )
    back_url = reverse('messaging:conversation', args=[purchase.conversation_id])
 
    if request.method == 'GET':
        if purchase.status != PurchaseRequest.Status.REQUESTED:
            return redirect(back_url)  # already answered; nothing left to fill in
        return _render_purchase_page(request, purchase)
 
    wants_json = _wants_json(request)
    form = PurchaseVerificationForm(request.POST, request.FILES, purchase=purchase)
    if not form.is_valid():
        message = _form_errors(form)
        return _json_error(message) if wants_json else _render_purchase_page(request, purchase, message, 400)
 
    try:
        services.submit_purchase_details(purchase.pk, request.user, form.cleaned_data)
    except PermissionDenied as error:
        return _json_error(str(error), 403)
    except ValidationError as error:
        message = ' '.join(error.messages)
        return _json_error(message) if wants_json else _render_purchase_page(request, purchase, message, 400)
 
    if wants_json:
        return JsonResponse({'ok': True, 'redirect': back_url})
    return redirect(back_url)
 
 
# ------------------------------------------- seller: confirm/decline/cancel
 
@login_required
@require_POST
def respond_purchase_request(request, purchase_id):
    purchase = get_object_or_404(PurchaseRequest.objects.select_related('conversation'), pk=purchase_id)
    # Participation check (404s for outsiders) before anything else.
    conversation = selectors.get_conversation_or_404(request.user, purchase.conversation_id)
    participant = selectors.other_participant(conversation, request.user)
    try:
        purchase = services.respond_purchase(purchase.pk, request.user, request.POST.get('action', ''))
    except PermissionDenied as error:
        return _json_error(str(error), 403)
    except ValidationError as error:
        return _json_error(' '.join(error.messages))
    message = purchase.message
    return JsonResponse({'ok': True, 'id': message.id, 'html': _render_message(request, message, participant)})
