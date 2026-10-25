import logging
import re

from django.conf import settings

logger = logging.getLogger(__name__)

_LABELLED = re.compile(
    r'ref(?:erence)?\.?\s*(?:no|number|num)?\.?\s*[:#]?\s*((?:\d[ \-]?){13})', re.I
)
_GROUPED = re.compile(r'(?<!\d)(\d{4}[ \-]?\d{3}[ \-]?\d{6})(?!\d)')
_PLAIN = re.compile(r'(?<!\d)(\d{13})(?!\d)')


def parse_reference(text):
    """Pull the 13-digit reference out of raw OCR text. Returns digits only, or ''."""
    for pattern in (_LABELLED, _GROUPED, _PLAIN):
        match = pattern.search(text or '')
        if match:
            digits = re.sub(r'\D', '', match.group(1))
            if len(digits) == 13:
                return digits
    return ''


def extract_gcash_reference(image_file):
    """OCR an uploaded screenshot. Never raises: returns '' if anything goes wrong."""
    try:
        import pytesseract
        from PIL import Image, ImageOps

        cmd = getattr(settings, 'TESSERACT_CMD', None)
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd

        image_file.seek(0)
        img = ImageOps.exif_transpose(Image.open(image_file)).convert('L')
        if img.width < 1500:  # small text reads better when enlarged
            img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
        img = ImageOps.autocontrast(img)

        text = pytesseract.image_to_string(img, config='--psm 6', timeout=10)
        return parse_reference(text)
    except Exception:
        logger.exception('GCash reference OCR failed')
        return ''
    finally:
        try:
            image_file.seek(0)  # so Django can still save the file afterwards
        except Exception:
            pass