from .permissions import is_marketplace_admin

ADMIN_NAMESPACES = {'admin', 'administration'}


def admin_context(request):
    """Adds two flags to every template:

    is_marketplace_admin - the signed-in user is a superuser or has role ADMIN
    is_admin_area        - the current URL is under the 'admin' or 'administration' namespace
    """
    match = getattr(request, 'resolver_match', None)
    namespaces = set(match.namespaces) if match else set()
    return {
        'is_marketplace_admin': is_marketplace_admin(getattr(request, 'user', None)),
        'is_admin_area': bool(namespaces & ADMIN_NAMESPACES),
    }
