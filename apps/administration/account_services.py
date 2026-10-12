"""Business rules for managing accounts.

Everything that CHANGES an account lives here, so the web UI, and later the
bulk import, all follow the same rules. Views only translate requests to and
from these functions.

Nothing in this file hard-deletes. "Delete" means soft delete (User.soft_delete).
"""

import secrets
import string

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction

# Change "accounts" to the app label that holds your models.py.
from apps.accounts.models import Roles, StaffProfile, StudentProfile

User = get_user_model()

STUDENT_NUMBER_DIGITS = 5      # 2026-00042  -> 4 + "-" + 5 = 10 chars (StudentProfile.student_id max_length)
STAFF_NUMBER_DIGITS = 4        # 4821-DV     -> 4 + "-" + 2 = 7 chars  (StaffProfile.staff_id max_length)
ID_RETRIES = 5                 # tries again if two admins create accounts at the same moment


class AccountActionError(Exception):
    """A rule was broken. The message is safe to show to the admin."""


# --------------------------------------------------------------------------
# ID and password generation
# --------------------------------------------------------------------------

def next_student_id(year):
    """Next free student ID for a year: YYYY-00001, YYYY-00002, ..."""
    prefix = f'{year}-'
    last = (
        StudentProfile.objects
        .filter(student_id__startswith=prefix)
        .order_by('-student_id')          # zero padded, so text order == number order
        .values_list('student_id', flat=True)
        .first()
    )
    number = int(last.split('-')[1]) + 1 if last else 1
    if number >= 10 ** STUDENT_NUMBER_DIGITS:
        raise AccountActionError(f'Student IDs for {year} are full.')
    return f'{year}-{number:0{STUDENT_NUMBER_DIGITS}d}'


def new_staff_id(campus):
    """Random 4 digits + campus code, e.g. 4821-DV. Picks again if already taken."""
    for _ in range(50):
        number = secrets.randbelow(10 ** STAFF_NUMBER_DIGITS)
        staff_id = f'{number:0{STAFF_NUMBER_DIGITS}d}-{campus.campus_code.upper()}'
        if not StaffProfile.objects.filter(staff_id=staff_id).exists():
            return staff_id
    raise AccountActionError('Could not find a free staff ID. Please try again.')


def generate_temporary_password(length=10):
    """Easy to read out loud: no 0/O, 1/l/I look-alikes."""
    alphabet = ''.join(c for c in string.ascii_letters + string.digits if c not in '0O1lI')
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# --------------------------------------------------------------------------
# Audit trail (uses Django's built-in LogEntry, so no model changes needed)
# --------------------------------------------------------------------------

def log_action(actor, target, flag, message):
    LogEntry.objects.create(
        user=actor,
        content_type=ContentType.objects.get_for_model(User),
        object_id=str(target.pk),
        object_repr=str(target)[:200],
        action_flag=flag,
        change_message=message,
    )


def _with_reason(text, reason):
    return f'{text} Reason: {reason}' if reason else text


# --------------------------------------------------------------------------
# Guards
# --------------------------------------------------------------------------

def ensure_manageable(actor, user):
    if user.pk == actor.pk:
        raise AccountActionError("You can't change your own account from this page.")
    if user.is_admin:
        raise AccountActionError("Admin accounts can't be changed from this page.")


# --------------------------------------------------------------------------
# Create / update
# --------------------------------------------------------------------------

def create_account(*, actor, data):
    """Create a student or staff account from validated form data.

    Returns (user, temporary_password). The password is only known here, so the
    caller must show it to the admin right away.
    """
    account_type = data['account_type']
    password = generate_temporary_password()

    for attempt in range(ID_RETRIES):
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=data['email'],
                    password=password,
                    first_name=data['first_name'],
                    middle_name=data.get('middle_name', ''),
                    last_name=data['last_name'],
                    contact_num=data['contact_num'],
                    role=Roles.USER,
                )
                if account_type == 'student':
                    StudentProfile.objects.create(
                        user=user,
                        student_id=next_student_id(data['enrollment_year']),
                        program=data.get('program'),
                        major=data.get('major'),
                        year_level=data.get('year_level') or None,
                    )
                else:
                    StaffProfile.objects.create(
                        user=user,
                        staff_id=new_staff_id(data['campus']),
                        staff_type=data['staff_type'],
                        campus=data['campus'],
                    )
            break
        except IntegrityError:
            # Most likely another admin took the same ID a moment ago. Try again.
            if attempt == ID_RETRIES - 1:
                raise

    identifier = account_identifier(user)
    log_action(actor, user, ADDITION, f'Created {account_type} account {identifier}.')
    return user, password


@transaction.atomic
def update_account(*, actor, user, data):
    """Edit details. The account type and the ID never change."""
    ensure_manageable(actor, user)
    if user.is_deleted:
        raise AccountActionError('Restore this account before editing it.')

    email_changed = user.email != data['email']

    user.first_name = data['first_name']
    user.middle_name = data.get('middle_name', '')
    user.last_name = data['last_name']
    user.contact_num = data['contact_num']
    fields = ['first_name', 'middle_name', 'last_name', 'contact_num']
    if email_changed:
        user.email = data['email']
        user.email_verified = False        # the new address has not been verified yet
        fields += ['email', 'email_verified']
    user.save(update_fields=fields)

    student = getattr(user, 'student_profile', None)
    staff = getattr(user, 'staff_profile', None)
    if student:
        student.program = data.get('program')
        student.major = data.get('major')
        student.year_level = data.get('year_level') or None
        student.save(update_fields=['program', 'major', 'year_level'])
    elif staff:
        staff.campus = data['campus']
        staff.staff_type = data['staff_type']
        staff.save(update_fields=['campus', 'staff_type'])
        # staff_id ends with the campus code, so it must follow a campus change.
        new_code = data['campus'].campus_code.upper()
        if not staff.staff_id.endswith(f'-{new_code}'):
            number = staff.staff_id.split('-')[0]
            staff.staff_id = f'{number}-{new_code}'
            staff.save(update_fields=['staff_id'])

    log_action(actor, user, CHANGE, 'Edited account details.')
    return user


def account_identifier(user):
    student = getattr(user, 'student_profile', None)
    staff = getattr(user, 'staff_profile', None)
    if student:
        return student.student_id
    if staff:
        return staff.staff_id
    return ''


# --------------------------------------------------------------------------
# Status changes
# --------------------------------------------------------------------------

def suspend_account(*, actor, user, reason=''):
    ensure_manageable(actor, user)
    if user.is_deleted:
        raise AccountActionError('This account is deleted. Restore it first.')
    if not user.is_active:
        raise AccountActionError('This account is already suspended.')
    user.suspend()
    log_action(actor, user, CHANGE, _with_reason('Suspended account.', reason))
    return 'Account suspended.'


def reactivate_account(*, actor, user, reason=''):
    ensure_manageable(actor, user)
    if user.is_deleted:
        raise AccountActionError('This account is deleted. Restore it first.')
    if user.is_active:
        raise AccountActionError('This account is already active.')
    user.reactivate()
    log_action(actor, user, CHANGE, 'Reactivated account.')
    return 'Account reactivated.'


def delete_account(*, actor, user, reason=''):
    """Soft delete: hidden and unable to sign in, but every row is kept."""
    ensure_manageable(actor, user)
    if user.is_deleted:
        raise AccountActionError('This account is already deleted.')
    user.soft_delete()
    log_action(actor, user, DELETION, _with_reason('Deleted account (soft delete).', reason))
    return 'Account deleted. You can restore it any time.'


def restore_account(*, actor, user, reason=''):
    ensure_manageable(actor, user)
    if not user.is_deleted:
        raise AccountActionError('This account is not deleted.')
    user.restore()                          # comes back suspended, see User.restore()
    log_action(actor, user, CHANGE, 'Restored deleted account (returned as suspended).')
    return 'Account restored. It is suspended until you reactivate it.'


def reset_password(*, actor, user, reason=''):
    """Give the person a new temporary password. Returns (message, password)."""
    ensure_manageable(actor, user)
    if user.is_deleted or not user.is_active:
        raise AccountActionError('Only active accounts can have their password reset.')
    password = generate_temporary_password()
    user.set_password(password)
    user.is_first_login = True              # they must choose their own password on next sign-in
    user.save(update_fields=['password', 'is_first_login'])
    log_action(actor, user, CHANGE, 'Reset password (temporary password issued).')
    return 'Password reset.', password
