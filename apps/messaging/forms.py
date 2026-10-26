from django import forms

from .models import Message
from datetime import time

from django.utils import timezone

from .models import PurchaseRequest
from .schedule_config import SCHEDULE_CLOSE_HOUR, SCHEDULE_OPEN_HOUR, SCHEDULE_TIMEZONE


ALLOWED_ATTACHMENT_TYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain', 'application/zip',
    'image/gif', 'image/jpeg', 'image/png', 'image/webp',
    'video/mp4', 'video/webm', 'video/quicktime',
}
MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024
MAX_ATTACHMENTS_PER_MESSAGE = 10


PROOF_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MIN_SLOT_MINUTES = 15
MAX_SLOT_MINUTES = 240


def schedule_window_message():
    def label(hour):
        return f'{hour % 12 or 12}:00 {"AM" if hour < 12 else "PM"}'

    return (
        f'Schedules must be between {label(SCHEDULE_OPEN_HOUR)} '
        f'and {label(SCHEDULE_CLOSE_HOUR)}.'
    )


def validate_schedule_times(start, end):
    if timezone.is_naive(start):
        start = timezone.make_aware(start, SCHEDULE_TIMEZONE)
    if timezone.is_naive(end):
        end = timezone.make_aware(end, SCHEDULE_TIMEZONE)

    local_start = timezone.localtime(start, SCHEDULE_TIMEZONE)
    local_end = timezone.localtime(end, SCHEDULE_TIMEZONE)
    minutes = (end - start).total_seconds() / 60

    if local_start.date() != local_end.date():
        raise forms.ValidationError('A schedule must start and end on the same day.')
    if end <= start:
        raise forms.ValidationError('The schedule end must be after the start.')
    if minutes < MIN_SLOT_MINUTES:
        raise forms.ValidationError(f'Pick at least {MIN_SLOT_MINUTES} minutes.')
    if minutes > MAX_SLOT_MINUTES:
        raise forms.ValidationError(f'Pick at most {MAX_SLOT_MINUTES // 60} hours.')
    if local_start.time() < time(SCHEDULE_OPEN_HOUR) or local_end.time() > time(SCHEDULE_CLOSE_HOUR):
        raise forms.ValidationError(schedule_window_message())
    if start < timezone.now():
        raise forms.ValidationError('That time has already passed.')


class MessageForm(forms.ModelForm):
    """Validates the compose form. Multiple files ride under the
    'attachments' field name and are validated the same way as the single
    legacy 'attachment' field."""

    class Meta:
        model = Message
        fields = ['body', 'attachment']
        widgets = {
            'body': forms.Textarea(attrs={
                'rows': 1,
                'placeholder': 'Ask the seller about this listing...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['body'].required = False
        self.fields['attachment'].required = False
        # Exposed to the template so the client-side size hint always matches
        # what the server actually enforces.
        self.max_attachment_size_bytes = MAX_ATTACHMENT_SIZE_BYTES

    def clean(self):
        cleaned_data = super().clean()
        attachments = self.files.getlist('attachments')

        if len(attachments) > MAX_ATTACHMENTS_PER_MESSAGE:
            raise forms.ValidationError(f'Attach at most {MAX_ATTACHMENTS_PER_MESSAGE} files per message.')

        if not cleaned_data.get('body', '').strip() and not cleaned_data.get('attachment') and not attachments:
            raise forms.ValidationError('Write a message or attach a file.')

        for attachment in attachments:
            self._validate_attachment(attachment)
        return cleaned_data

    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if attachment:
            self._validate_attachment(attachment)
        return attachment

    @classmethod
    def _validate_attachment(cls, attachment):
        if attachment.size > MAX_ATTACHMENT_SIZE_BYTES:
            raise forms.ValidationError('Attachments must be 10 MB or smaller.')
        if attachment.content_type not in ALLOWED_ATTACHMENT_TYPES:
            raise forms.ValidationError('Attach a supported document, image, or video file.')




def schedule_hours():
    """Return the shared bookable schedule window."""
    return SCHEDULE_OPEN_HOUR, SCHEDULE_CLOSE_HOUR


class PurchaseVerificationForm(forms.Form):
    """What the buyer submits on the purchase verification page."""

    DATETIME_FORMATS = ['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S']

    quantity = forms.IntegerField(min_value=1, max_value=999, required=False)
    payment_method = forms.ChoiceField(choices=PurchaseRequest.PaymentMethod.choices)
    payment_reference = forms.CharField(max_length=30, required=False)
    payment_proof = forms.ImageField(required=False)  # ImageField also verifies it is a real image (Pillow)
    scheduled_start = forms.DateTimeField(
        input_formats=DATETIME_FORMATS,
        error_messages={'required': 'Pick a day and time on the calendar.', 'invalid': 'That time is not valid.'},
    )
    scheduled_end = forms.DateTimeField(
        input_formats=DATETIME_FORMATS,
        error_messages={'required': 'Pick a day and time on the calendar.', 'invalid': 'That time is not valid.'},
    )
    buyer_note = forms.CharField(max_length=500, required=False)

    def __init__(self, *args, purchase, **kwargs):
        super().__init__(*args, **kwargs)
        self.purchase = purchase

    def full_clean(self):
        with timezone.override(SCHEDULE_TIMEZONE):
            super().full_clean()

    def clean_payment_proof(self):
        proof = self.cleaned_data.get('payment_proof')
        if not proof:
            return proof
        if proof.size > MAX_ATTACHMENT_SIZE_BYTES:
            raise forms.ValidationError('Screenshots must be 10 MB or smaller.')
        if getattr(proof, 'content_type', '') not in PROOF_CONTENT_TYPES:
            raise forms.ValidationError('Upload a JPG, PNG or WebP screenshot.')
        return proof

    def clean(self):
        cleaned = super().clean()
        purchase = self.purchase

        # Quantity: services are always 1.
        if purchase.is_service:
            cleaned['quantity'] = 1
        elif not cleaned.get('quantity') and 'quantity' not in self.errors:
            self.add_error('quantity', 'Enter how many you want.')
        # TODO(stock): validate quantity against Listing.stock_quantity once the
        # stock rules are settled. Intentionally not connected yet.

        # Payment: GCash needs a screenshot, cash does not.
        method = cleaned.get('payment_method')
        if method == PurchaseRequest.PaymentMethod.GCASH:
            if not cleaned.get('payment_proof'):
                self.add_error('payment_proof', 'Upload your GCash payment screenshot, or choose cash on hand.')
        elif method == PurchaseRequest.PaymentMethod.CASH:
            cleaned['payment_proof'] = None
            cleaned['payment_reference'] = ''

        self._clean_schedule(cleaned)
        return cleaned

    def _clean_schedule(self, cleaned):
        start, end = cleaned.get('scheduled_start'), cleaned.get('scheduled_end')
        if not start or not end:
            return

        try:
            validate_schedule_times(start, end)
        except forms.ValidationError as error:
            self.add_error('scheduled_start', error)
