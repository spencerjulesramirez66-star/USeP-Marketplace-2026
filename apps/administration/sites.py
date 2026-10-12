from django.contrib import admin
from django.shortcuts import render

from .permissions import is_marketplace_admin
from .views import ADMIN_SECTIONS


class MarketplaceAdminSite(admin.AdminSite):
    site_header = 'USeP Marketplace Administration'
    site_title = 'USeP Marketplace Admin'
    index_title = 'Overview'

    def has_permission(self, request):
        return is_marketplace_admin(request.user)

    def index(self, request, extra_context=None):
        title, eyebrow = ADMIN_SECTIONS['overview']
        context = {
            **self.each_context(request),
            'active_section': 'overview',
            'section_title': title,
            'section_eyebrow': eyebrow,
            **(extra_context or {}),
        }
        return render(request, 'administration/dashboard.html', context)
