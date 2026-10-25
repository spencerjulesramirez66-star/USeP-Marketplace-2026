from django.contrib.auth.decorators import user_passes_test
from django.http import Http404
from django.shortcuts import render

from .account_queries import form_options
from .permissions import can_create_admin, is_marketplace_admin

ADMIN_SECTIONS = {
    'overview': ('Overview', 'CAMPUS MARKETPLACE'),
    'accounts': ('Accounts', 'PEOPLE'),
    'listings': ('Listings', 'MARKETPLACE'),
    'categories': ('Categories', 'MARKETPLACE SETUP'),
    'reports': ('Reports', 'TRUST & SAFETY'),
    'activity': ('Activity log', 'AUDIT'),
}


def extra_context(section, user):
    """Data a section's partial needs. Sections without an entry get nothing extra."""
    if section == 'accounts':
        return {'account_options': {**form_options(), 'can_create_admin': can_create_admin(user)}}
    return {}


@user_passes_test(is_marketplace_admin)
def administrator_page(request, section='overview'):
    if section not in ADMIN_SECTIONS:
        raise Http404

    section_title, section_eyebrow = ADMIN_SECTIONS[section]
    return render(request, 'administration/dashboard.html', {
        'active_section': section,
        'section_title': section_title,
        'section_eyebrow': section_eyebrow,
        **extra_context(section, request.user),
    })