from django.contrib.auth.decorators import user_passes_test
from django.http import Http404
from django.shortcuts import render


ADMIN_SECTIONS = {
    'overview': ('Overview', 'CAMPUS MARKETPLACE'),
    'accounts': ('Accounts', 'PEOPLE'),
    'listings': ('Listings', 'MARKETPLACE'),
    'categories': ('Categories', 'MARKETPLACE SETUP'),
    'reports': ('Reports', 'TRUST & SAFETY'),
    'activity': ('Activity log', 'AUDIT'),
    'settings': ('Settings', 'PREFERENCES'),
}


@user_passes_test(
    lambda user: user.is_superuser or getattr(user, 'role', None) == 'ADMIN'
)
def administrator_page(request, section='overview'):
    if section not in ADMIN_SECTIONS:
        raise Http404

    section_title, section_eyebrow = ADMIN_SECTIONS[section]
    return render(request, 'administrator/dashboard.html', {
        'active_section': section,
        'section_title': section_title,
        'section_eyebrow': section_eyebrow,
    })