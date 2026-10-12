"""Single source of truth for 'who counts as a marketplace admin'.

Used by sites.py (admin permission), views.py (placeholder pages) and
context_processors.py (templates). If the role field or value ever changes,
change it here only.
"""

ADMIN_ROLE = 'ADMIN'


def is_marketplace_admin(user):
    return bool(
        user is not None
        and user.is_active
        and (user.is_superuser or getattr(user, 'role', None) == ADMIN_ROLE)
    )
