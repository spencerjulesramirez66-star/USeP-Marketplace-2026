from django.conf import settings
from django.db import models

import os
import uuid

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

    class Kind(models.TextChoices):
        TEXT = 'text', 'Text'
        PURCHASE_REQUEST = 'purchase_request', 'Purchase request'


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

    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.TEXT,
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


def purchase_proof_upload_to(instance, filename):
    """Random file names so payment screenshots can't be guessed from a URL."""
    extension = os.path.splitext(filename)[1].lower()[:10]
    return f'purchase_proofs/{uuid.uuid4().hex}{extension}'


class PurchaseRequest(models.Model):
    """The data behind a 'Confirm purchase' chat message.

    Lifecycle:  REQUESTED (seller sent the card)
             -> SUBMITTED (buyer filled in the verification page)
             -> CONFIRMED / DECLINED (seller reviewed it)
    CANCELLED is the seller withdrawing the request at any point before that.

    Deliberately NOT connected to Listing.stock_quantity yet. See the TODO in
    services.respond_purchase().
    """

    class Status(models.TextChoices):
        REQUESTED = 'requested', 'Waiting for buyer'
        SUBMITTED = 'submitted', 'Waiting for seller'
        CONFIRMED = 'confirmed', 'Confirmed'
        DECLINED = 'declined', 'Declined'
        CANCELLED = 'cancelled', 'Cancelled'
        PROPOSED = 'proposed', 'New time proposed'
        COMPLETED = 'completed', 'Delivered'

    class PaymentMethod(models.TextChoices):
        GCASH = 'gcash', 'GCash'
        CASH = 'cash', 'Cash on hand'

    message = models.OneToOneField('Message', on_delete=models.CASCADE, related_name='purchase_request')
    conversation = models.ForeignKey('Conversation', on_delete=models.CASCADE, related_name='purchase_requests')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.REQUESTED)

    # Snapshot taken when the seller sends the card, so later price edits
    # on the listing don't change what the buyer agreed to.
    is_service = models.BooleanField(default=False)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Filled in by the buyer
    quantity = models.PositiveIntegerField(default=1)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, blank=True)
    payment_reference = models.CharField(max_length=30, blank=True)
    payment_proof = models.ImageField(upload_to=purchase_proof_upload_to, blank=True, null=True)
    scheduled_start = models.DateTimeField(blank=True, null=True)
    scheduled_end = models.DateTimeField(blank=True, null=True)
    buyer_note = models.CharField(max_length=500, blank=True)

    proposed_start = models.DateTimeField(blank=True, null=True)
    proposed_end = models.DateTimeField(blank=True, null=True)
    proposed_by = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True,
                                    on_delete=models.SET_NULL, related_name='+')
    proposal_note = models.CharField(max_length=500, blank=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    responded_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_start']),
            models.Index(fields=['conversation', 'status']),
        ]

    def __str__(self):
        return f'PurchaseRequest #{self.pk} ({self.status})'
