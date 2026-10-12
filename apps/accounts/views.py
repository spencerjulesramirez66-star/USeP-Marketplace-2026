from functools import wraps

from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout as auth_logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from PIL import Image, UnidentifiedImageError

from .models import EmailOTP, OTPPurpose, User
from .utils import generate_otp, send_otp_email
from throttle import (
    RateLimitExceeded,
    check_and_hit,
    get_client_ip,
    reset,
)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

RATE_WINDOW = 300  # seconds, shared by every throttle below

LOGIN_LIMIT = 5
CHANGE_PASSWORD_LIMIT = 5
FORGOT_PASSWORD_LIMIT = 5
OTP_RESEND_LIMIT = 5
OTP_VERIFY_LIMIT = 10
PROFILE_UPDATE_LIMIT = 10

OTP_MAX_ATTEMPTS = 5

MAX_PROFILE_PICTURE_SIZE = 5 * 1024 * 1024
MAX_PROFILE_PICTURE_DIMENSION = 4096
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}

PROFILE_FIELDS = {
    "first_name": {"label": "First name", "max_length": 100, "required": True},
    "middle_name": {"label": "Middle name", "max_length": 100, "required": False},
    "last_name": {"label": "Last name", "max_length": 100, "required": True},
    "contact_num": {"label": "Contact number", "max_length": 11, "required": True},
}
NAME_FIELDS = {"first_name", "middle_name", "last_name"}

FORGOT_TEMPLATE = "password/forgotpassword.html"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def account_is_usable(user):
    """An account may proceed only if it exists, is active and not deleted."""
    return user is not None and user.is_active and not user.is_deleted


def safe_redirect_url(request, destination, fallback="profile"):
    if destination and url_has_allowed_host_and_scheme(
        url=destination,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return destination
    return reverse(fallback)


def redirect_user(request, user, next_url=None):
    """Send a logged-in user to the right landing page."""
    if user.is_first_login:
        return redirect("change_password")

    if user.is_admin:
        return redirect("admin:index")

    return redirect(
        safe_redirect_url(request, next_url, fallback="dashboard:buyer")
    )


def clear_reset_session(request):
    request.session.pop("reset_user_id", None)
    request.session.pop("reset_otp_verified", None)


def clear_verification_session(request):
    clear_reset_session(request)
    request.session.pop("pending_user_id", None)


def get_usable_user(pk):
    user = User.objects.filter(pk=pk).first()
    return user if account_is_usable(user) else None


def start_email_verification(request, user):
    """Begin (or resume) the email-verification flow and go to the verify page."""
    otp = generate_otp(user, purpose=OTPPurpose.EMAIL_VERIFICATION)

    request.session["pending_user_id"] = user.pk
    # Stale password-reset state must not take priority on the verify page.
    clear_reset_session(request)

    if otp is not None:
        send_otp_email(user, otp, purpose=OTPPurpose.EMAIL_VERIFICATION)
    else:
        messages.info(
            request,
            "A code was already sent recently — check your inbox.",
        )

    return redirect("verify")


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _fail(request, message, status=400):
    if _is_ajax(request):
        return JsonResponse({"error": message}, status=status)
    messages.error(request, message)
    return redirect("profile")


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

def anonymous_only(view):
    """Logged-in users are redirected away from login/verify/reset pages."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect_user(request, request.user, request.GET.get("next"))
        return view(request, *args, **kwargs)
    return wrapper


def active_account_required(view):
    """login_required + the account must still be active and not deleted."""
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not account_is_usable(request.user):
            auth_logout(request)
            if _is_ajax(request):
                return JsonResponse(
                    {"error": "Your account is unavailable."}, status=403
                )
            messages.error(request, "Your account is unavailable.")
            return redirect("login")
        return view(request, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def authenticate_user(request, email):
    user = authenticate(
        request,
        username=email,
        password=request.POST.get("password"),
    )
    return user if account_is_usable(user) else None


@anonymous_only
def setup_login_view(request):
    if request.method != "POST":
        return render(
            request,
            "accounts/login.html",
            {"next": request.GET.get("next", "")},
        )

    email = request.POST.get("email", "").strip().lower()
    throttle_key = f"login_throttle:{get_client_ip(request)}:{email}"

    try:
        check_and_hit(throttle_key, limit=LOGIN_LIMIT, window_seconds=RATE_WINDOW)
    except RateLimitExceeded:
        messages.error(
            request,
            "Too many login attempts. Please try again in a few minutes.",
        )
        return redirect("login")

    user = authenticate_user(request, email)

    if user is None:
        messages.error(request, "Email and password are incorrect.")
        return redirect("login")

    reset(throttle_key)

    if not user.email_verified:
        return start_email_verification(request, user)

    login(request, user)
    return redirect_user(request, user, request.POST.get("next"))


@login_required
@require_POST
def logout_view(request):
    auth_logout(request)
    messages.success(request, "You've been logged out.")
    return redirect("login")


# ---------------------------------------------------------------------------
# OTP verification (email verification + password reset share this page)
# ---------------------------------------------------------------------------

def get_verification_context(request):
    """
    Work out what the verify page is currently for.

    Returns (mode, user): mode is "reset" or "email_verification",
    or (None, None) if nothing valid is pending. A password reset in
    progress takes priority over email verification.
    """
    reset_user_id = request.session.get("reset_user_id")

    if reset_user_id and not request.session.get("reset_otp_verified", False):
        user = get_usable_user(reset_user_id)
        return ("reset", user) if user else (None, None)

    pending_user_id = request.session.get("pending_user_id")

    if pending_user_id:
        user = get_usable_user(pending_user_id)
        return ("email_verification", user) if user else (None, None)

    return None, None


def _resend_otp(request, user, purpose):
    try:
        check_and_hit(
            f"resend_otp_throttle:{user.pk}",
            limit=OTP_RESEND_LIMIT,
            window_seconds=RATE_WINDOW,
        )
    except RateLimitExceeded:
        messages.warning(request, "Too many resend attempts. Please try again later.")
        return redirect("verify")

    otp = generate_otp(user, purpose=purpose)

    if otp is not None:
        send_otp_email(user, otp, purpose=purpose)
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


def _check_otp(request, user, mode, purpose):
    entered_otp = "".join(
        request.POST.get(f"otp{i}", "") for i in range(1, 7)
    )

    throttle_key = f"verify_throttle:{mode}:{user.pk}"

    try:
        check_and_hit(throttle_key, limit=OTP_VERIFY_LIMIT, window_seconds=RATE_WINDOW)
    except RateLimitExceeded:
        messages.error(
            request,
            "Too many verification attempts. Please try again later.",
        )
        clear_verification_session(request)
        return redirect("login")

    with transaction.atomic():
        otp_record = (
            EmailOTP.objects
            .select_for_update()
            .filter(user=user, purpose=purpose, is_used=False)
            .order_by("-created_at")
            .first()
        )

        if not otp_record:
            if EmailOTP.objects.filter(user=user, purpose=purpose).exists():
                messages.error(
                    request,
                    "That code has already been used or a newer one "
                    "was sent — check your email for the most recent code.",
                )
            else:
                messages.error(
                    request,
                    "No verification code was found for this account.",
                )
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
            clear_verification_session(request)
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

    reset(throttle_key)

    if mode == "reset":
        request.session["reset_otp_verified"] = True
        return redirect("reset_password")

    login(request, user)
    request.session.pop("pending_user_id", None)
    return redirect_user(request, user)


@anonymous_only
def setup_verify_view(request):
    mode, user = get_verification_context(request)

    if not user:
        messages.error(request, "Your verification session has expired.")
        return redirect("login")

    if request.method != "POST":
        return render(request, "verification/verify.html", {"email": user.email})

    purpose = (
        OTPPurpose.PASSWORD_RESET
        if mode == "reset"
        else OTPPurpose.EMAIL_VERIFICATION
    )

    if "resend_otp" in request.POST:
        return _resend_otp(request, user, purpose)

    return _check_otp(request, user, mode, purpose)


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------

@active_account_required
def setup_change_password_view(request):
    if request.method != "POST":
        return render(request, "password/change-password.html")

    throttle_key = f"change_password_throttle:{request.user.pk}"

    try:
        check_and_hit(
            throttle_key,
            limit=CHANGE_PASSWORD_LIMIT,
            window_seconds=RATE_WINDOW,
        )
    except RateLimitExceeded:
        messages.error(request, "Too many attempts. Please try again in a few minutes.")
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
        for message in error.messages:
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
        return redirect_user(request, request.user)
    return redirect("profile")


@anonymous_only
def setup_forgot_password_view(request):
    if request.method != "POST":
        return render(request, FORGOT_TEMPLATE, {"step": "request"})

    email = request.POST.get("email", "").strip().lower()
    throttle_key = f"forgot_password_throttle:{get_client_ip(request)}:{email}"

    try:
        check_and_hit(
            throttle_key,
            limit=FORGOT_PASSWORD_LIMIT,
            window_seconds=RATE_WINDOW,
        )
    except RateLimitExceeded:
        messages.error(request, "Too many attempts. Please try again in a few minutes.")
        return render(request, FORGOT_TEMPLATE, {"step": "request"})

    user = User.objects.filter(email__iexact=email).first()

    if not account_is_usable(user):
        messages.success(
            request,
            "If an eligible account exists with that email, "
            "instructions will be sent.",
        )
        return render(request, FORGOT_TEMPLATE, {"step": "request"})

    if not user.email_verified:
        # Same wording as the normal path so this doesn't leak account state.
        # They verify their email first, then can reset their password.
        response = start_email_verification(request, user)
        messages.success(
            request,
            "If an account exists with that email, a code has been sent.",
        )
        return response

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
        request.session.pop("pending_user_id", None)

        messages.success(
            request,
            "If an account exists with that email, a reset code has been sent.",
        )

    return redirect("verify")


@anonymous_only
def setup_reset_password_view(request):
    user = None

    if request.session.get("reset_otp_verified"):
        user = get_usable_user(request.session.get("reset_user_id"))

    if user is None:
        clear_reset_session(request)
        messages.error(request, "Your reset session has expired.")
        return redirect("forgot_password")

    if request.method != "POST":
        return render(request, FORGOT_TEMPLATE, {"step": "reset"})

    new_password = request.POST.get("new_password")
    confirm_password = request.POST.get("confirm_password")

    if new_password != confirm_password:
        messages.error(request, "New passwords do not match.")
        return render(request, FORGOT_TEMPLATE, {"step": "reset"})

    try:
        validate_password(new_password, user)
    except ValidationError as error:
        for message in error.messages:
            messages.error(request, message)
        return render(request, FORGOT_TEMPLATE, {"step": "reset"})

    user.set_password(new_password)
    user.save(update_fields=["password"])
    clear_reset_session(request)

    messages.success(request, "Your password has been reset. You can now log in.")
    return render(request, FORGOT_TEMPLATE, {"step": "done"})


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

def validate_profile_picture(upload):
    """Validate an uploaded image before it is saved."""
    if not upload:
        raise ValidationError("Please select an image.")

    if upload.size > MAX_PROFILE_PICTURE_SIZE:
        raise ValidationError("The image must not exceed 5 MB.")

    try:
        with Image.open(upload) as image:
            if image.format not in ALLOWED_IMAGE_FORMATS:
                raise ValidationError("Upload a JPEG, PNG, or WebP image.")

            if max(image.size) > MAX_PROFILE_PICTURE_DIMENSION:
                raise ValidationError(
                    f"Image must be at most {MAX_PROFILE_PICTURE_DIMENSION}px "
                    "wide and tall."
                )

            image.verify()

    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
        ValueError,
    ):
        raise ValidationError("The uploaded file is not a valid image.")

    finally:
        upload.seek(0)


@active_account_required
def setup_profile_view(request):
    student_profile = getattr(request.user, "student_profile", None)

    major = student_profile.major if student_profile else None
    program = student_profile.program if student_profile else None

    if program is None and major is not None:
        program = major.program

    return render(
        request,
        "accounts/profile.html",
        {"program": program, "major": major},
    )


@active_account_required
@require_POST
def upload_profile_picture(request):
    try:
        picture = request.FILES.get("profile_picture")
        validate_profile_picture(picture)
        request.user.profile_picture = picture
        request.user.save(update_fields=["profile_picture"])

    except ValidationError as error:
        for message in error.messages:
            messages.error(request, message)

    except (OSError, ValueError):
        messages.error(
            request,
            "The image could not be processed. Please try another image.",
        )

    else:
        messages.success(request, "Profile picture updated successfully.")

    return redirect(
        safe_redirect_url(request, request.POST.get("next"), fallback="profile")
    )


@active_account_required
@require_POST
def update_profile_field(request):
    throttle_key = f"update_profile_field_throttle:{request.user.pk}"

    try:
        check_and_hit(
            throttle_key,
            limit=PROFILE_UPDATE_LIMIT,
            window_seconds=RATE_WINDOW,
        )
    except RateLimitExceeded:
        return _fail(request, "Too many attempts. Please try again later.", status=429)

    field = request.POST.get("field", "").strip()
    value = request.POST.get("value", "").strip()

    rules = PROFILE_FIELDS.get(field)
    if rules is None:
        return _fail(request, "Invalid field.")

    label = rules["label"]

    if rules["required"] and not value:
        return _fail(request, f"{label} cannot be empty.")

    if len(value) > rules["max_length"]:
        return _fail(request, f"{label} is too long.")

    if field in NAME_FIELDS and any(char.isdigit() for char in value):
        return _fail(request, f"{label} cannot contain digits.")

    if field == "contact_num":
        value = value.replace(" ", "").replace("-", "")

        if not value.isdigit():
            return _fail(request, "Contact number must contain digits only.")

        if len(value) != 11 or not value.startswith("09"):
            return _fail(
                request,
                "Enter a valid 11-digit Philippine mobile number starting with 09.",
            )

    setattr(request.user, field, value)

    try:
        with transaction.atomic():
            request.user.save(update_fields=[field])
    except IntegrityError:
        if field == "contact_num":
            return _fail(request, "That contact number is already in use.")
        raise

    reset(throttle_key)

    if _is_ajax(request):
        return JsonResponse({"field": field, "value": value})

    messages.success(request, f"{label} updated successfully.")
    return redirect("profile")