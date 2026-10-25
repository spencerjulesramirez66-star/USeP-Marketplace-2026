"""Emails sent when an admin manages an account.

Uses Django's send_mail, so it goes out through your Brevo settings
(EMAIL_* and DEFAULT_FROM_EMAIL), same as the OTP emails in accounts/utils.py.
"""

from django.conf import settings
from django.core.mail import send_mail


def send_account_created_email(user, temporary_password):
    """Tell a new user how to sign in. Raises if the email can't be sent."""
    site_url = getattr(settings, 'SITE_URL', '')      # optional, e.g. 'https://marketplace.usep.edu.ph'
    sign_in_line = f'Sign in here: {site_url}\n\n' if site_url else ''
    role_line = 'This is an administrator account.\n\n' if user.is_admin else ''

    send_mail(
        subject='Your USeP Marketplace account',
        message=(
            f'Hello {user.first_name},\n\n'
            f'An administrator created a USeP Marketplace account for you.\n\n'
            f'{role_line}'
            f'To sign in, use:\n'
            f'  Email: {user.email}\n'
            f'  Temporary password: {temporary_password}\n\n'
            f'{sign_in_line}'
            f'You will be asked to choose your own password the first time you sign in.\n'
            f'Please do not share this password with anyone.\n\n'
            f'If you were not expecting this email, you can ignore it.'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )