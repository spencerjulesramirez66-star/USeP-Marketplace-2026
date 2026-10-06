"""Actions that change messaging data. Views call these; the rules live here,
not in the view or in JavaScript."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from decimal import Decimal

from .models import (
    Conversation,
    ConversationReadState,
    ConversationTypingState,
    ConversationUserState,
    Message,
    MessageAttachment,
    MessageRevision,
    PurchaseRequest
)

MAX_BODY_LENGTH = 2000


PR = PurchaseRequest.Status

# action -> (statuses it may start from, status it moves to)
SELLER_TRANSITIONS = {
    'confirm': ({PR.SUBMITTED}, PR.CONFIRMED),
    'decline': ({PR.SUBMITTED}, PR.DECLINED),
    'cancel': ({PR.REQUESTED, PR.SUBMITTED}, PR.CANCELLED),
}


def start_conversation(buyer, listing):
    """Get or create the buyer<->seller conversation for a listing."""
    if listing.seller_id == buyer.id:
        raise PermissionDenied('You cannot message yourself about your own listing.')

    conversation = Conversation.objects.filter(
        buyer=buyer, seller=listing.seller, listing=listing,
    ).first()
    if conversation:
        return conversation

    if listing.status in (listing.Status.DRAFT, listing.Status.ARCHIVED):
        raise PermissionDenied('This listing is not available.')
    return Conversation.objects.create(buyer=buyer, seller=listing.seller, listing=listing)


@transaction.atomic
def send_message(conversation, sender, body='', files=(), reply_to_id=None):
    reply_to = None
    if reply_to_id:
        reply_to = conversation.messages.filter(pk=reply_to_id, is_deleted=False).first()
        if reply_to is None:
            raise ValidationError('The message you are replying to is no longer available.')

    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        body=(body or '').strip(),
        replied_to=reply_to,
    )
    for uploaded in files:
        MessageAttachment.objects.create(message=message, file=uploaded)

    # Bumps the conversation to the top of everyone's sidebar.
    Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())
    # Sending implicitly ends "typing".
    ConversationTypingState.objects.filter(conversation=conversation, user=sender).update(last_activity_at=None)
    return message


def edit_message(message, editor, body):
    """Edit a message's text. Only the sender can edit, only while it has a
    body (an attachment-only or already-unsent message can't be)."""
    if message.sender_id != editor.id:
        raise PermissionDenied('You cannot edit this message.')
    if message.is_deleted or not message.body:
        raise PermissionDenied('This message cannot be edited.')

    body = (body or '').strip()
    if not body:
        raise ValidationError('A message cannot be empty.')
    if len(body) > MAX_BODY_LENGTH:
        raise ValidationError(f'Messages are limited to {MAX_BODY_LENGTH} characters.')
    if body == message.body:
        return message

    with transaction.atomic():
        MessageRevision.objects.create(message=message, body=message.body, editor=editor)
        message.body = body
        message.is_edited = True
        message.edited_at = timezone.now()
        message.save(update_fields=['body', 'is_edited', 'edited_at', 'updated_at'])
    return message


def delete_message(message, user):
    """'Unsend': remove content for everyone but keep the row, so replies to
    it can still show 'Message unavailable'."""
    if message.sender_id != user.id:
        raise PermissionDenied('You cannot delete this message.')
    if message.is_deleted:
        return message

    with transaction.atomic():
        for attachment in message.attachments.all():
            attachment.file.delete(save=False)
            attachment.delete()
        if message.attachment:
            message.attachment.delete(save=False)
            message.attachment = None
        message.body = ''
        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.save(update_fields=['body', 'attachment', 'is_deleted', 'deleted_at', 'updated_at'])
    return message


def mark_read(conversation, user):
    """Mark the other person's messages read, and remember how far `user` has read."""
    incoming = conversation.messages.exclude(sender=user)
    last_id = incoming.order_by('-id').values_list('id', flat=True).first()
    incoming.filter(is_read=False).update(is_read=True)  # .update(): does not touch updated_at

    if last_id:
        state, _ = ConversationReadState.objects.get_or_create(conversation=conversation, user=user)
        if state.last_read_message_id is None or last_id > state.last_read_message_id:
            state.last_read_message_id = last_id
            state.last_read_at = timezone.now()
            state.save(update_fields=['last_read_message', 'last_read_at'])


def set_typing(conversation, user, is_typing, session_id, sequence):
    """Record typing state. A stale sequence number from the same browser
    tab is ignored, so out-of-order requests can't resurrect an old state."""
    state, _ = ConversationTypingState.objects.get_or_create(conversation=conversation, user=user)
    if state.client_session_id == session_id and sequence <= state.last_sequence:
        return
    state.client_session_id = session_id
    state.last_sequence = sequence
    state.last_activity_at = timezone.now() if is_typing else None
    state.save(update_fields=['client_session_id', 'last_sequence', 'last_activity_at'])


def clear_conversation(conversation, user):
    """'Delete conversation' for this user only; the other participant is unaffected."""
    last_id = conversation.messages.order_by('-id').values_list('id', flat=True).first()
    ConversationUserState.objects.update_or_create(
        conversation=conversation,
        user=user,
        defaults={'cleared_at': timezone.now(), 'cleared_through_message_id': last_id},
    )



def _touch_message(message):
    """Bump Message.updated_at so the poll endpoint's 'changed' list re-sends the card."""
    message.save(update_fields=['updated_at'])


def _has_conflict(seller_id, start, end, exclude_pk=None):
    """True if the seller already has a pending or confirmed slot overlapping start..end."""
    qs = PurchaseRequest.objects.filter(
        conversation__listing__seller_id=seller_id,
        status__in=[PR.SUBMITTED, PR.CONFIRMED, PR.PROPOSED], 
        scheduled_start__lt=end,
        scheduled_end__gt=start,
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


def busy_slots(seller_id, exclude_pk=None):
    """Upcoming taken slots for the calendar's hatched blocks. Times only, no buyer details."""
    qs = PurchaseRequest.objects.filter(
        conversation__listing__seller_id=seller_id,
        status__in=[PR.SUBMITTED, PR.CONFIRMED, PR.PROPOSED], 
        scheduled_end__gte=timezone.now(),
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return [
        {
            'start': timezone.localtime(p.scheduled_start).isoformat(),
            'end': timezone.localtime(p.scheduled_end).isoformat(),
        }
        for p in qs
    ]


@transaction.atomic
def request_purchase(conversation, seller):
    """Seller drops a 'Confirm purchase' card into the chat."""
    listing = conversation.listing
    if listing.seller_id != seller.id:
        raise PermissionDenied('Only the owner of this listing can request a purchase confirmation.')
    if conversation.purchase_requests.filter(status=PR.REQUESTED).exists():
        raise ValidationError('There is already an open purchase request in this chat.')

    message = send_message(conversation, seller, body='Purchase confirmation request', files=[])
    message.kind = Message.Kind.PURCHASE_REQUEST
    message.save(update_fields=['kind', 'updated_at'])

    PurchaseRequest.objects.create(
        message=message,
        conversation=conversation,
        is_service=bool(listing.is_service_listing),
        unit_price=listing.price,  # read-only snapshot; no stock touched
    )
    return message


def submit_purchase_details(purchase_id, buyer, cleaned):
    """Buyer submits the verification form. `cleaned` is PurchaseVerificationForm.cleaned_data."""
    with transaction.atomic():
        purchase = PurchaseRequest.objects.select_for_update().get(pk=purchase_id)
        conversation = purchase.conversation

        if conversation.buyer_id != buyer.id:
            raise PermissionDenied('Only the buyer in this chat can fill this in.')
        if purchase.status != PR.REQUESTED:
            raise ValidationError('This request has already been answered.')

        start, end = cleaned['scheduled_start'], cleaned['scheduled_end']
        if _has_conflict(conversation.listing.seller_id, start, end, purchase.pk):
            raise ValidationError('That time was just taken. Pick another slot.')

        quantity = 1 if purchase.is_service else cleaned['quantity']
        purchase.quantity = quantity
        purchase.total_amount = purchase.unit_price * Decimal(quantity)
        purchase.payment_method = cleaned['payment_method']
        purchase.payment_reference = cleaned.get('payment_reference', '')
        purchase.payment_proof = cleaned.get('payment_proof')
        purchase.scheduled_start, purchase.scheduled_end = start, end
        purchase.buyer_note = cleaned.get('buyer_note', '')
        purchase.status = PR.SUBMITTED
        purchase.submitted_at = timezone.now()
        purchase.save()
        _touch_message(purchase.message)
    return purchase


@transaction.atomic
def respond_purchase(purchase_id, seller, action):
    """Seller confirms, declines or cancels."""
    if action not in SELLER_TRANSITIONS:
        raise ValidationError('Unknown action.')

    purchase = PurchaseRequest.objects.select_for_update().get(pk=purchase_id)
    if purchase.conversation.listing.seller_id != seller.id:
        raise PermissionDenied('Only the seller can do that.')

    allowed_from, new_status = SELLER_TRANSITIONS[action]
    if purchase.status not in allowed_from:
        raise ValidationError('This request can no longer be changed.')

    purchase.status = new_status
    purchase.responded_at = timezone.now()
    purchase.save(update_fields=['status', 'responded_at'])

    # TODO(stock): when new_status == CONFIRMED, subtract purchase.quantity from
    # the listing's stock (and set RESERVED/SOLD) here, inside this transaction.
    # Left out on purpose until the stock rules are decided.

    _touch_message(purchase.message)
    return purchase
