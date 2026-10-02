from django.conf import settings
from django.db import models


class Conversation(models.Model):
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='buyer_conversations',
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='seller_conversations',
    )
    listing = models.ForeignKey(
        'dashboard.Listing',
        on_delete=models.CASCADE,
        related_name='conversations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['buyer', 'seller', 'listing'],
                name='unique_conversation_per_listing',
            )
        ]

    def __str__(self):
        return f'Conversation #{self.pk} ({self.buyer_id} <-> {self.seller_id})'

    def other_participant(self, user):
        return self.seller if self.buyer_id == user.id else self.buyer


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_marketplace_messages',
    )
    body = models.TextField(max_length=2000, blank=True)
    attachment = models.FileField(upload_to='messages/', blank=True, null=True)
    replied_to = models.ForeignKey(
        'self', blank=True, null=True, on_delete=models.SET_NULL, related_name='replies',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(blank=True, null=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['conversation', 'sender', 'is_read']),
        ]

    def __str__(self):
        return f'Message #{self.pk} in conversation #{self.conversation_id}'

    @property
    def attachment_is_image(self):
        return bool(self.attachment and self.attachment.name.lower().endswith(
            ('.gif', '.jpeg', '.jpg', '.png', '.webp'),
        ))


class MessageAttachment(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='messages/')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_image(self):
        return self.file.name.lower().endswith(('.gif', '.jpeg', '.jpg', '.png', '.webp'))

    @property
    def is_video(self):
        return self.file.name.lower().endswith(('.mp4', '.webm', '.mov'))


class MessageRevision(models.Model):
    """The body a message had before an edit."""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='revisions')
    body = models.TextField(max_length=2000)
    edited_at = models.DateTimeField(auto_now_add=True)
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='message_revisions')

    class Meta:
        ordering = ['edited_at', 'pk']


class ConversationUserState(models.Model):
    """A participant's local 'delete conversation' boundary."""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='user_states')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversation_states')
    cleared_through_message = models.ForeignKey(
        Message, blank=True, null=True, on_delete=models.SET_NULL, related_name='+',
    )
    cleared_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['conversation', 'user'], name='unique_conversation_user_state'),
        ]


class ConversationReadState(models.Model):
    """The furthest message a participant has actually read."""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='read_states')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversation_read_states')
    last_read_message = models.ForeignKey(Message, blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
    last_read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['conversation', 'user'], name='unique_conversation_read_state'),
        ]


class ConversationTypingState(models.Model):
    """Ephemeral per-participant typing activity.

    The timestamp, not a boolean, is authoritative: a stale timestamp simply
    stops counting as "typing" once TYPING_TTL_SECONDS (see selectors.py) has
    passed, with nothing to clean up on a timer.
    """
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='typing_states')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversation_typing_states')
    last_activity_at = models.DateTimeField(blank=True, null=True)
    # Scopes last_sequence to one browser tab/page-load, so a freshly loaded
    # page doesn't inherit (and get blocked by) an older tab's sequence.
    client_session_id = models.CharField(max_length=36, blank=True, null=True)
    last_sequence = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['conversation', 'user'], name='unique_conversation_typing_state'),
        ]
