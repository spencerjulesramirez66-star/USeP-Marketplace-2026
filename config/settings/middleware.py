NO_CACHE_URL_PREFIXES = (
    "/accounts/",
)


class NoCacheAuthenticatedPagesMiddleware:
    """
    Prevents the browser (and any intermediate cache/proxy) from serving
    stale pages via back-button/bfcache after logout.

    Covers two cases automatically, so individual views don't need to
    remember @never_cache:

      1. Any page served while the user is authenticated (dashboards,
         profile pages, anything gated by @login_required).
      2. Any URL under NO_CACHE_URL_PREFIXES — the login/OTP/verify/
         change-password flow — even before the user is authenticated,
         since those pages shouldn't be replayed from history either.

    To extend to a new app's auth-adjacent views, just add its URL
    prefix to NO_CACHE_URL_PREFIXES below. No per-view decorator needed.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        user = getattr(request, 'user', None)
        is_authenticated = bool(user and getattr(user, 'is_authenticated', False))

        should_not_cache = (
            is_authenticated
            or request.path.startswith(NO_CACHE_URL_PREFIXES)
        )

        if should_not_cache:
            response["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"

        return response