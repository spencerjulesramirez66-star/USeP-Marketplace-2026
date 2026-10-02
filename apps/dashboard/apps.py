from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dashboard'

    # No ready()/signals hook: the only signal this app had was the new-
    # message notification, which moved to apps.messaging along with the
    # Message model it listened to.
