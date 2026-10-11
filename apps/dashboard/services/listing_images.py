"""Listing gallery updates shared by create, edit, and delete-image views."""

from apps.dashboard.models import ListingImage


def save_listing_images(listing, uploaded_images):
    for image in uploaded_images:
        if not listing.image:
            listing.image = image
            listing.save(update_fields=['image', 'updated_at'])
        ListingImage.objects.create(listing=listing, image=image)


def remove_listing_images(listing, image_ids):
    images = list(ListingImage.objects.filter(listing=listing, id__in=image_ids))
    if not images:
        return

    primary_names = {image.image.name for image in images}
    ListingImage.objects.filter(id__in=[image.id for image in images]).delete()
    if listing.image and listing.image.name in primary_names:
        replacement = listing.listing_images.first()
        listing.image = replacement.image if replacement else None
        listing.save(update_fields=['image', 'updated_at'])
    elif not listing.listing_images.exists() and not listing.image_urls and listing.image:
        listing.image = None
        listing.save(update_fields=['image', 'updated_at'])
