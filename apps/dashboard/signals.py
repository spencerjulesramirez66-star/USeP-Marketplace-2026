from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from .models import Message
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Message)
def notify_recipient_of_new_message(sender, instance, created, **kwargs):
    if not created:
        return
    def broadcast():
        conversation = instance.conversation
        recipient = conversation.seller if instance.sender_id == conversation.buyer_id else conversation.buyer
        logger.info('Realtime message notification: message=%s recipient=%s', instance.pk, recipient.pk)
        # Import lazily to avoid loading views while Django registers signals.
        from .views import _unread_message_count
        unread_count = _unread_message_count(recipient)
        sender_name = f'{instance.sender.first_name} {instance.sender.last_name}'.strip() or instance.sender.email
        preview = instance.body.strip()[:100] or 'Sent an attachment'
        async_to_sync(get_channel_layer().group_send)(
            f'marketplace_user_{recipient.pk}',
            {
                'type': 'message.notification',
                'payload': {
                    'type': 'message_notification',
                    'message_id': instance.pk,
                    'conversation_id': conversation.pk,
                    'conversation_url': reverse('dashboard:conversation', args=[conversation.pk]),
                    'sender': {
                        'id': instance.sender_id,
                        'name': sender_name,
                        'avatar_url': instance.sender.avatar_url,
                    },
                    'preview': preview,
                    'listing_title': conversation.listing.title,
                    'unread_count': unread_count,
                },
            },
        )
    transaction.on_commit(broadcast)
