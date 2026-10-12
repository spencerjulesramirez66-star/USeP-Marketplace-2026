from django.contrib.admin.apps import AdminConfig


class MarketplaceAdminConfig(AdminConfig):
    default_site = 'apps.administration.sites.MarketplaceAdminSite'