from django.contrib.auth.decorators import user_passes_test
from django.http import Http404
from django.shortcuts import render

from .account_queries import form_options
from .permissions import is_marketplace_admin

ADMIN_SECTIONS = {
    'overview': ('Overview', 'CAMPUS MARKETPLACE'),
    'accounts': ('Accounts', 'PEOPLE'),
    'listings': ('Listings', 'MARKETPLACE'),
    'categories': ('Categories', 'MARKETPLACE SETUP'),
    'reports': ('Reports', 'TRUST & SAFETY'),
    'activity': ('Activity log', 'AUDIT'),
    'transactions': ('Transactions', 'OPERATIONS'),
}


def extra_context(section):
    """Data a section's partial needs. Sections without an entry get nothing extra."""
    if section == 'accounts':
        return {'account_options': form_options()}
    if section == 'transactions':
        return {'transaction_tab': 'monitoring'}
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
        **extra_context(section),
    })
