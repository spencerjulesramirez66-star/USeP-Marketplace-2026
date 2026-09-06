from django.db import transaction
from django.db.models import F
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import User, EmailOTP, OTPPurpose
from .utils import generate_otp, send_otp_email
from throttle import check_and_hit, reset, get_client_ip, RateLimitExceeded

LOGIN_RATE_LIMIT = 5           
LOGIN_RATE_WINDOW = 300       
OTP_MAX_ATTEMPTS = 5

CHANGE_PASSWORD_RATE_LIMIT = 5
CHANGE_PASSWORD_RATE_WINDOW = 300

FORGOT_PASSWORD_RATE_LIMIT = 5
FORGOT_PASSWORD_RATE_WINDOW = 300

RESET_VERIFY_RATE_LIMIT = 10
RESET_VERIFY_RATE_WINDOW = 300

RESET_RESEND_RATE_LIMIT = 5
RESET_RESEND_RATE_WINDOW = 300



def setup_login_view(request):

    if request.user.is_authenticated:
        return redirect_user(request.user)

    if request.method == "POST":

        email = request.POST.get("email", "").strip().lower()
        throttle_key = f"login_throttle:{get_client_ip(request)}:{email}"

        try:
            check_and_hit(
                throttle_key,
                limit=LOGIN_RATE_LIMIT,
                window_seconds=LOGIN_RATE_WINDOW,
            )
        except RateLimitExceeded:
            messages.error(
                request,
                "Too many login attempts. Please try again in a few minutes.",
            )
            return redirect("login")

        user = get_user(request, email=email)

        if user is None:
            messages.error(request, "Email and password are incorrect.")
            return redirect("login")

        reset(throttle_key)

        if not user.email_verified:
            otp = generate_otp(user, purpose=OTPPurpose.EMAIL_VERIFICATION)
            request.session["pending_user_id"] = user.pk
            # Starting a fresh email-verification flow — any leftover
            # password-reset session state from an earlier, abandoned
            # attempt is now stale and must not take priority.
            request.session.pop("reset_user_id", None)
            request.session.pop("reset_otp_verified", None)
            if otp is not None:
                send_otp_email(user, otp, purpose=OTPPurpose.EMAIL_VERIFICATION)
            else:
                messages.info(
                    request,
                    "A code was already sent recently — check your inbox.",
                )

            return redirect("verify")

        login(request, user)
        return redirect_user(user)

    return render(request, "accounts/login.html")


def get_verification_context(request):
    """
    Figures out what the verify page is currently being used for.

    Returns (mode, user) where mode is "reset", "email_verification",
    or None if there's nothing pending. Checks the reset flow first —
    if a password reset is in progress, that takes priority.
    """

    reset_user_id = request.session.get("reset_user_id")

    if reset_user_id and not request.session.get("reset_otp_verified", False):
        try:
            return "reset", User.objects.get(pk=reset_user_id)
        except User.DoesNotExist:
            return None, None

    pending_user_id = request.session.get("pending_user_id")

    if pending_user_id:
        try:
            return "email_verification", User.objects.get(pk=pending_user_id)
        except User.DoesNotExist:
            return None, None

    return None, None


def setup_verify_view(request):

    if request.user.is_authenticated:
        return redirect_user(request.user)

    mode, user = get_verification_context(request)
    pending_email = user.email if user else None

    otp_purpose = (
        OTPPurpose.PASSWORD_RESET if mode == "reset" else OTPPurpose.EMAIL_VERIFICATION
    )

    if request.method == "POST":

        if not mode:
            messages.error(request, "Your verification session has expired.")
            return redirect("login")

        if "resend_otp" in request.POST:

            resend_throttle_key = f"resend_otp_throttle:{user.pk}"

            try:
                check_and_hit(resend_throttle_key, limit=5, window_seconds=300)
            except RateLimitExceeded:
                messages.warning(request, "Too many resend attempts. Please try again later.")
                return redirect("verify")

            otp = generate_otp(user, purpose=otp_purpose)

            if otp is not None:
                send_otp_email(user, otp, purpose=otp_purpose)
                messages.success(
                    request,
                    "A new code has been sent — your previous code is no longer valid.",
                )
            else:
                messages.warning(
                    request,
                    "A code was already sent recently — check your inbox.",
                )

            return redirect("verify")

        entered_otp = "".join(
            request.POST.get(f"otp{i}", "") for i in range(1, 7)
        )

        verify_throttle_key = f"verify_throttle:{mode}:{user.pk}"

        try:
            check_and_hit(verify_throttle_key, limit=10, window_seconds=300)
        except RateLimitExceeded:
            messages.error(
                request,
                "Too many verification attempts. Please try again later.",
            )
            if mode == "reset":
                request.session.pop("reset_user_id", None)
                request.session.pop("reset_otp_verified", None)
            else:
                request.session.pop("pending_user_id", None)
            return redirect("login")

        with transaction.atomic():
            otp_record = (
                EmailOTP.objects
                .select_for_update()
                .filter(user=user, purpose=otp_purpose, is_used=False)
                .order_by("-created_at")
                .first()
            )

            if not otp_record:
                # Was a code sent at all, or does one exist but it's
                # already used up (superseded by a resend/re-request)?
                # This tells the user what actually happened instead
                # of a flat, unhelpful "no valid code" message.
                superseded = (
                    EmailOTP.objects
                    .filter(user=user, purpose=otp_purpose)
                    .exists()
                )

                if superseded:
                    messages.error(
                        request,
                        "That code has already been used or a newer one "
                        "was sent — check your email for the most recent code.",
                    )
                else:
                    messages.error(request, "No verification code was found for this account.")

                return redirect("login")

            if otp_record.expires_at < timezone.now():
                otp_record.is_used = True
                otp_record.save(update_fields=["is_used"])
                messages.error(request, "Your verification code has expired.")
                return redirect("verify")

            if otp_record.attempts >= OTP_MAX_ATTEMPTS:
                otp_record.is_used = True
                otp_record.save(update_fields=["is_used"])
                messages.error(request, "Too many verification attempts.")
                if mode == "reset":
                    request.session.pop("reset_user_id", None)
                    request.session.pop("reset_otp_verified", None)
                else:
                    request.session.pop("pending_user_id", None)
                return redirect("login")

            if not check_password(entered_otp, otp_record.otp_hash):

                EmailOTP.objects.filter(pk=otp_record.pk).update(
                    attempts=F("attempts") + 1
                )

                messages.error(request, "Invalid verification code.")
                return redirect("verify")

            otp_record.is_used = True
            otp_record.save(update_fields=["is_used"])

            if mode == "email_verification":
                user.email_verified = True
                user.save(update_fields=["email_verified"])

        reset(verify_throttle_key)

        if mode == "reset":
            request.session["reset_otp_verified"] = True
            return redirect("reset_password")

        login(request, user)
        request.session.pop("pending_user_id", None)

        return redirect_user(user)

    if not mode:
        messages.error(request, "Your verification session has expired.")
        return redirect("login")

    return render(request, "verification/verify.html", {"email": pending_email})

@login_required
def setup_change_password_view(request):

    if request.method == "POST":

        throttle_key = f"change_password_throttle:{request.user.pk}"

        try:
            check_and_hit(
                throttle_key,
                limit=CHANGE_PASSWORD_RATE_LIMIT,
                window_seconds=CHANGE_PASSWORD_RATE_WINDOW,
            )
        except RateLimitExceeded:
            messages.error(
                request,
                "Too many attempts. Please try again in a few minutes.",
            )
            return redirect("change_password")

        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not request.user.check_password(current_password):
            messages.error(request, "Your current password is incorrect.")
            return redirect("change_password")

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect("change_password")

        try:
            validate_password(new_password, request.user)
        except ValidationError as error:
            for message in error:
                messages.error(request, message)
            return redirect("change_password")

        reset(throttle_key)

        was_first_login = request.user.is_first_login

        request.user.set_password(new_password)
        request.user.is_first_login = False
        request.user.save(update_fields=["password", "is_first_login"])

        update_session_auth_hash(request, request.user)

        messages.success(request, "Your password has been changed successfully.")

        if was_first_login:
            return redirect_user(request.user)
        return redirect("profile")

    return render(request, "password/change-password.html")

def get_user(request, email=None):
    email = email if email is not None else request.POST.get("email", "").strip().lower()
    password = request.POST.get("password")

    return authenticate(request, username=email, password=password)


def redirect_user(user):

    if user.is_first_login:
        return redirect("change_password")

    return redirect("dashboard:buyer")

def setup_forgot_password_view(request):

    if request.user.is_authenticated:
        return redirect_user(request.user)

    if request.method == "POST":

        email = request.POST.get("email", "").strip().lower()
        throttle_key = f"forgot_password_throttle:{get_client_ip(request)}:{email}"

        try:
            check_and_hit(
                throttle_key,
                limit=FORGOT_PASSWORD_RATE_LIMIT,
                window_seconds=FORGOT_PASSWORD_RATE_WINDOW,
            )
        except RateLimitExceeded:
            messages.error(
                request,
                "Too many attempts. Please try again in a few minutes.",
            )
            return render(request, "password/forgotpassword.html", {"step": "request"})

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = None

        # Unverified accounts go through email verification first, not
        # password reset — don't send a reset code for them.
        if user is not None and not user.email_verified:
            messages.error(
                request,
                "Please verify your email address before resetting your password.",
            )

            otp = generate_otp(user, purpose=OTPPurpose.EMAIL_VERIFICATION)
            request.session["pending_user_id"] = user.pk
            # Same reasoning as the login view — clear any stale
            # reset-flow state so it can't hijack the verify page.
            request.session.pop("reset_user_id", None)
            request.session.pop("reset_otp_verified", None)

            if otp is not None:
                send_otp_email(user, otp, purpose=OTPPurpose.EMAIL_VERIFICATION)
            else:
                messages.info(
                    request,
                    "A code was already sent recently — check your inbox.",
                )

            return redirect("verify")

        # Don't reveal whether the email exists
        if user is not None:

            existing_otp = (
                EmailOTP.objects
                .filter(user=user, purpose=OTPPurpose.PASSWORD_RESET, is_used=False)
                .order_by("-created_at")
                .first()
            )

            already_pending = (
                existing_otp is not None
                and existing_otp.expires_at > timezone.now()
                and request.session.get("reset_user_id") == user.pk
                and not request.session.get("reset_otp_verified", False)
            )

            if already_pending:
                # A reset is already in progress for this user — don't
                # rotate the code just because they resubmitted the
                # email form. Only the explicit Resend button on the
                # verify page should invalidate/regenerate it.
                messages.info(
                    request,
                    "A reset code was already sent to this email. "
                    "Check your inbox, or use Resend on the next page.",
                )
            else:
                otp = generate_otp(user, purpose=OTPPurpose.PASSWORD_RESET)
                if otp is not None:
                    send_otp_email(user, otp, purpose=OTPPurpose.PASSWORD_RESET)

                request.session["reset_user_id"] = user.pk
                request.session["reset_otp_verified"] = False
                # Clear any stale email-verification session state so
                # it can't be picked up instead — get_verification_context
                # checks reset_user_id first, but this keeps both keys
                # honest regardless of ordering.
                request.session.pop("pending_user_id", None)

                messages.success(
                    request,
                    "If an account exists with that email, a reset code has been sent.",
                )

            return redirect("verify")

        return render(request, "password/forgotpassword.html", {"step": "request"})

    return render(request, "password/forgotpassword.html", {"step": "request"})


def setup_reset_password_view(request):

    if request.user.is_authenticated:
        return redirect_user(request.user)

    reset_user_id = request.session.get("reset_user_id")
    reset_otp_verified = request.session.get("reset_otp_verified", False)

    if not reset_user_id or not reset_otp_verified:
        messages.error(request, "Your reset session has expired.")
        return redirect("forgot_password")

    try:
        user = User.objects.get(pk=reset_user_id)
    except User.DoesNotExist:
        request.session.pop("reset_user_id", None)
        request.session.pop("reset_otp_verified", None)
        messages.error(request, "Your reset session has expired.")
        return redirect("forgot_password")

    if request.method == "POST":

        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return render(request, "password/forgotpassword.html", {"step": "reset"})

        try:
            validate_password(new_password, user)
        except ValidationError as error:
            for message in error:
                messages.error(request, message)
            return render(request, "password/forgotpassword.html", {"step": "reset"})

        user.set_password(new_password)
        user.save(update_fields=["password"])

        request.session.pop("reset_user_id", None)
        request.session.pop("reset_otp_verified", None)

        messages.success(request, "Your password has been reset. You can now log in.")

        return render(request, "password/forgotpassword.html", {"step": "done"})

    return render(request, "password/forgotpassword.html", {"step": "reset"})


@login_required
def logout_view(request):
    auth_logout(request)
    messages.success(request, "You've been logged out.")
    return redirect("login")


@login_required
@require_POST
def upload_profile_picture(request):
    profile_picture = request.FILES.get('profile_picture')

    if profile_picture:
        request.user.profile_picture = profile_picture
        request.user.save(update_fields=['profile_picture'])

    next_url = request.POST.get('next') or 'dashboard:seller'
    return redirect(next_url)

@login_required
def setup_profile_view(request):
    student_profile = getattr(request.user, 'student_profile', None)
    return render(
        request,
        'accounts/profile.html',
        {
            'program': student_profile.program if student_profile and student_profile.program else (student_profile.major.program if student_profile else None),
            'major': student_profile.major if student_profile else None,
        },
    )