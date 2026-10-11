"""JSON endpoints used by the Accounts page (static/administration/js/admin-accounts.js).

They only check permission, read the request and call account_queries /
account_services. The rules themselves live in those two files.
"""

from functools import wraps

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from . import account_services as services
from .account_forms import AccountForm
from .account_queries import accounts_page, accounts_queryset, serialize_account
from .permissions import is_marketplace_admin

User = get_user_model()

# url name -> (service function, reason required?)
STATUS_ACTIONS = {
    'suspend': (services.suspend_account, True),
    'reactivate': (services.reactivate_account, False),
    'delete': (services.delete_account, True),
    'restore': (services.restore_account, False),
}


def admin_json(view):
    """Like user_passes_test, but answers with JSON instead of redirecting to a login page."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Your session expired. Please sign in again.'}, status=401)
        if not is_marketplace_admin(request.user):
            return JsonResponse({'error': "You don't have permission to do this."}, status=403)
        return view(request, *args, **kwargs)
    return wrapper


def _error(message, status=400, errors=None):
    return JsonResponse({'error': message, 'errors': errors or {}}, status=status)


def _form_errors(form):
    return {field: list(messages) for field, messages in form.errors.items()}


def _get_account(user_id):
    return accounts_queryset().filter(pk=user_id).first()


def _detail(request, user_id):
    """Re-read the account so the screen always gets fresh data."""
    return serialize_account(_get_account(user_id), actor=request.user, detail=True)


# --------------------------------------------------------------------------

@admin_json
@require_GET
def accounts_data(request):
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1
    data = accounts_page(
        q=request.GET.get('q', '').strip(),
        type_=request.GET.get('type', ''),
        status=request.GET.get('status', 'active'),
        page=page,
    )
    return JsonResponse(data)


@admin_json
@require_GET
def account_detail(request, user_id):
    if not _get_account(user_id):
        return _error('Account not found.', 404)
    return JsonResponse({'account': _detail(request, user_id)})


@admin_json
@require_POST
def account_create(request):
    form = AccountForm(request.POST)
    if not form.is_valid():
        return _error('Please fix the highlighted fields.', errors=_form_errors(form))

    try:
        user, password = services.create_account(actor=request.user, data=form.cleaned_data)
    except services.AccountActionError as exc:
        return _error(str(exc))

    return JsonResponse({
        'message': 'Account created.',
        'account': _detail(request, user.pk),
        'temporary_password': password,
    }, status=201)


@admin_json
@require_POST
def account_update(request, user_id):
    user = _get_account(user_id)
    if not user:
        return _error('Account not found.', 404)

    form = AccountForm(request.POST, instance=user)
    if not form.is_valid():
        return _error('Please fix the highlighted fields.', errors=_form_errors(form))

    try:
        services.update_account(actor=request.user, user=user, data=form.cleaned_data)
    except services.AccountActionError as exc:
        return _error(str(exc), 409)

    return JsonResponse({'message': 'Changes saved.', 'account': _detail(request, user_id)})


@admin_json
@require_POST
def account_action(request, user_id, action):
    """suspend / reactivate / delete / restore / reset-password"""
    user = _get_account(user_id)
    if not user:
        return _error('Account not found.', 404)

    reason = request.POST.get('reason', '').strip()[:500]
    password = None

    try:
        if action == 'reset-password':
            message, password = services.reset_password(actor=request.user, user=user)
        elif action in STATUS_ACTIONS:
            func, needs_reason = STATUS_ACTIONS[action]
            if needs_reason and not reason:
                return _error('Please give a short reason.', errors={'reason': ['Please give a short reason.']})
            message = func(actor=request.user, user=user, reason=reason)
        else:
            return _error('Unknown action.', 404)
    except services.AccountActionError as exc:
        return _error(str(exc), 409)

    payload = {'message': message, 'account': _detail(request, user_id)}
    if password:
        payload['temporary_password'] = password
    return JsonResponse(payload)
