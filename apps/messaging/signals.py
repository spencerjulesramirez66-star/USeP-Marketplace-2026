import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from . import selectors
from .models import Message

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Message)
def notify_recipient_of_new_message(sender, instance, created, **kwargs):
    if not created:
        return

    def broadcast():
        try:
            channel_layer = get_channel_layer()
            if channel_layer is None:
                logger.warning('No channel layer configured; skipping realtime notification.')
                return

            conversation = instance.conversation
            recipient = selectors.other_participant(conversation, instance.sender)
            sender_name = f'{instance.sender.first_name} {instance.sender.last_name}'.strip() or instance.sender.email
            preview = instance.body.strip()[:100] or 'Sent an attachment'
            async_to_sync(channel_layer.group_send)(
                f'marketplace_user_{recipient.pk}',
                {
                    'type': 'message.notification',
                    'payload': {
                        'type': 'message_notification',
                        'message_id': instance.pk,
                        'conversation_id': conversation.pk,
                        'conversation_url': reverse('messaging:conversation', args=[conversation.pk]),
                        'sender': {
                            'id': instance.sender_id,
                            'name': sender_name,
                            'avatar_url': getattr(instance.sender, 'avatar_url', None),
                        },
                        'preview': preview,
                        'listing_title': conversation.listing.title,
                        'unread_count': selectors.unread_total(recipient),
                    },
                },
            )
        except Exception:
            logger.exception('Realtime notification failed for message=%s', instance.pk)

    transaction.on_commit(broadcast)
