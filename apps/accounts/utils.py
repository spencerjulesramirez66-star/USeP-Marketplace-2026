import secrets
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from .models import EmailOTP, OTPPurpose

OTP_LENGTH = 6
OTP_TTL_MINUTES = 10
OTP_RESEND_COOLDOWN_SECONDS = 60


def generate_otp(user, purpose, *, force=False):
    cooldown_key = f"otp_cooldown:{purpose}:{user.pk}"

    if not force and cache.get(cooldown_key):
        return None

    otp = str(secrets.randbelow(1_000_000)).zfill(OTP_LENGTH)

    EmailOTP.objects.filter(
        user=user,
        purpose=purpose,
        is_used=False,
    ).update(is_used=True)

    EmailOTP.objects.create(
        user=user,
        otp_hash=make_password(otp),
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=OTP_TTL_MINUTES),
    )

    cache.set(cooldown_key, True, timeout=OTP_RESEND_COOLDOWN_SECONDS)

    return otp


def send_otp_email(user, otp, purpose=OTPPurpose.EMAIL_VERIFICATION):

    if purpose == OTPPurpose.PASSWORD_RESET:
        subject = "USeP Marketplace Password Reset Code"
        intro = "You requested to reset your password."
    else:
        subject = "USeP Marketplace Verification Code"
        intro = "Thank you for signing up."

    send_mail(
        subject=subject,
        message=(
            f"Hello {user.first_name},\n\n"
            f"{intro}\n\n"
            f"Your code is: {otp}\n\n"
            f"This code will expire in {OTP_TTL_MINUTES} minutes.\n\n"
            f"If you did not request this code, please ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )