from django.core.cache import cache


class RateLimitExceeded(Exception):
    pass


def get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")

    if forwarded:
        return forwarded.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR", "unknown")


def check_and_hit(key, *, limit, window_seconds):
    """
    Fixed-window counter. Raises RateLimitExceeded once `limit` hits have
    happened inside `window_seconds`. Cheap: one cache read + one write
    per call, no DB hit, so it's safe to use on every login POST.
    """
    count = cache.get(key, 0)

    if count >= limit:
        raise RateLimitExceeded

    # incr() is atomic on Django's cache backends; falls back to set() the
    # first time the key doesn't exist yet.
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)


def reset(key):
    cache.delete(key)