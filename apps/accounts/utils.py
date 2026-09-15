import secrets
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.utils import timezone

<<<<<<< HEAD
from .models import EmailOTP

OTP_LENGTH = 6
OTP_TTL_MINUTES = 5
OTP_RESEND_COOLDOWN_SECONDS = 60


def generate_otp(user, *, force=False):
    """
    Creates a new OTP for the user, invalidating any previous unused ones.

    Returns the plaintext OTP, or None if a resend was requested too soon
    (unless force=True). Callers should check for None and show a
    "please wait" message instead of silently re-sending mail.
    """
    cooldown_key = f"otp_cooldown:{user.pk}"
=======
from .models import EmailOTP, OTPPurpose

OTP_LENGTH = 6
OTP_TTL_MINUTES = 10
OTP_RESEND_COOLDOWN_SECONDS = 60


def generate_otp(user, purpose, *, force=False):
    cooldown_key = f"otp_cooldown:{purpose}:{user.pk}"
>>>>>>> 6fe02047874f2a41b2024f6c526d69b183b30d75

    if not force and cache.get(cooldown_key):
        return None

    otp = str(secrets.randbelow(1_000_000)).zfill(OTP_LENGTH)

<<<<<<< HEAD
    # Invalidate any still-active codes in one query instead of N saves.
    EmailOTP.objects.filter(user=user, is_used=False).update(is_used=True)
=======
    EmailOTP.objects.filter(
        user=user,
        purpose=purpose,
        is_used=False,
    ).update(is_used=True)
>>>>>>> 6fe02047874f2a41b2024f6c526d69b183b30d75

    EmailOTP.objects.create(
        user=user,
        otp_hash=make_password(otp),
<<<<<<< HEAD
        expires_at=timezone.now() + timedelta(minutes=OTP_TTL_MINUTES),
    )

    # Block another generate_otp() call for this user until the cooldown passes.
=======
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=OTP_TTL_MINUTES),
    )

>>>>>>> 6fe02047874f2a41b2024f6c526d69b183b30d75
    cache.set(cooldown_key, True, timeout=OTP_RESEND_COOLDOWN_SECONDS)

    return otp


<<<<<<< HEAD
def send_otp_email(user, otp):
    send_mail(
        subject="USeP Marketplace Verification Code",
        message=(
            f"Hello {user.first_name},\n\n"
            f"Your verification code is: {otp}\n\n"
=======
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
>>>>>>> 6fe02047874f2a41b2024f6c526d69b183b30d75
            f"This code will expire in {OTP_TTL_MINUTES} minutes.\n\n"
            f"If you did not request this code, please ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )