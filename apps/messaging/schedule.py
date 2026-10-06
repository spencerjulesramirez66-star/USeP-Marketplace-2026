"""Order schedule: calendar page, reschedule negotiation, delivery + stock.

Negotiation: seller proposes (SUBMITTED/CONFIRMED -> PROPOSED), the buyer accepts
(-> CONFIRMED with the new time) or counters (still PROPOSED, turn passes back).
Delivery: seller marks a CONFIRMED order delivered (-> COMPLETED) and stock drops.
"""
from datetime import time
from functools import wraps

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import MAX_SLOT_MINUTES, MIN_SLOT_MINUTES, schedule_hours
from .models import PurchaseRequest
from .services import respond_purchase, send_message

PR = PurchaseRequest.Status
LIVE = [PR.SUBMITTED, PR.CONFIRMED, PR.PROPOSED]
SHOWN = LIVE + [PR.COMPLETED]
FMT = ['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S']


class ProposalForm(forms.Form):
    start = forms.DateTimeField(input_formats=FMT, error_messages={'required': 'Pick a start time.', 'invalid': 'That start time is not valid.'})
    end = forms.DateTimeField(input_formats=FMT, error_messages={'required': 'Pick an end time.', 'invalid': 'That end time is not valid.'})
    note = forms.CharField(max_length=500, required=False)

    def clean(self):
        c = super().clean()
        s, e = c.get('start'), c.get('end')
        if not s or not e:
            return c
        ls, le = timezone.localtime(s), timezone.localtime(e)
        open_h, close_h = schedule_hours()
        minutes = (e - s).total_seconds() / 60
        if ls.date() != le.date():
            problem = 'A slot has to start and end on the same day.'
        elif minutes < MIN_SLOT_MINUTES:
            problem = f'Pick at least {MIN_SLOT_MINUTES} minutes.'
        elif minutes > MAX_SLOT_MINUTES:
            problem = f'Pick at most {MAX_SLOT_MINUTES // 60} hours.'
        elif ls.time() < time(open_h) or le.time() > time(close_h):
            problem = f'Choose a time between {open_h}:00 and {close_h}:00.'
        elif s < timezone.now():
            problem = 'That time has already passed.'
        else:
            return c
        raise forms.ValidationError(problem)


# ---------- services ----------

def _name(u):
    return f'{u.first_name} {u.last_name}'.strip() or u.email


def _lock(purchase_id):
    return PurchaseRequest.objects.select_for_update().select_related(
        'conversation__listing__seller', 'conversation__buyer').get(pk=purchase_id)


def _role(p, user):
    if user.id == p.conversation.listing.seller_id:
        return 'seller'
    if user.id == p.conversation.buyer_id:
        return 'buyer'
    raise PermissionDenied('This is not your order.')


def _taken(p, start, end):
    """Another live order of the same seller overlaps start..end (current or proposed slot)."""
    return PurchaseRequest.objects.filter(
        conversation__listing__seller_id=p.conversation.listing.seller_id, status__in=LIVE,
    ).exclude(pk=p.pk).filter(
        Q(scheduled_start__lt=end, scheduled_end__gt=start)
        | Q(status=PR.PROPOSED, proposed_start__lt=end, proposed_end__gt=start)
    ).exists()


def _origin(request):
    return request.build_absolute_uri('/').rstrip('/')


def _notify(p, sender, text, origin=''):
    """Chat message = notification (feeds the existing unread badge)."""
    link = f"{origin}{reverse('messaging:schedule')}?order={p.pk}"
    send_message(p.conversation, sender, body=f'{text}\nOpen the schedule: {link}')
    p.message.save(update_fields=['updated_at'])  # re-sends the purchase card on poll


def _when(dt):
    return timezone.localtime(dt).strftime('%a %b %d, %I:%M %p').replace(' 0', ' ')


@transaction.atomic
def propose_time(purchase_id, user, start, end, note='', origin=''):
    p = _lock(purchase_id)
    role = _role(p, user)
    opening = role == 'seller' and p.status in (PR.SUBMITTED, PR.CONFIRMED)
    countering = p.status == PR.PROPOSED and p.proposed_by_id != user.id
    if not (opening or countering):
        raise ValidationError('You cannot propose a new time for this order right now.')
    if _taken(p, start, end):
        raise ValidationError('That time overlaps another order. Pick a free slot.')
    p.status, p.proposed_start, p.proposed_end = PR.PROPOSED, start, end
    p.proposed_by, p.proposal_note = user, note
    p.save(update_fields=['status', 'proposed_start', 'proposed_end', 'proposed_by', 'proposal_note'])
    reason = f' Reason: {note}' if note else ''
    _notify(p, user, f'Schedule change for "{p.conversation.listing.title}": {_name(user)} suggests {_when(start)} to {timezone.localtime(end):%I:%M %p}.{reason} Please accept it or suggest another time.', origin)
    return p


@transaction.atomic
def accept_proposal(purchase_id, user, origin=''):
    p = _lock(purchase_id)
    _role(p, user)
    if p.status != PR.PROPOSED:
        raise ValidationError('There is no proposal to accept.')
    if p.proposed_by_id == user.id:
        raise ValidationError('Waiting for the other person to respond.')
    if _taken(p, p.proposed_start, p.proposed_end):
        raise ValidationError('That time was just taken. Propose another one.')
    p.scheduled_start, p.scheduled_end = p.proposed_start, p.proposed_end
    p.proposed_start = p.proposed_end = p.proposed_by = None
    p.proposal_note, p.status, p.responded_at = '', PR.CONFIRMED, timezone.now()
    p.save(update_fields=['scheduled_start', 'scheduled_end', 'proposed_start', 'proposed_end',
                          'proposed_by', 'proposal_note', 'status', 'responded_at'])
    _notify(p, user, f'Schedule agreed for "{p.conversation.listing.title}": {_when(p.scheduled_start)}.', origin)
    return p


@transaction.atomic
def complete_order(purchase_id, user, origin=''):
    """Seller confirms delivery by hand; this is the only place stock is subtracted."""
    p = _lock(purchase_id)
    if _role(p, user) != 'seller':
        raise PermissionDenied('Only the seller can confirm delivery.')
    if p.status != PR.CONFIRMED:
        raise ValidationError('Only a confirmed order can be marked delivered.')
    listing = p.conversation.listing
    if not p.is_service:
        Listing = type(listing)
        listing = Listing.objects.select_for_update().get(pk=listing.pk)
        if listing.stock_quantity < p.quantity:
            raise ValidationError(f'Only {listing.stock_quantity} in stock but this order needs {p.quantity}. Update your stock first.')
        left = listing.stock_quantity - p.quantity
        Listing.objects.filter(pk=listing.pk).update(
            stock_quantity=left,
            status=Listing.Status.SOLD if left == 0 else listing.status,
            updated_at=timezone.now(),
        )
    p.status, p.completed_at = PR.COMPLETED, timezone.now()
    p.save(update_fields=['status', 'completed_at'])
    _notify(p, user, f'Your order "{p.conversation.listing.title}" has been delivered. Thank you!', origin)
    return p


# ---------- views ----------

def api(view):
    @login_required
    @require_POST
    @wraps(view)
    def wrapper(request, *a, **kw):
        try:
            p = view(request, *a, **kw)
            return JsonResponse({'ok': True, 'event': event_payload(p, request.user)})
        except PermissionDenied as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=403)
        except ValidationError as e:
            return JsonResponse({'ok': False, 'error': ' '.join(e.messages)}, status=400)
        except PurchaseRequest.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Order not found.'}, status=404)
    return wrapper


def event_payload(p, user):
    c, listing = p.conversation, p.conversation.listing
    seller = user.id == listing.seller_id
    other = c.buyer if seller else listing.seller
    iso = lambda d: timezone.localtime(d).isoformat() if d else None
    my_turn = p.status == PR.PROPOSED and p.proposed_by_id != user.id
    return {
        'id': p.pk, 'title': listing.title, 'status': p.status, 'role': 'seller' if seller else 'buyer',
        'with': _name(other), 'start': iso(p.scheduled_start), 'end': iso(p.scheduled_end),
        'proposed_start': iso(p.proposed_start), 'proposed_end': iso(p.proposed_end),
        'proposal_note': p.proposal_note, 'buyer_note': p.buyer_note, 'quantity': p.quantity,
        'total': str(p.total_amount), 'payment': p.get_payment_method_display() if p.payment_method else '',
        'is_service': p.is_service, 'stock': listing.stock_quantity,
        'chat_url': reverse('messaging:conversation', args=[c.pk]),
        'can_propose': (seller and p.status in (PR.SUBMITTED, PR.CONFIRMED)) or my_turn,
        'can_accept': my_turn,
        'waiting': p.status == PR.PROPOSED and not my_turn,
        'can_deliver': seller and p.status == PR.CONFIRMED,
        'can_confirm': seller and p.status == PR.SUBMITTED,
    }


@login_required
def schedule_page(request):
    return render(request, 'seller/schedule.html', {
        'open_hour': schedule_hours()[0], 'close_hour': schedule_hours()[1],
        'focus_order': request.GET.get('order', ''),
    })


@login_required
def schedule_events(request):
    qs = PurchaseRequest.objects.filter(
        Q(conversation__listing__seller=request.user) | Q(conversation__buyer=request.user),
        status__in=SHOWN, scheduled_start__isnull=False,
    ).select_related('conversation__listing__seller', 'conversation__buyer')
    return JsonResponse({'events': [event_payload(p, request.user) for p in qs]})


@api
def schedule_propose(request, purchase_id):
    form = ProposalForm(request.POST)
    if not form.is_valid():
        raise ValidationError([m for errs in form.errors.values() for m in errs])
    d = form.cleaned_data
    return propose_time(purchase_id, request.user, d['start'], d['end'], d['note'], _origin(request))


@api
def schedule_accept(request, purchase_id):
    return accept_proposal(purchase_id, request.user, _origin(request))


@api
def schedule_deliver(request, purchase_id):
    return complete_order(purchase_id, request.user, _origin(request))


@api
def schedule_confirm(request, purchase_id):
    return respond_purchase(purchase_id, request.user, 'confirm')