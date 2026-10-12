"""Reading accounts: filtering, counting and turning them into plain data.

The list screen uses these today. A future export can call filter_accounts()
with the same filters and write serialize_account() rows to a file, so what
the admin sees and what they export always match.
"""

from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Q

from apps.accounts.models import Campus, College, Roles, StaffType, YearLevel

User = get_user_model()

PAGE_SIZE = 15
STATUSES = ('active', 'suspended', 'deleted')
TYPES = ('student', 'staff', 'admin')

STATUS_LABELS = {'active': 'Active', 'suspended': 'Suspended', 'deleted': 'Deleted'}
TYPE_LABELS = {'student': 'Student', 'staff': 'Staff', 'admin': 'Admin'}


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def account_type(user):
    if user.is_admin:
        return 'admin'
    if getattr(user, 'student_profile', None):
        return 'student'
    if getattr(user, 'staff_profile', None):
        return 'staff'
    return 'student'          # a plain user with no profile; should not normally happen


def account_status(user):
    if user.is_deleted:
        return 'deleted'
    return 'active' if user.is_active else 'suspended'


def full_name(user):
    return ' '.join(p for p in (user.first_name, user.middle_name, user.last_name) if p)


# --------------------------------------------------------------------------
# Querying
# --------------------------------------------------------------------------

def accounts_queryset():
    return (
        User.objects
        .select_related(
            'student_profile__program__college',
            'student_profile__major',
            'staff_profile__campus',
        )
        .order_by('-date_joined', '-pk')
    )


def _apply_search_and_type(qs, q='', type_=''):
    # Every word must match something, so "juan 2026" narrows down step by step.
    for word in (q or '').split():
        qs = qs.filter(
            Q(first_name__icontains=word)
            | Q(middle_name__icontains=word)
            | Q(last_name__icontains=word)
            | Q(email__icontains=word)
            | Q(contact_num__icontains=word)
            | Q(student_profile__student_id__icontains=word)
            | Q(staff_profile__staff_id__icontains=word)
        )
    if type_ == 'student':
        qs = qs.filter(student_profile__isnull=False)
    elif type_ == 'staff':
        qs = qs.filter(staff_profile__isnull=False)
    elif type_ == 'admin':
        qs = qs.filter(Q(role=Roles.ADMIN) | Q(is_superuser=True))
    return qs


def _apply_status(qs, status):
    if status == 'active':
        return qs.filter(is_active=True, is_deleted=False)
    if status == 'suspended':
        return qs.filter(is_active=False, is_deleted=False)
    if status == 'deleted':
        return qs.filter(is_deleted=True)
    return qs


def filter_accounts(q='', type_='', status='active'):
    """The one place that decides which accounts match a set of filters."""
    qs = _apply_search_and_type(accounts_queryset(), q, type_)
    return _apply_status(qs, status)


def status_counts(q='', type_=''):
    """Numbers shown on the status tabs (they follow the search and type filter)."""
    qs = _apply_search_and_type(User.objects.all(), q, type_)
    return qs.aggregate(
        active=Count('pk', filter=Q(is_active=True, is_deleted=False)),
        suspended=Count('pk', filter=Q(is_active=False, is_deleted=False)),
        deleted=Count('pk', filter=Q(is_deleted=True)),
    )


def accounts_page(q='', type_='', status='active', page=1):
    if status not in STATUSES:
        status = 'active'
    if type_ not in TYPES:
        type_ = ''

    paginator = Paginator(filter_accounts(q, type_, status), PAGE_SIZE)
    page_obj = paginator.get_page(page)          # out-of-range pages fall back safely
    return {
        'results': [serialize_account(u) for u in page_obj.object_list],
        'page': page_obj.number,
        'num_pages': paginator.num_pages,
        'total': paginator.count,
        'start': page_obj.start_index() if paginator.count else 0,
        'end': page_obj.end_index() if paginator.count else 0,
        'counts': status_counts(q, type_),
    }


# --------------------------------------------------------------------------
# Turning accounts into plain data
# --------------------------------------------------------------------------

def serialize_account(user, actor=None, detail=False):
    kind = account_type(user)
    status = account_status(user)
    student = getattr(user, 'student_profile', None)
    staff = getattr(user, 'staff_profile', None)

    data = {
        'id': user.pk,
        'full_name': full_name(user),
        'email': user.email,
        'type': kind,
        'type_label': TYPE_LABELS[kind],
        'status': status,
        'status_label': STATUS_LABELS[status],
        'identifier': (student.student_id if student else staff.staff_id if staff else ''),
        'avatar_url': user.avatar_url,
        'date_joined': user.date_joined.isoformat(),
    }
    if not detail:
        return data

    data.update({
        'first_name': user.first_name,
        'middle_name': user.middle_name,
        'last_name': user.last_name,
        'contact_num': user.contact_num,
        'email_verified': user.email_verified,
        'deleted_at': user.deleted_at.isoformat() if user.deleted_at else None,
        # Admins (and yourself) are view-only on this page.
        'protected': user.is_admin or (actor is not None and user.pk == actor.pk),
        'student': None,
        'staff': None,
    })
    if student:
        program = student.program
        data['student'] = {
            'student_id': student.student_id,
            'college_id': program.college_id if program else None,
            'college': program.college.college_name if program else '',
            'program_id': student.program_id,
            'program': program.program_name if program else '',
            'major_id': student.major_id,
            'major': student.major.major_name if student.major else '',
            'year_level': student.year_level or '',
            'year_level_label': student.get_year_level_display() if student.year_level else '',
        }
    if staff:
        data['staff'] = {
            'staff_id': staff.staff_id,
            'campus_id': staff.campus_id,
            'campus': str(staff.campus),
            'staff_type': staff.staff_type,
            'staff_type_label': staff.get_staff_type_display(),
        }
    return data


def form_options():
    """Choices for the create/edit form (colleges > programs > majors, campuses...)."""
    from datetime import date

    colleges = College.objects.prefetch_related('programs__majors').order_by('college_name')
    return {
        'current_year': date.today().year,
        'colleges': [
            {
                'id': c.pk,
                'name': c.college_name,
                'programs': [
                    {
                        'id': p.pk,
                        'name': p.program_name,
                        'majors': [{'id': m.pk, 'name': m.major_name} for m in p.majors.all()],
                    }
                    for p in c.programs.all()
                ],
            }
            for c in colleges
        ],
        'campuses': [{'id': c.pk, 'name': str(c)} for c in Campus.objects.order_by('campus_code')],
        'year_levels': [{'value': v, 'label': l} for v, l in YearLevel.choices],
        'staff_types': [{'value': v, 'label': l} for v, l in StaffType.choices],
    }
