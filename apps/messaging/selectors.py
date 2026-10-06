"""Read-only database queries for messaging.

Nothing here changes data. `get_conversation_or_404` is the single place that
checks a user belongs to a conversation — every view and service call routes
through it instead of re-checking membership in several places.
"""
import os
import re
from datetime import timedelta
from urllib.parse import urlparse

from django.db.models import Count, F, Max, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import (
    Conversation,
    ConversationReadState,
    ConversationTypingState,
    ConversationUserState,
    Message,
    MessageAttachment,
)

TYPING_TTL_SECONDS = 6
URL_PATTERN = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)


# ------------------------------------------------------------------ access

def get_conversation_or_404(user, conversation_id):
    """The conversation, only if `user` is its buyer or seller.

    A non-member gets a 404 rather than a 403, so conversation IDs cannot be
    probed for existence.
    """
    queryset = (
        Conversation.objects
        .select_related('buyer', 'seller', 'listing')
        .filter(Q(buyer=user) | Q(seller=user))
    )
    return get_object_or_404(queryset, pk=conversation_id)


def get_message_or_404(conversation, message_id):
    """A message, only if it belongs to an already-checked conversation."""
    return get_object_or_404(
        Message.objects.select_related('sender', 'conversation'),
        pk=message_id,
        conversation=conversation,
    )


def other_participant(conversation, user):
    return conversation.seller if conversation.buyer_id == user.id else conversation.buyer


# --------------------------------------------------------------- conversations

def _conversations_for(user):
    """Conversations of `user`, with everything the sidebar needs in one
    query (plus one prefetch for listing images) instead of one query per
    row."""
    cleared_at = ConversationUserState.objects.filter(
        conversation=OuterRef('pk'), user=user,
    ).values('cleared_at')[:1]

    unread_filter = (
        Q(messages__is_read=False, messages__is_deleted=False)
        & ~Q(messages__sender=user)
        & (Q(cleared_at__isnull=True) | Q(messages__created_at__gt=F('cleared_at')))
    )
    return (
        Conversation.objects
        .filter(Q(buyer=user) | Q(seller=user))
        .select_related('buyer', 'seller', 'listing')
        .prefetch_related('listing__listing_images')
        .annotate(cleared_at=Subquery(cleared_at))
        .annotate(
            last_message_at=Max('messages__created_at'),
            unread_count=Count('messages', filter=unread_filter),
        )
        .order_by('-updated_at')
    )


def _not_cleared(conversations):
    """Hide a conversation the user deleted, until a newer message arrives."""
    for conversation in conversations:
        if conversation.cleared_at is None:
            yield conversation
        elif conversation.last_message_at and conversation.last_message_at > conversation.cleared_at:
            yield conversation


def unread_total(user):
    """Just the badge count -- cheaper than sidebar_groups() for polling/context use."""
    cleared_at = ConversationUserState.objects.filter(
        conversation=OuterRef('pk'), user=user,
    ).values('cleared_at')[:1]
    unread_filter = (
        Q(messages__is_read=False, messages__is_deleted=False)
        & ~Q(messages__sender=user)
        & (Q(cleared_at__isnull=True) | Q(messages__created_at__gt=F('cleared_at')))
    )
    return (
        Conversation.objects
        .filter(Q(buyer=user) | Q(seller=user))
        .annotate(cleared_at=Subquery(cleared_at))
        .aggregate(total=Count('messages', filter=unread_filter))
    )['total'] or 0


def sidebar_groups(user):
    """Conversations grouped by the other participant, newest activity first
    within each group."""
    groups = {}
    order = []
    for conversation in _not_cleared(_conversations_for(user)):
        participant = other_participant(conversation, user)
        if participant.id not in groups:
            groups[participant.id] = {'participant': participant, 'conversations': [], 'unread_count': 0}
            order.append(participant.id)
        group = groups[participant.id]
        group['conversations'].append(conversation)
        group['unread_count'] += conversation.unread_count
    return [groups[pid] for pid in order]


def search_conversations(user, query, limit=20):
    """Search by listing title or the other participant's name/email."""
    matches = _conversations_for(user).filter(
        Q(listing__title__icontains=query)
        | Q(buyer__first_name__icontains=query) | Q(buyer__last_name__icontains=query)
        | Q(seller__first_name__icontains=query) | Q(seller__last_name__icontains=query)
        | Q(buyer__email__icontains=query) | Q(seller__email__icontains=query)
    )
    return list(_not_cleared(matches))[:limit]


# -------------------------------------------------------------------- messages

def _cleared_at(conversation, user):
    return (
        ConversationUserState.objects
        .filter(conversation=conversation, user=user)
        .values_list('cleared_at', flat=True)
        .first()
    )


def visible_messages(conversation, user):
    """Messages this user may see (respects their own 'delete conversation')."""
    messages = conversation.messages.all()
    cleared_at = _cleared_at(conversation, user)
    if cleared_at:
        messages = messages.filter(created_at__gt=cleared_at)
    return messages


def thread_messages(conversation, user):
    """Visible messages with related rows preloaded, for rendering without
    per-message queries."""
    return (
        visible_messages(conversation, user)
        .select_related('sender', 'replied_to', 'replied_to__sender')
        .prefetch_related('attachments', 'replied_to__attachments')
    )


def search_messages(conversation, user, query, limit=50):
    return list(
        visible_messages(conversation, user)
        .filter(is_deleted=False, body__icontains=query)
        .select_related('sender')
        .order_by('-created_at')[:limit]
    )


def messages_since(conversation, user, after_id, since):
    """(new_messages, changed_messages) for the poll endpoint.

    new     = messages with id greater than `after_id`
    changed = older messages edited or unsent since `since`
              (Message.updated_at moves on edit/delete but not on read state)
    """
    base = thread_messages(conversation, user)
    new = list(base.filter(id__gt=after_id))
    changed = list(base.filter(id__lte=after_id, updated_at__gte=since)) if since else []
    return new, changed


def last_message_id(conversation, user):
    return visible_messages(conversation, user).order_by('-id').values_list('id', flat=True).first() or 0


# ------------------------------------------------------------ read / typing

def seen_message_id(conversation, user, participant):
    """The newest message `user` sent that `participant` has read."""
    last_read_id = (
        ConversationReadState.objects
        .filter(conversation=conversation, user=participant)
        .values_list('last_read_message_id', flat=True)
        .first()
    )
    if not last_read_id:
        return None
    return (
        conversation.messages
        .filter(sender=user, id__lte=last_read_id, is_deleted=False)
        .order_by('-id')
        .values_list('id', flat=True)
        .first()
    )


def is_typing(conversation, participant):
    cutoff = timezone.now() - timedelta(seconds=TYPING_TTL_SECONDS)
    return ConversationTypingState.objects.filter(
        conversation=conversation, user=participant, last_activity_at__gte=cutoff,
    ).exists()


# ------------------------------------------------------------- shared content

def shared_attachments(conversation, user, limit=200):
    """(media, files) lists of {'url', 'name', 'is_video'} for the details panel."""
    messages = visible_messages(conversation, user).filter(is_deleted=False)
    media, files = [], []

    def add(url, name, is_image, is_video):
        item = {'url': url, 'name': os.path.basename(name), 'is_video': is_video}
        (media if is_image or is_video else files).append(item)

    for attachment in (
        MessageAttachment.objects.filter(message__in=messages).order_by('-created_at')[:limit]
    ):
        add(attachment.file.url, attachment.file.name, attachment.is_image, attachment.is_video)

    # Legacy single-file field, kept until fully migrated into MessageAttachment.
    for message in messages.exclude(attachment='').exclude(attachment__isnull=True).order_by('-created_at')[:limit]:
        add(message.attachment.url, message.attachment.name, message.attachment_is_image, False)

    return media, files


def shared_links(conversation, user, limit=30):
    """Unique URLs found in message text, newest first. Purely local text
    scanning: the browser fetches rich previews separately, per link."""
    bodies = (
        visible_messages(conversation, user)
        .filter(is_deleted=False)
        .exclude(body='')
        .order_by('-created_at')
        .values_list('body', flat=True)
    )
    seen, links = set(), []
    for body in bodies:
        for url in URL_PATTERN.findall(body):
            url = url.rstrip('.,);]')
            if url in seen:
                continue
            seen.add(url)
            domain = urlparse(url).netloc.lower().removeprefix('www.')
            links.append({
                'url': url,
                'domain': domain,
                'title': domain,
                'image': None,
                'is_drive': domain in ('drive.google.com', 'docs.google.com'),
            })
            if len(links) >= limit:
                return links
    return links
