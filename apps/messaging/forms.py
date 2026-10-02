from django import forms

from .models import Message

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
