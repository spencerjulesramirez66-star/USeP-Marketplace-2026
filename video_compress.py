"""Re-encode any uploaded video into a broadly browser-playable H.264/AAC
mp4, mirroring how img_compress.compress_to_webp normalizes images.

Handles the common failure case where a phone-recorded .mov/.mp4 is
actually HEVC (H.265) internally, which most non-Safari browsers refuse
to decode even though the file extension looks fine.

Requires the `ffmpeg` binary on PATH. Check with `which ffmpeg` on the
server; install with `sudo apt install ffmpeg` (Debian/Ubuntu) if missing.
"""
import logging
import os
import subprocess
import tempfile

from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


class VideoTranscodeError(Exception):
    """Raised when ffmpeg fails or isn't available."""

def compress_to_mp4(video_file, max_height=1080, timeout=300):
    """Transcode an uploaded video file to H.264/AAC mp4."""
    suffix = os.path.splitext(video_file.name)[1] or '.tmp'

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as src:
        for chunk in video_file.chunks():
            src.write(chunk)
        src_path = src.name

    dst_path = f'{src_path}.out.mp4'

    try:
        result = subprocess.run(
            [
                'ffmpeg', '-y', '-i', src_path,

                '-vf', (
                    f"scale='min(iw,{max_height * 2})':'min(ih,{max_height})':"
                    "force_original_aspect_ratio=decrease,"
                    "scale=trunc(iw/2)*2:trunc(ih/2)*2"
                ),

                '-c:v', 'libopenh264',
                '-b:v', '2M',
                '-pix_fmt', 'yuv420p',

                '-c:a', 'aac',
                '-b:a', '128k',

                '-movflags', '+faststart',

                dst_path,
            ],
            capture_output=True,
            timeout=timeout,
        )

    except FileNotFoundError as error:
        logger.error(
            'ffmpeg binary not found — video transcoding is unavailable.'
        )
        raise VideoTranscodeError(
            'Video processing is not available on this server.'
        ) from error

    except subprocess.TimeoutExpired as error:
        _cleanup(src_path, dst_path)
        logger.warning(
            'ffmpeg timed out while processing %s',
            video_file.name,
        )
        raise VideoTranscodeError(
            'Video processing took too long.'
        ) from error

    if result.returncode != 0 or not os.path.exists(dst_path):
        stderr_tail = (
            result.stderr.decode(errors='ignore')[-800:]
            if result.stderr
            else ''
        )

        logger.warning(
            'ffmpeg failed for %s: %s',
            video_file.name,
            stderr_tail,
        )

        _cleanup(src_path, dst_path)

        raise VideoTranscodeError(
            'This video could not be processed. It may be corrupted '
            'or in an unsupported format.'
        )

    with open(dst_path, 'rb') as handle:
        data = handle.read()

    _cleanup(src_path, dst_path)

    filename = os.path.splitext(video_file.name)[0] + '.mp4'

    return ContentFile(data, name=filename)

def _cleanup(*paths):
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            pass