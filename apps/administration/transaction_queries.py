from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from django.core.paginator import Paginator
from django.db.models import (
    Avg,
    CharField,
    Count,
    DateTimeField,
    ExpressionWrapper,
    F,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Cast, TruncDate
from django.utils import timezone

from apps.messaging.models import PurchaseRequest

ADMIN_TIMEZONE = ZoneInfo('Asia/Manila')
PAGE_SIZE = 25
TRANSACTION_QUERY_CEILING = 7
MONITORING_QUERY_CEILING = 19
STALLED_PENDING_HOURS = 48
STALLED_DELIVERY = PurchaseRequest.Status.CONFIRMED
HIGH_VALUE_THRESHOLD = Decimal('5000.00')
REPEAT_CANCELLER_THRESHOLD = 3
REPEAT_CANCELLER_DAYS = 30

TRANSACTION_STATUS_BUCKETS = {
    'pending': {
        'label': 'PENDING',
        'statuses': (
            PurchaseRequest.Status.REQUESTED,
            PurchaseRequest.Status.SUBMITTED,
        ),
    },
    'in_progress': {
        'label': 'IN PROGRESS',
        'statuses': (
            PurchaseRequest.Status.CONFIRMED,
            PurchaseRequest.Status.PROPOSED,
        ),
    },
    'completed': {
        'label': 'COMPLETED',
        'statuses': (PurchaseRequest.Status.COMPLETED,),
    },
    'closed_failed': {
        'label': 'CLOSED/FAILED',
        'statuses': (
            PurchaseRequest.Status.DECLINED,
            PurchaseRequest.Status.CANCELLED,
        ),
    },
}

SORT_OPTIONS = {
    'newest': ('-created_at', '-pk'),
    'oldest': ('created_at', 'pk'),
    'highest_amount': ('-total_amount', '-created_at', '-pk'),
    'lowest_amount': ('total_amount', 'created_at', 'pk'),
}


def monitoring_period(params, today=None):
    today = today or timezone.localdate(timezone=ADMIN_TIMEZONE)
    period = params.get('range', '7d')
    if period == 'today':
        start = end = today
    elif period == '30d':
        start, end = today - timedelta(days=29), today
    elif period == 'this_month':
        start, end = today.replace(day=1), today
    elif period == 'custom':
        start = _parse_day(params.get('date_from'))
        end = _parse_day(params.get('date_to'))
        if not start or not end or start > end:
            raise ValueError('Choose a valid custom start and end date.')
    else:
        period = '7d'
        start, end = today - timedelta(days=6), today
    return {
        'range': period,
        'start': start,
        'end': end,
        'previous_start': start - (end - start + timedelta(days=1)),
        'previous_end': start - timedelta(days=1),
    }


def _range_filter(field, start, end):
    return {
        f'{field}__gte': local_day_boundary(start),
        f'{field}__lt': local_day_boundary(end + timedelta(days=1)),
    }


def _percent_delta(current, previous):
    current = current or 0
    previous = previous or 0
    return {
        'current': str(current) if isinstance(current, Decimal) else current,
        'previous': str(previous) if isinstance(previous, Decimal) else previous,
        'change': str(current - previous) if isinstance(current, Decimal) else current - previous,
        'percent': round((float(current - previous) / float(previous)) * 100, 1) if previous else None,
    }


def _monitoring_kpis(start, end):
    created_range = Q(**_range_filter('created_at', start, end))
    completed_range = Q(**_range_filter('completed_at', start, end))
    bucket_conditions = {
        key: Q(status__in=value['statuses'])
        for key, value in TRANSACTION_STATUS_BUCKETS.items()
    }
    return PurchaseRequest.objects.aggregate(
        total=Count('pk', filter=created_range),
        pending=Count('pk', filter=created_range & bucket_conditions['pending']),
        in_progress=Count('pk', filter=created_range & bucket_conditions['in_progress']),
        closed_failed=Count('pk', filter=created_range & bucket_conditions['closed_failed']),
        completed_count=Count(
            'pk',
            filter=completed_range & bucket_conditions['completed'],
        ),
        completed_value=Sum(
            'total_amount',
            filter=completed_range & bucket_conditions['completed'],
        ),
        average_value=Avg('total_amount', filter=created_range),
    )


def _monitoring_attention(now):
    pending_cutoff = now - timedelta(hours=STALLED_PENDING_HOURS)
    pending = transaction_queryset().filter(
        status__in=TRANSACTION_STATUS_BUCKETS['pending']['statuses'],
        created_at__lt=pending_cutoff,
    )
    delivery = transaction_queryset().filter(
        status=STALLED_DELIVERY,
        scheduled_end__lt=now,
        completed_at__isnull=True,
    )
    high_value = transaction_queryset().filter(total_amount__gte=HIGH_VALUE_THRESHOLD)

    cancel_cutoff = now - timedelta(days=REPEAT_CANCELLER_DAYS)
    qualified_buyers = (
        PurchaseRequest.objects.filter(
            status=PurchaseRequest.Status.CANCELLED,
            responded_at__gte=cancel_cutoff,
            responded_at__lte=now,
        )
        .values('conversation__buyer_id')
        .annotate(cancel_count=Count('pk'))
        .filter(cancel_count__gte=REPEAT_CANCELLER_THRESHOLD)
    )
    latest_cancellation = (
        PurchaseRequest.objects.filter(
            status=PurchaseRequest.Status.CANCELLED,
            responded_at__gte=cancel_cutoff,
            responded_at__lte=now,
            conversation__buyer_id=OuterRef('conversation__buyer_id'),
        )
        .order_by('-responded_at', '-pk')
        .values('pk')[:1]
    )
    repeat_buyers = qualified_buyers.annotate(
        latest_request_id=Subquery(latest_cancellation),
    )
    repeat_rows = transaction_queryset().filter(
        pk__in=Subquery(repeat_buyers.values('latest_request_id')),
    )
    rule_data = (
        ('stalled_pending', 'Stalled pending', pending, pending.count(),
         'status=pending'),
        ('stalled_delivery', 'Stalled delivery', delivery, delivery.count(),
         'status=in_progress'),
        ('high_value', 'High value', high_value, high_value.count(),
         f'amount_min={HIGH_VALUE_THRESHOLD}'),
    )
    items = []
    counts = {}
    for rule, label, queryset, count, history_query in rule_data:
        counts[rule] = count
        for purchase in queryset.order_by('created_at', 'pk')[:10]:
            items.append((purchase.created_at, rule, label, purchase, count, history_query))

    counts['repeat_canceller'] = repeat_buyers.count()
    for purchase in repeat_rows.order_by('-responded_at', '-pk')[:10]:
        items.append((
            purchase.responded_at,
            'repeat_canceller',
            'Repeat canceller',
            purchase,
            counts['repeat_canceller'],
            'status=cancelled',
        ))

    return counts, sorted(items, key=lambda item: item[0] or now, reverse=True)[:10]


def transaction_monitoring(params, history_url):
    period = monitoring_period(params)
    start, end = period['start'], period['end']
    previous_start, previous_end = period['previous_start'], period['previous_end']
    current = _monitoring_kpis(start, end)
    previous = _monitoring_kpis(previous_start, previous_end)

    series = (
        PurchaseRequest.objects.filter(**_range_filter('created_at', start, end))
        .annotate(
            manila_created_at=ExpressionWrapper(
                F('created_at') + Value(ADMIN_TIMEZONE.utcoffset(timezone.now())),
                output_field=DateTimeField(),
            ),
        )
        .annotate(day=TruncDate('manila_created_at'))
        .values('day')
        .annotate(**{
            key: Count('pk', filter=Q(status__in=value['statuses']))
            for key, value in TRANSACTION_STATUS_BUCKETS.items()
        })
        .order_by('day')
    )
    status_breakdown = (
        PurchaseRequest.objects.filter(**_range_filter('created_at', start, end))
        .values('status')
        .annotate(count=Count('pk'))
        .order_by('-count', 'status')
    )
    completed_period = _range_filter('completed_at', start, end)
    sellers = (
        PurchaseRequest.objects.filter(
            status=PurchaseRequest.Status.COMPLETED,
            **completed_period,
        )
        .values(
            'conversation__seller_id',
            'conversation__seller__first_name',
            'conversation__seller__middle_name',
            'conversation__seller__last_name',
            'conversation__seller__email',
        )
        .annotate(value=Sum('total_amount'))
        .order_by('-value', 'conversation__seller_id')[:5]
    )
    categories = (
        PurchaseRequest.objects.filter(**_range_filter('created_at', start, end))
        .values('conversation__listing__category_id', 'conversation__listing__category__name')
        .annotate(count=Count('pk'))
        .order_by('-count', 'conversation__listing__category__name')[:5]
    )
    attention_counts, attention_items = _monitoring_attention(timezone.now())
    latest = transaction_queryset().order_by('-created_at', '-pk')[:10]

    total = current['total']
    completed_count = current['completed_count']
    completed_value = current['completed_value'] or Decimal('0.00')
    average_value = current['average_value'] or Decimal('0.00')
    prior_completed_value = previous['completed_value'] or Decimal('0.00')
    prior_average_value = previous['average_value'] or Decimal('0.00')
    prior_rate = (
        previous['completed_count'] / previous['total'] * 100
        if previous['total'] else 0
    )
    current_rate = completed_count / total * 100 if total else 0

    encoded_links = {
        'stalled_pending': 'status=pending',
        'stalled_delivery': 'status=in_progress',
        'high_value': f'amount_min={HIGH_VALUE_THRESHOLD}',
        'repeat_canceller': 'status=cancelled',
    }
    return {
        'period': {
            'range': period['range'],
            'start': start.isoformat(),
            'end': end.isoformat(),
            'label': f'{start.strftime("%b")} {start.day} – {end.strftime("%b")} {end.day}, {end.year} PHT',
        },
        'last_updated': local_datetime_display(timezone.now()),
        'kpis': {
            'total': total,
            'pending': current['pending'],
            'in_progress': current['in_progress'],
            'completed_count': completed_count,
            'completed_value': str(completed_value),
            'completed_value_display': format_money_value(completed_value),
            'closed_failed': current['closed_failed'],
            'average_value': str(average_value),
            'average_value_display': format_money_value(average_value),
            'completion_rate': round(current_rate, 1),
            'deltas': {
                'total': _percent_delta(total, previous['total']),
                'pending': _percent_delta(current['pending'], previous['pending']),
                'in_progress': _percent_delta(current['in_progress'], previous['in_progress']),
                'completed_count': _percent_delta(completed_count, previous['completed_count']),
                'completed_value': _percent_delta(completed_value, prior_completed_value),
                'closed_failed': _percent_delta(current['closed_failed'], previous['closed_failed']),
                'average_value': _percent_delta(average_value, prior_average_value),
                'completion_rate': _percent_delta(current_rate, prior_rate),
            },
        },
        'daily_series': list(series),
        'status_breakdown': [
            {
                'status': row['status'],
                'label': PurchaseRequest.Status(row['status']).label,
                'bucket': status_bucket(row['status']),
                'count': row['count'],
            }
            for row in status_breakdown
        ],
        'top_sellers': [
            {
                'id': row['conversation__seller_id'],
                'name': ' '.join(part for part in (
                    row['conversation__seller__first_name'],
                    row['conversation__seller__middle_name'],
                    row['conversation__seller__last_name'],
                ) if part).strip() or row['conversation__seller__email'],
                'value': str(row['value']),
                'value_display': format_money_value(row['value']),
            }
            for row in sellers
        ],
        'top_categories': [
            {
                'id': row['conversation__listing__category_id'],
                'name': row['conversation__listing__category__name'],
                'count': row['count'],
            }
            for row in categories
        ],
        'attention_counts': attention_counts,
        'attention_items': [
            {
                'rule': rule,
                'rule_label': label,
                'count': count,
                'transaction': serialize_transaction(purchase),
                'history_url': f'{history_url}?{history_query}',
            }
            for _, rule, label, purchase, count, history_query in attention_items
        ],
        'latest_transactions': [serialize_transaction(purchase) for purchase in latest],
        'stock_note': (
            'Stock decreases when product delivery is confirmed as complete; '
            'it does not decrease when a request is created or accepted.'
        ),
        'cancellation_note': 'Cancellation party is not recorded.',
    }


def status_bucket(status):
    for bucket, values in TRANSACTION_STATUS_BUCKETS.items():
        if status in values['statuses']:
            return bucket
    return ''


def status_bucket_label(status):
    bucket = status_bucket(status)
    return TRANSACTION_STATUS_BUCKETS[bucket]['label'] if bucket else 'Unknown'


def local_day_boundary(day):
    return timezone.make_aware(datetime.combine(day, time.min), ADMIN_TIMEZONE)


def local_day(value):
    return timezone.localtime(value, ADMIN_TIMEZONE).date() if value else None


def _parse_day(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _parse_amount(value):
    try:
        amount = Decimal(value)
        return amount if amount.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def transaction_queryset():
    return PurchaseRequest.objects.select_related(
        'conversation__buyer',
        'conversation__seller',
        'conversation__listing__category',
    )


def normalized_filters(params):
    status = params.get('status', '').strip()
    valid_statuses = {value for value, _ in PurchaseRequest.Status.choices}
    if status not in valid_statuses and status not in TRANSACTION_STATUS_BUCKETS:
        status = ''

    kind = params.get('type', '').strip()
    if kind not in {'product', 'service'}:
        kind = ''

    sort = params.get('sort', 'newest').strip()
    if sort not in SORT_OPTIONS:
        sort = 'newest'

    category = params.get('category', '').strip()
    seller = params.get('seller', '').strip()
    payment_method = params.get('payment_method', '').strip()
    valid_payment_methods = {value for value, _ in PurchaseRequest.PaymentMethod.choices}
    if payment_method not in valid_payment_methods:
        payment_method = ''

    return {
        'q': params.get('q', '').strip()[:200],
        'status': status,
        'type': kind,
        'category': category if category.isdigit() else '',
        'seller': seller if seller.isdigit() else '',
        'payment_method': payment_method,
        'date_from': params.get('date_from', '').strip(),
        'date_to': params.get('date_to', '').strip(),
        'amount_min': params.get('amount_min', '').strip(),
        'amount_max': params.get('amount_max', '').strip(),
        'sort': sort,
        'page': params.get('page', '1'),
    }


def filter_transactions(params):
    filters = normalized_filters(params)
    queryset = transaction_queryset()

    search_words = filters['q'].split()
    if search_words:
        queryset = queryset.annotate(search_id=Cast('pk', output_field=CharField()))

    for word in search_words:
        queryset = queryset.filter(
            Q(search_id__icontains=word)
            | Q(conversation__listing__title__icontains=word)
            | Q(conversation__buyer__first_name__icontains=word)
            | Q(conversation__buyer__middle_name__icontains=word)
            | Q(conversation__buyer__last_name__icontains=word)
            | Q(conversation__buyer__email__icontains=word)
            | Q(conversation__seller__first_name__icontains=word)
            | Q(conversation__seller__middle_name__icontains=word)
            | Q(conversation__seller__last_name__icontains=word)
            | Q(conversation__seller__email__icontains=word)
        )

    if filters['status'] in TRANSACTION_STATUS_BUCKETS:
        queryset = queryset.filter(status__in=TRANSACTION_STATUS_BUCKETS[filters['status']]['statuses'])
    elif filters['status']:
        queryset = queryset.filter(status=filters['status'])

    if filters['type'] == 'product':
        queryset = queryset.filter(is_service=False)
    elif filters['type'] == 'service':
        queryset = queryset.filter(is_service=True)

    if filters['category']:
        queryset = queryset.filter(conversation__listing__category_id=filters['category'])
    if filters['seller']:
        queryset = queryset.filter(conversation__seller_id=filters['seller'])
    if filters['payment_method']:
        queryset = queryset.filter(payment_method=filters['payment_method'])

    date_from = _parse_day(filters['date_from'])
    date_to = _parse_day(filters['date_to'])
    if date_from:
        queryset = queryset.filter(created_at__gte=local_day_boundary(date_from))
    if date_to:
        queryset = queryset.filter(created_at__lt=local_day_boundary(date_to + timedelta(days=1)))

    amount_min = _parse_amount(filters['amount_min'])
    amount_max = _parse_amount(filters['amount_max'])
    if amount_min is not None:
        queryset = queryset.filter(total_amount__gte=amount_min)
    if amount_max is not None:
        queryset = queryset.filter(total_amount__lte=amount_max)

    return queryset.order_by(*SORT_OPTIONS[filters['sort']]), filters


def transaction_page(queryset, filters):
    paginator = Paginator(queryset, PAGE_SIZE)
    page_obj = paginator.get_page(filters['page'])
    summary = queryset.aggregate(
        value=Sum('total_amount'),
    )
    return {
        'results': [serialize_transaction(item) for item in page_obj.object_list],
        'page': page_obj.number,
        'num_pages': paginator.num_pages,
        'total': paginator.count,
        'start': page_obj.start_index() if paginator.count else 0,
        'end': page_obj.end_index() if paginator.count else 0,
        'filtered_value': str(summary['value'] or Decimal('0.00')),
        'filtered_value_display': format_money_value(summary['value']),
        'filters': filters,
    }


def format_money_value(value):
    from .formatters import format_money

    return format_money(value)


def _person_name(user):
    return ' '.join(part for part in (user.first_name, user.middle_name, user.last_name) if part).strip() or user.email


def serialize_transaction(purchase):
    conversation = purchase.conversation
    listing = conversation.listing
    return {
        'id': purchase.pk,
        'display_id': f'#{purchase.pk:04d}',
        'created_at': purchase.created_at.isoformat(),
        'created_at_local': local_datetime_iso(purchase.created_at),
        'created_display': local_datetime_display(purchase.created_at),
        'status': purchase.status,
        'status_label': purchase.get_status_display(),
        'status_bucket': status_bucket(purchase.status),
        'status_bucket_label': status_bucket_label(purchase.status),
        'type': 'Service' if purchase.is_service else 'Product',
        'listing_id': listing.pk,
        'listing_title': listing.title,
        'listing_url': listing.get_absolute_url() if listing.lifecycle_state == listing.Lifecycle.NORMAL else '',
        'category': listing.category.name,
        'buyer_name': _person_name(conversation.buyer),
        'buyer_email': conversation.buyer.email,
        'buyer_account_status': account_status(conversation.buyer),
        'seller_name': _person_name(conversation.seller),
        'seller_email': conversation.seller.email,
        'seller_account_status': account_status(conversation.seller),
        'quantity': purchase.quantity,
        'unit_price': str(purchase.unit_price),
        'unit_price_display': format_money_value(purchase.unit_price),
        'total': str(purchase.total_amount),
        'total_display': format_money_value(purchase.total_amount),
    }


def account_status(user):
    if user.is_deleted:
        return 'Deleted'
    if not user.is_active:
        return 'Inactive'
    return 'Active'


def filter_options():
    category_values = transaction_queryset().values_list(
        'conversation__listing__category_id',
        'conversation__listing__category__name',
    ).distinct().order_by('conversation__listing__category__name')
    seller_values = transaction_queryset().values_list(
        'conversation__seller_id',
        'conversation__seller__first_name',
        'conversation__seller__middle_name',
        'conversation__seller__last_name',
        'conversation__seller__email',
    ).distinct().order_by('conversation__seller__first_name', 'conversation__seller__last_name')
    return {
        'categories': [{'id': item[0], 'name': item[1]} for item in category_values],
        'sellers': [
            {
                'id': item[0],
                'name': ' '.join(part for part in item[1:4] if part).strip() or item[4],
            }
            for item in seller_values
        ],
        'status_buckets': TRANSACTION_STATUS_BUCKETS,
        'statuses': PurchaseRequest.Status.choices,
        'types': (('product', 'Product'), ('service', 'Service')),
        'payment_methods': PurchaseRequest.PaymentMethod.choices,
        'sort_options': (
            ('newest', 'Newest'),
            ('oldest', 'Oldest'),
            ('highest_amount', 'Highest amount'),
            ('lowest_amount', 'Lowest amount'),
        ),
    }


def local_datetime_iso(value):
    from .formatters import local_datetime_iso as format_local_datetime

    return format_local_datetime(value)


def local_datetime_display(value):
    from .formatters import local_datetime_display as format_local_datetime

    return format_local_datetime(value)


def transaction_csv_rows(queryset):
    headers = (
        'Transaction ID',
        'Created',
        'Status',
        'Status group',
        'Type',
        'Listing ID',
        'Listing title',
        'Category',
        'Buyer name',
        'Buyer email',
        'Seller name',
        'Seller email',
        'Quantity',
        'Unit price',
        'Total',
        'Payment method',
        'Payment reference',
        'Payment proof uploaded',
        'Scheduled start',
        'Scheduled end',
        'Proposed start',
        'Proposed end',
        'Completed at',
        'Submitted at',
        'Responded at',
    )
    yield headers
    for purchase in queryset.iterator(chunk_size=2000):
        conversation = purchase.conversation
        listing = conversation.listing
        yield (
            purchase.pk,
            local_datetime_iso(purchase.created_at),
            purchase.get_status_display(),
            status_bucket_label(purchase.status),
            'Service' if purchase.is_service else 'Product',
            listing.pk,
            listing.title,
            listing.category.name,
            _person_name(conversation.buyer),
            conversation.buyer.email,
            _person_name(conversation.seller),
            conversation.seller.email,
            purchase.quantity,
            str(purchase.unit_price),
            str(purchase.total_amount),
            purchase.get_payment_method_display() if purchase.payment_method else '',
            purchase.payment_reference,
            'Yes' if purchase.payment_proof else 'No',
            local_datetime_iso(purchase.scheduled_start),
            local_datetime_iso(purchase.scheduled_end),
            local_datetime_iso(purchase.proposed_start),
            local_datetime_iso(purchase.proposed_end),
            local_datetime_iso(purchase.completed_at),
            local_datetime_iso(purchase.submitted_at),
            local_datetime_iso(purchase.responded_at),
        )
