import json

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.views import redirect_to_login
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET
from django.urls import reverse

from . import transaction_queries as queries
from .account_views import admin_json
from .csv_utils import stream_csv
from .permissions import is_marketplace_admin

User = get_user_model()


def _history_context(request):
    queryset, filters = queries.filter_transactions(request.GET)
    page_data = queries.transaction_page(queryset, filters)
    return {
        'section_title': 'Transactions',
        'section_eyebrow': 'OPERATIONS',
        'active_section': 'transactions',
        'transaction_tab': 'history',
        'transaction_filters': filters,
        'transaction_options': queries.filter_options(),
        'transaction_data': page_data,
    }


@require_GET
def transaction_history(request):
    if not is_marketplace_admin(request.user):
        return redirect_to_login(request.get_full_path())
    return render(
        request,
        'administration/dashboard.html',
        _history_context(request),
    )


@admin_json
@require_GET
def transaction_history_data(request):
    queryset, filters = queries.filter_transactions(request.GET)
    return JsonResponse(queries.transaction_page(queryset, filters))


@admin_json
@require_GET
def transaction_monitoring_data(request):
    try:
        data = queries.transaction_monitoring(
            request.GET,
            reverse('administration:transactions_history'),
        )
    except ValueError as error:
        return JsonResponse({'error': str(error)}, status=400)
    return JsonResponse(data)


@admin_json
@require_GET
def transaction_detail(request, purchase_id):
    purchase = get_object_or_404(
        queries.transaction_queryset(),
        pk=purchase_id,
    )
    data = queries.serialize_transaction(purchase)
    data.update({
        'payment_method': purchase.get_payment_method_display() if purchase.payment_method else '',
        'payment_reference': purchase.payment_reference,
        'payment_proof_uploaded': bool(purchase.payment_proof),
        'scheduled_start': queries.local_datetime_display(purchase.scheduled_start),
        'scheduled_end': queries.local_datetime_display(purchase.scheduled_end),
        'proposed_start': queries.local_datetime_display(purchase.proposed_start),
        'proposed_end': queries.local_datetime_display(purchase.proposed_end),
        'completed_at': queries.local_datetime_display(purchase.completed_at),
        'submitted_at': queries.local_datetime_display(purchase.submitted_at),
        'responded_at': queries.local_datetime_display(purchase.responded_at),
    })
    return JsonResponse({'transaction': data})


@admin_json
@require_GET
def transaction_export(request):
    queryset, filters = queries.filter_transactions(request.GET)
    row_count = queryset.count()
    content_type = ContentType.objects.get_for_model(User)
    LogEntry.objects.create(
        user=request.user,
        content_type=content_type,
        object_id=str(request.user.pk),
        object_repr=str(request.user)[:200],
        action_flag=CHANGE,
        change_message=(
            f'Exported transactions CSV | filters: {json.dumps(filters, sort_keys=True)} '
            f'| rows: {row_count}'
        ),
    )
    return stream_csv(queries.transaction_csv_rows(queryset), 'transactions.csv')
