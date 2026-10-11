"""Server-side state transitions for listings in the Recycle Bin."""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.dashboard.models import Listing


RESTORED = 'restored'
EXPIRED = 'expired'
UNAVAILABLE = 'unavailable'


def recycle_bin_retention_days():
    """Return the configured duration, retaining the legacy disabled setting."""
    days = settings.LISTING_RECYCLE_BIN_RETENTION_DAYS
    return days if days and days > 0 else None


def recycle_bin_deadline(recycled_at):
    days = recycle_bin_retention_days()
    if not recycled_at or not days:
        return None
    return recycled_at + timedelta(days=days)


def is_recycle_bin_expired(listing, now=None):
    deadline = recycle_bin_deadline(listing.recycled_at)
    return deadline is not None and (now or timezone.now()) >= deadline


def eligible_recycle_bin_listings(queryset, now=None):
    """Keep listings at or past their deadline out of seller-facing results."""
    days = recycle_bin_retention_days()
    if not days:
        return queryset
    cutoff = (now or timezone.now()) - timedelta(days=days)
    return queryset.filter(recycled_at__gt=cutoff)


def move_to_recycle_bin(listing, now=None):
    now = now or timezone.now()
    listing.lifecycle_state = Listing.Lifecycle.RECYCLE_BIN
    listing.recycled_at = now
    listing.recycle_bin_expires_at = recycle_bin_deadline(now)
    listing.archived_at = None
    listing.save(update_fields=[
        'lifecycle_state', 'recycled_at', 'recycle_bin_expires_at', 'archived_at', 'updated_at',
    ])


@transaction.atomic
def restore_recycled_listing(listing_id, seller, now=None):
    """Restore only a still-eligible listing, locking against archive processing."""
    now = now or timezone.now()
    listing = Listing.objects.select_for_update().filter(
        pk=listing_id,
        seller=seller,
        lifecycle_state=Listing.Lifecycle.RECYCLE_BIN,
    ).first()
    if listing is None:
        return UNAVAILABLE

    if is_recycle_bin_expired(listing, now):
        Listing.objects.filter(
            pk=listing.pk,
            lifecycle_state=Listing.Lifecycle.RECYCLE_BIN,
        ).update(
            lifecycle_state=Listing.Lifecycle.ARCHIVED,
            archived_at=now,
            updated_at=now,
        )
        return EXPIRED

    listing.lifecycle_state = Listing.Lifecycle.NORMAL
    listing.recycled_at = None
    listing.recycle_bin_expires_at = None
    listing.archived_at = None
    listing.save(update_fields=[
        'lifecycle_state', 'recycled_at', 'recycle_bin_expires_at', 'archived_at', 'updated_at',
    ])
    return RESTORED


@transaction.atomic
def archive_expired_recycled_listings(now=None):
    """Archive only listings that have completed the configured recycle period."""
    days = recycle_bin_retention_days()
    if not days:
        return 0

    now = now or timezone.now()
    cutoff = now - timedelta(days=days)
    return Listing.objects.filter(
        lifecycle_state=Listing.Lifecycle.RECYCLE_BIN,
        recycled_at__lte=cutoff,
    ).update(
        lifecycle_state=Listing.Lifecycle.ARCHIVED,
        archived_at=now,
        updated_at=now,
    )
