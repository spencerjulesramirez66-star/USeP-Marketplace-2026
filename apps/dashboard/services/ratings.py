"""Rating aggregates shared by storefront and listing-detail views."""

from django.db.models import Avg, Count

from apps.dashboard.models import Listing, ListingReview, rating_star_states


def seller_reputation(seller):
    summary = ListingReview.objects.filter(
        listing__seller=seller,
    ).exclude(listing__status=Listing.Status.DRAFT).aggregate(
        average=Avg('rating'),
        total=Count('id'),
    )
    return {
        'reputation_average': summary['average'],
        'reputation_count': summary['total'],
        'reputation_star_states': rating_star_states(summary['average']),
    }
