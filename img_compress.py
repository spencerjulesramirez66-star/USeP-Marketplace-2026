from io import BytesIO

from PIL import Image
from django.core.files.base import ContentFile


def compress_to_webp(image_file, quality=80, max_size=(1920, 1920)):
    image = Image.open(image_file)

    # Preserve transparency for PNG images
    if image.mode in ("RGBA", "LA"):
        converted = image.convert("RGBA")
    else:
        converted = image.convert("RGB")

    # Resize while preserving aspect ratio
    converted.thumbnail(max_size, Image.Resampling.LANCZOS)

    output = BytesIO()

    converted.save(
        output,
        format="WEBP",
        quality=quality,
        method=6,
    )

    output.seek(0)

    filename = image_file.name.rsplit(".", 1)[0] + ".webp"

    return ContentFile(output.read(), name=filename)