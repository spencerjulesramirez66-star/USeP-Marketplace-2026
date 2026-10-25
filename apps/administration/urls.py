from django.urls import path

from . import account_views
from . import transaction_views
from .views import administrator_page

app_name = 'administration'

# The overview lives at admin:index (see sites.py), so it is not listed here.
urlpatterns = [
    path('accounts/', administrator_page, {'section': 'accounts'}, name='accounts'),
    path('listings/', administrator_page, {'section': 'listings'}, name='listings'),
    path('categories/', administrator_page, {'section': 'categories'}, name='categories'),
    path('reports/', administrator_page, {'section': 'reports'}, name='reports'),
    path('activity/', administrator_page, {'section': 'activity'}, name='activity'),
    path('transactions/monitoring/', administrator_page, {'section': 'transactions'}, name='transactions_monitoring'),
    path('transactions/history/', transaction_views.transaction_history, name='transactions_history'),
    path('transactions/data/', transaction_views.transaction_history_data, name='transactions_data'),
    path('transactions/monitoring/data/', transaction_views.transaction_monitoring_data, name='transactions_monitoring_data'),
    path('transactions/<int:purchase_id>/', transaction_views.transaction_detail, name='transaction_detail'),
    path('transactions/export.csv', transaction_views.transaction_export, name='transactions_export'),

    # Accounts: JSON endpoints used by admin-accounts.js
    path('accounts/data/', account_views.accounts_data, name='accounts_data'),
    path('accounts/create/', account_views.account_create, name='account_create'),
    path('accounts/<int:user_id>/', account_views.account_detail, name='account_detail'),
    path('accounts/<int:user_id>/update/', account_views.account_update, name='account_update'),
    path('accounts/<int:user_id>/<slug:action>/', account_views.account_action, name='account_action'),
]
