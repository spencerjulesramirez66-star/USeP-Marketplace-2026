from django.urls import path
from .views import administrator_page

urlpatterns = [
    path('', administrator_page, name='dashboard'),
    path('accounts/', administrator_page, {'section': 'accounts'}, name='admin_accounts'),
    path('listings/', administrator_page, {'section': 'listings'}, name='admin_listings'),
    path('categories/', administrator_page, {'section': 'categories'}, name='admin_categories'),
    path('reports/', administrator_page, {'section': 'reports'}, name='admin_reports'),
    path('activity/', administrator_page, {'section': 'activity'}, name='admin_activity'),
    path('settings/', administrator_page, {'section': 'settings'}, name='admin_settings'),
]