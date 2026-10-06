"""Helpers for preparing user-uploaded message attachments before they're
saved to a FileField.

`prepare_attachment` is called once per file in
`_save_message_with_attachments` (apps/dashboard/views.py), for every file
in `request.FILES.getlist('attachments')`. Its return value is assigned
directly to `MessageAttachment.file`.

Image attachments are re-encoded to webp via the same `compress_to_webp`
helper Listing/ListingImage already use in models.py, so message photos
get the same size/format treatment as listing photos instead of being
stored raw.

Video attachments are transcoded to H.264/AAC mp4 via `compress_to_mp4`,
so any source codec/container a phone or camera produces (HEVC .mov
included) comes out in a format every browser can actually play.
"""
import os
import re
import uuid

from django.core.exceptions import SuspiciousFileOperation
from img_compress import compress_to_webp
from video_compress import VideoTranscodeError, compress_to_mp4

# Extensions that get run through compress_to_webp.
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

# Extensions that get run through compress_to_mp4. Accepting a wide set of
# source containers is safe here specifically because every one of them
# gets re-encoded to the same output format — none are stored as-is.
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.webm', '.avi', '.mkv', '.m4v', '.3gp'}

# Non-media extensions that are stored as-is.
OTHER_ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt'}

ALLOWED_ATTACHMENT_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | OTHER_ALLOWED_EXTENSIONS

# Guard against huge originals before we even try to decode them.
MAX_ATTACHMENT_BYTES = 100 * 1024 * 1024  # 100 MB — videos are bigger than images before compression


class AttachmentRejected(Exception):
    """Raised when an uploaded file fails validation."""


def _safe_extension(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise AttachmentRejected(f'"{ext or "unknown"}" files are not supported.')
    return ext


def _unique_name(filename):
    stem = os.path.splitext(filename)[0]
    stem = re.sub(r'[^A-Za-z0-9_-]+', '-', stem).strip('-')[:60] or 'attachment'
    return stem, uuid.uuid4().hex[:8]


def prepare_attachment(uploaded_file):
    """Validate an uploaded file, compress it if it's an image, and return
    something safe to assign to MessageAttachment.file.
    """
    if not uploaded_file or not getattr(uploaded_file, 'name', None):
        raise AttachmentRejected('No file was provided.')

    if uploaded_file.size == 0:
        raise AttachmentRejected('The file is empty.')

    if uploaded_file.size > MAX_ATTACHMENT_BYTES:
        raise AttachmentRejected(
            f'"{uploaded_file.name}" is too large '
            f'(max {MAX_ATTACHMENT_BYTES // (1024 * 1024)}MB).'
        )

    ext = _safe_extension(uploaded_file.name)
    stem, suffix = _unique_name(uploaded_file.name)

    if ext in IMAGE_EXTENSIONS:
        try:
            compressed = compress_to_webp(uploaded_file)
        except Exception as error:  # Pillow raises several distinct error
            # types (UnidentifiedImageError, OSError, ...) for a corrupt or
            # unsupported image; treat all of them as a rejected upload
            # rather than a 500.
            raise AttachmentRejected(f'"{uploaded_file.name}" could not be processed as an image.') from error
        compressed.name = f'{stem}-{suffix}.webp'
        return compressed

    if ext in VIDEO_EXTENSIONS:
        try:
            compressed = compress_to_mp4(uploaded_file)
        except VideoTranscodeError as error:
            raise AttachmentRejected(str(error)) from error
        compressed.name = f'{stem}-{suffix}.mp4'
        return compressed

    try:
        uploaded_file.name = f'{stem}-{suffix}{ext}'
    except SuspiciousFileOperation:
        raise AttachmentRejected('The file name is not valid.')
    return uploaded_file