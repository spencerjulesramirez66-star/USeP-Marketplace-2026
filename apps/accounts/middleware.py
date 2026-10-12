from django.conf import settings
from django.shortcuts import redirect
from django.urls import Resolver404, resolve

# URL names a first-login user may still reach.
EXEMPT_URL_NAMES = {"change_password", "logout"}


class ForcePasswordChangeMiddleware:
    """Keep users with is_first_login=True on the change-password page.

    Add after AuthenticationMiddleware (and MessageMiddleware) in settings.MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Skip empty prefixes: "".startswith-matching would exempt every URL.
        self.asset_prefixes = tuple(
            prefix for prefix in (settings.STATIC_URL, settings.MEDIA_URL) if prefix
        )

    def __call__(self, request):
        user = request.user

        if user.is_authenticated and user.is_first_login:
            if not request.path.startswith(self.asset_prefixes):
                try:
                    url_name = resolve(request.path_info).url_name
                except Resolver404:
                    return self.get_response(request)

                if url_name not in EXEMPT_URL_NAMES:
                    return redirect("change_password")

        return self.get_response(request)
