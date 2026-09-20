"""Server-side handling for message attachments: size limits and image compression."""
import logging

# Adjust this import to wherever compress_to_webp lives in your project.
from img_compress import compress_to_webp

logger = logging.getLogger(__name__)

DEFAULT_MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024

# GIFs would lose animation and SVGs can't be opened by Pillow; store them untouched.
SKIP_COMPRESSION_TYPES = {'image/gif', 'image/svg+xml'}


def max_attachment_size(form):
    """Use the form's limit (the same value the chat JS enforces) with a safe fallback."""
    limit = getattr(form, 'max_attachment_size_bytes', None)
    if callable(limit):
        limit = limit()
    return limit or DEFAULT_MAX_ATTACHMENT_SIZE_BYTES


def validate_attachment_sizes(files, limit):
    """Return an error message for the first oversized file, or None if all fit."""
    for upload in files:
        if upload.size > limit:
            return f'{upload.name} is too large. Maximum file size is {round(limit / (1024 * 1024))} MB.'
    return None


def prepare_attachment(upload):
    """Compress images to WebP; return every other file (or a failed image) unchanged."""
    content_type = (getattr(upload, 'content_type', '') or '').lower()
    if not content_type.startswith('image/') or content_type in SKIP_COMPRESSION_TYPES:
        return upload
    try:
        return compress_to_webp(upload)
    except Exception:
        logger.exception('Image compression failed for %s; storing the original.', upload.name)
        upload.seek(0)
        return upload