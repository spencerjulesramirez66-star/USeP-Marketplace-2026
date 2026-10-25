import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Exists, OuterRef, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.accounts.models import User

from .forms import (
    CONDITION_CHOICES,
    MAX_REVIEW_PHOTOS,
    PRODUCT_CONDITIONS,
    SERVICE_CONDITIONS,
    ListingForm,
    ListingReviewForm,
    ListingReviewReplyForm,
    validate_listing_images,
)
from .models import (
    Category,
    Listing,
    ListingImage,
    ListingReview,
    ListingReviewPhoto,
    ListingReviewReply,
    ReviewNotification,
    SavedItem,
)
from .services.listing_images import remove_listing_images, save_listing_images
from .services.listing_lifecycle import (
    EXPIRED,
    RESTORED,
    eligible_recycle_bin_listings,
    move_to_recycle_bin,
    restore_recycled_listing,
)
from .services.ratings import seller_reputation

RECOMMENDATION_WEIGHTS = {
    'popularity': 0.5,
    'recency': 0.2,
    'affinity': 0.3,
}
REVIEW_DISPLAY_LIMIT = 10
REPUTATION_PAGE_SIZE = 10
logger = logging.getLogger(__name__)


def _condition_options():
    return (
        [{'value': condition, 'type': 'product'} for condition in PRODUCT_CONDITIONS]
        + [{'value': condition, 'type': 'service'} for condition in SERVICE_CONDITIONS]
    )


def _category_context():
    categories = Category.objects.all()
    category_context = [{
        'id': None,
        'label': 'All',
        'slug': 'all',
        'count': Listing.objects.filter(
            status=Listing.Status.ACTIVE,
            lifecycle_state=Listing.Lifecycle.NORMAL,
        ).count(),
    }]
    category_context.extend([
        {
            'id': category.id,
            'label': category.name,
            'slug': category.slug,
            'count': Listing.objects.filter(
                category=category,
                status=Listing.Status.ACTIVE,
                lifecycle_state=Listing.Lifecycle.NORMAL,
            ).count(),
        }
        for category in categories
    ])
    return category_context


def _seller_profile(user):
    role = 'Marketplace seller'
    program = ''
    campus = ''
    if hasattr(user, 'staff_profile'):
        role = user.staff_profile.get_staff_type_display()
        campus = str(user.staff_profile.campus)
    elif hasattr(user, 'student_profile'):
        role = 'Student seller'
        student_profile = user.student_profile
        program = str(student_profile.program or student_profile.major.program)
    return {
        'id': user.pk,
        'name': f'{user.first_name} {user.last_name}'.strip() or user.email,
        'role': role,
        'avatar': user.profile_picture.url if user.profile_picture else '',
        'email': user.email,
        'contact': user.contact_num,
        'program': program,
        'campus': campus,
        **seller_reputation(user),
    }


@login_required
def setup_seller_dashboard(request):
    listing_view = request.GET.get('view', 'listings')
    if listing_view == 'archived':
        raise Http404('Archived listings are only available to administrators.')
    all_listings = Listing.objects.filter(seller=request.user).select_related('category')
    lifecycle_state = {
        'recycle': Listing.Lifecycle.RECYCLE_BIN,
    }.get(listing_view, Listing.Lifecycle.NORMAL)
    if lifecycle_state == Listing.Lifecycle.NORMAL:
        listing_view = 'listings'
    listings = all_listings.filter(lifecycle_state=lifecycle_state)
    if listing_view == 'recycle':
        listings = eligible_recycle_bin_listings(listings)
    active_listings = all_listings.filter(
        status=Listing.Status.ACTIVE,
        lifecycle_state=Listing.Lifecycle.NORMAL,
    )
    context = {
        'listings': listings,
        'listing_form': ListingForm(),
        'categories': _category_context(),
        'condition_choices': [value for value, _ in CONDITION_CHOICES],
        'condition_options': _condition_options(),
        'active_count': active_listings.count(),
        'total_views': sum(listing.views for listing in all_listings),
        'sold_count': all_listings.filter(status=Listing.Status.SOLD).count(),
        'manage_listing_id': request.GET.get('manage'),
        'listing_view': listing_view,
        'recycle_bin_count': eligible_recycle_bin_listings(
            all_listings.filter(lifecycle_state=Listing.Lifecycle.RECYCLE_BIN),
        ).count(),
    }
    return render(request, 'seller/dashboard.html', context)


@login_required
def seller_reputation_page(request):
    listings = Listing.objects.filter(seller=request.user).select_related('category')
    seller_reply = ListingReviewReply.objects.filter(
        review_id=OuterRef('pk'),
        author_id=OuterRef('listing__seller_id'),
    )
    all_reviews = ListingReview.objects.filter(
        listing__seller=request.user,
    ).annotate(has_seller_reply=Exists(seller_reply))
    summary = all_reviews.aggregate(average=Avg('rating'), total=Count('pk'))
    rating_counts = {
        row['rating']: row['count']
        for row in all_reviews.values('rating').annotate(count=Count('pk'))
    }
    distribution = [
        {'rating': rating, 'count': rating_counts.get(rating, 0)}
        for rating in range(5, 0, -1)
    ]
    needs_reply_count = all_reviews.filter(
        listing__lifecycle_state=Listing.Lifecycle.NORMAL,
        has_seller_reply=False,
    ).count()

    selected_listing = request.GET.get('listing', '')
    selected_rating = request.GET.get('rating', '')
    needs_reply = request.GET.get('needs_reply') == '1'
    reviews = all_reviews.select_related('listing', 'reviewer').prefetch_related(
        'photos',
        'replies__author',
    ).order_by('-created_at', '-pk')
    if selected_listing.isdigit() and listings.filter(pk=selected_listing).exists():
        reviews = reviews.filter(listing_id=selected_listing)
    else:
        selected_listing = ''
    if selected_rating in {str(value) for value, _ in ListingReview.Rating.choices}:
        reviews = reviews.filter(rating=selected_rating)
    else:
        selected_rating = ''
    if needs_reply:
        reviews = reviews.filter(
            listing__lifecycle_state=Listing.Lifecycle.NORMAL,
            has_seller_reply=False,
        )

    page_obj = Paginator(reviews, REPUTATION_PAGE_SIZE).get_page(request.GET.get('page'))
    page_links = []
    for page_number in page_obj.paginator.page_range:
        query = request.GET.copy()
        query['page'] = page_number
        page_links.append({
            'number': page_number,
            'url': f'{request.path}?{query.urlencode()}',
        })
    page_urls = {page['number']: page['url'] for page in page_links}

    return render(request, 'seller/reputation.html', {
        'listings': listings,
        'reviews': page_obj.object_list,
        'page_obj': page_obj,
        'page_links': page_links,
        'average_rating': round(summary['average'] or 0, 1),
        'review_count': summary['total'],
        'rating_distribution': distribution,
        'rating_choices': ListingReview.Rating.choices,
        'needs_reply_count': needs_reply_count,
        'selected_listing': selected_listing,
        'selected_rating': selected_rating,
        'needs_reply': needs_reply,
        'reply_form': ListingReviewReplyForm(),
        'rating_stars': range(1, 6),
        'return_url': request.get_full_path(),
        'previous_page_url': page_urls.get(page_obj.previous_page_number()) if page_obj.has_previous() else '',
        'next_page_url': page_urls.get(page_obj.next_page_number()) if page_obj.has_next() else '',
    })


@login_required
def become_seller(request):
    messages.success(request, 'Your seller workspace is ready.')
    return redirect('dashboard:seller')


@login_required
def create_listing(request):
    if request.method != 'POST':
        return redirect('dashboard:seller')

    try:
        uploaded_images = validate_listing_images(request.FILES.getlist('images'))
    except ValidationError as error:
        messages.error(request, f'Listing was not saved: {error}. Please reselect the photos and try again.')
        return redirect('dashboard:seller')

    form = ListingForm(request.POST, request.FILES)
    if form.is_valid():
        listing = form.save(commit=False)
        listing.seller = request.user
        listing.status = listing.status or Listing.Status.ACTIVE
        if getattr(listing.category, 'slug', '').lower() == 'services':
            listing.stock_quantity = 0
        elif listing.stock_quantity is None:
            listing.stock_quantity = 0
        listing.save()
        if uploaded_images:
            listing.image = uploaded_images[0]
            listing.save(update_fields=['image', 'updated_at'])
            save_listing_images(listing, uploaded_images)
        messages.success(request, 'Your listing has been saved.')
    else:
        messages.error(request, f'Listing was not saved: {form.errors.as_text()}')
    return redirect('dashboard:seller')


@login_required
def edit_listing(request, listing_id):
    listing = get_object_or_404(
        Listing,
        pk=listing_id,
        seller=request.user,
        lifecycle_state=Listing.Lifecycle.NORMAL,
    )
    if request.method == 'GET':
        return render(
            request,
            'seller/edit-listing.html',
            {
                'listing': listing,
                'listing_form': ListingForm(instance=listing),
                'categories': _category_context(),
            },
        )

    # ModelForm validation writes the POSTed values onto `listing`, so remember
    # the stock the seller had before this edit.
    previous_stock = listing.stock_quantity
    remove_ids = [value for value in request.POST.getlist('remove_image_ids') if value.isdigit()]
    remove_urls = request.POST.getlist('remove_image_urls')
    kept_image_count = listing.listing_images.exclude(id__in=remove_ids).count()
    kept_image_count += len([url for url in listing.image_urls if url not in remove_urls])
    try:
        uploaded_images = validate_listing_images(
            request.FILES.getlist('images'),
            existing_count=kept_image_count,
        )
    except ValidationError as error:
        messages.error(request, f'Listing was not updated: {error}. Please reselect the new photos and try again.')
        return redirect(request.POST.get('next') or 'dashboard:seller')

    form = ListingForm(request.POST, instance=listing)
    if form.is_valid():
        updated_listing = form.save(commit=False)
        if updated_listing.category and updated_listing.category.slug.lower() == 'services':
            updated_listing.stock_quantity = 0
        elif updated_listing.stock_quantity is None:
            updated_listing.stock_quantity = 0
        elif (
            updated_listing.status == Listing.Status.SOLD
            and updated_listing.stock_quantity > previous_stock
        ):
            # The seller added stock to a sold listing: put it back on sale.
            # If they chose Draft/Archived in the same edit, that choice wins.
            updated_listing.status = Listing.Status.ACTIVE
        updated_listing.save()
        if remove_urls:
            listing.image_urls = [url for url in listing.image_urls if url not in remove_urls]
            listing.save(update_fields=['image_urls', 'updated_at'])
        if remove_ids:
            remove_listing_images(listing, remove_ids)
        if not listing.listing_images.exists() and not listing.image_urls:
            listing.image = None
            listing.save(update_fields=['image', 'updated_at'])
        if uploaded_images:
            save_listing_images(listing, uploaded_images)
        messages.success(request, 'Your listing has been updated.')
    else:
        messages.error(request, f'Listing was not updated: {form.errors.as_text()}')
    return redirect(request.POST.get('next') or 'dashboard:seller')


@login_required
def delete_listing_image(request, listing_id, image_id):
    if request.method == 'POST':
        image = get_object_or_404(
            ListingImage,
            pk=image_id,
            listing_id=listing_id,
            listing__seller=request.user,
            listing__lifecycle_state=Listing.Lifecycle.NORMAL,
        )
        remove_listing_images(image.listing, [image.id])
        messages.success(request, 'Photo removed from the listing.')
    return redirect(request.POST.get('next') or 'dashboard:seller')


@login_required
@require_POST
def delete_listing(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id, seller=request.user)
    if listing.lifecycle_state != Listing.Lifecycle.NORMAL:
        messages.info(request, 'This listing is already unavailable.')
        return redirect('dashboard:seller')

    move_to_recycle_bin(listing)
    messages.success(request, 'The listing moved to the Recycle Bin and is hidden from public browsing.')
    return redirect('dashboard:seller')


@login_required
@require_POST
def restore_listing(request, listing_id):
    result = restore_recycled_listing(listing_id, request.user)
    if result == RESTORED:
        messages.success(request, 'Listing restored. Its previous stock and availability status were kept.')
    elif result == EXPIRED:
        messages.info(request, 'This listing reached its 30-day Recycle Bin limit and is no longer available to restore.')
    else:
        messages.info(request, 'This listing is no longer available to restore.')
    return redirect('dashboard:seller')


def _buyer_affinity_categories(user):
    if not user.is_authenticated:
        return set()
    saved_categories = SavedItem.objects.filter(buyer=user).values_list('listing__category_id', flat=True)
    # A buyer's messaging history also signals category interest, without a
    # direct dependency on the messaging app's models here.
    from apps.messaging.models import Conversation
    messaged_categories = Conversation.objects.filter(buyer=user).values_list('listing__category_id', flat=True)
    return set(saved_categories) | set(messaged_categories)


def _rank_listings_for_buyer(listings, user):
    # score = 0.5 * popularity + 0.2 * recency + 0.3 * affinity

    listings = list(listings)
    if not listings:
        return listings

    affinity_categories = _buyer_affinity_categories(user)
    max_views = max((listing.views for listing in listings), default=0) or 1
    now = timezone.now()

    def score(listing):
        popularity_score = listing.views / max_views
        days_old = max((now - listing.created_at).days, 0)
        recency_score = 1 / (1 + days_old)
        affinity_score = 1 if listing.category_id in affinity_categories else 0
        return (
            RECOMMENDATION_WEIGHTS['popularity'] * popularity_score
            + RECOMMENDATION_WEIGHTS['recency'] * recency_score
            + RECOMMENDATION_WEIGHTS['affinity'] * affinity_score
        )

    return sorted(listings, key=score, reverse=True)


def setup_buyer_dashboard(request):
    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', 'all').strip().lower()
    seller_id = request.GET.get('seller')
    listings = Listing.objects.filter(
        status=Listing.Status.ACTIVE,
        lifecycle_state=Listing.Lifecycle.NORMAL,
    ).select_related(
        'seller',
        'category',
    ).annotate(
        rating_average=Avg('reviews__rating'),
        rating_count=Count('reviews'),
    )
    if request.user.is_authenticated:
        cart_membership = SavedItem.objects.filter(
            buyer=request.user,
            listing_id=OuterRef('pk'),
        )
        # The shared card can render the authoritative cart state without a
        # separate query for every listing.
        listings = listings.annotate(is_in_cart=Exists(cart_membership))

    if query:
        listings = listings.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
        )
    if category_slug != 'all':
        listings = listings.filter(category__slug=category_slug)

    seller_profile = None
    if seller_id:
        try:
            seller = get_object_or_404(User, pk=int(seller_id))
            seller_profile = _seller_profile(seller)
            listings = listings.filter(seller=seller)
        except (TypeError, ValueError):
            seller_profile = None
    elif request.user.is_authenticated:
        # Professional marketplaces don't surface a seller's own active
        # listings in their own general browse/recommended feed - that's
        # what the seller dashboard is for. An explicit storefront view
        # (?seller=<id>) is untouched, so a seller can still reach their
        # own listings that way if they land on it.
        listings = listings.exclude(seller_id=request.user.id)

    if seller_id:
        # A specific seller's storefront: keep the existing chronological
        # order rather than personalizing it.
        items = listings
        item_count = listings.count()
    else:
        items = _rank_listings_for_buyer(listings, request.user)
        item_count = len(items)

    if seller_profile is not None:
        seller_profile['listing_count'] = item_count

    context = {
        'items': items,
        'categories': _category_context(),
        'selected_category': category_slug,
        'query': query,
        'category_count': item_count,
        'seller_filter': seller_id,
        'seller_profile': seller_profile,
        'rating_stars': range(1, 6),
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'buyer/product-feed.html', context)

    return render(request, 'buyer/buyer-dashboard.html', context)


def setup_buyer_item_detail(request, item_slug, review_form=None, increment_view=True):
    listing = get_object_or_404(
        Listing.objects.select_related('seller', 'category'),
        slug=item_slug,
    )
    if listing.lifecycle_state != Listing.Lifecycle.NORMAL:
        raise Http404('Listing not found.')
    saved_by_request_user = request.user.is_authenticated and SavedItem.objects.filter(
        buyer=request.user,
        listing=listing,
    ).exists()
    if listing.status not in (
        Listing.Status.ACTIVE,
        Listing.Status.RESERVED,
        Listing.Status.SOLD,
        Listing.Status.ARCHIVED,
    ):
        raise Http404('Listing not found.')
    if increment_view:
        Listing.objects.filter(pk=listing.pk).update(views=listing.views + 1)
        listing.views += 1
    other_products = Listing.objects.filter(
        seller=listing.seller,
        status=Listing.Status.ACTIVE,
        lifecycle_state=Listing.Lifecycle.NORMAL,
    ).exclude(pk=listing.pk).select_related('category')
    gallery_images = [
        {'id': image.id, 'url': image.image.url}
        for image in listing.listing_images.all()
    ]
    if not gallery_images:
        gallery_images = [{'id': None, 'url': image} for image in listing.gallery_urls]
    listing_reviews = (
        ListingReview.objects.filter(listing=listing)
        .select_related('reviewer')
        .prefetch_related('photos', 'replies__author')
    )
    review_summary = listing_reviews.aggregate(average=Avg('rating'), total=Count('id'))
    review_count = review_summary['total']
    counts_by_rating = {
        row['rating']: row['count']
        for row in listing_reviews.values('rating').annotate(count=Count('id'))
    }
    rating_breakdown = [
        {
            'value': rating,
            'count': counts_by_rating.get(rating, 0),
            'percentage': round(counts_by_rating.get(rating, 0) * 100 / review_count) if review_count else 0,
        }
        for rating in range(5, 0, -1)
    ]
    can_review = request.user.is_authenticated and request.user.id != listing.seller_id
    user_review = listing_reviews.filter(reviewer=request.user).first() if can_review else None
    user_review_photo_count = user_review.photos.count() if user_review else 0
    review_form = review_form if review_form is not None else ListingReviewForm(instance=user_review)
    selected_rating = str(review_form['rating'].value() or '')

    seller_other_reviews = ListingReview.objects.none()
    seller_other_review_summary = {'average': None, 'total': 0}
    seller_other_review_queryset = ListingReview.objects.filter(
        listing__seller=listing.seller,
    ).exclude(
        listing=listing,
    ).exclude(
        listing__status=Listing.Status.DRAFT,
    )
    seller_other_review_summary = seller_other_review_queryset.aggregate(
        average=Avg('rating'),
        total=Count('id'),
    )
    if seller_other_review_summary['total']:
        seller_other_reviews = (
            seller_other_review_queryset.select_related('reviewer', 'listing')
            .prefetch_related('photos')[:REVIEW_DISPLAY_LIMIT]
        )
    item_context = {
        'id': listing.id,
        'slug': listing.slug,
        'title': listing.title,
        'category': listing.category.name,
        'price': listing.price,
        'price_label': listing.price_label,
        'condition': listing.condition,
        'location': listing.location,
        'stock_quantity': listing.stock_quantity,
        'seller_id': listing.seller_id,
        'seller': listing.seller_name,
        'seller_avatar': listing.seller_avatar_url,
        'seller_role': listing.seller_role,
        'status': listing.status,
        'views': listing.views,
        'image_url': listing.image_url,
        'images': listing.gallery_urls,
        'gallery_images': gallery_images,
        'description': listing.description,
    }
    return render(
        request,
        'buyer/buyer-detail.html',
        {
            'item': item_context,
            'seller_info': _seller_profile(listing.seller),
            'can_edit': request.user.is_authenticated and request.user.id == listing.seller_id,
            'other_products': other_products,
            'categories': _category_context(),
            'selected_category': listing.category.slug,
            'query': request.GET.get('q', ''),
            'is_saved': saved_by_request_user,
            'condition_choices': [value for value, _ in CONDITION_CHOICES],
            'average_rating': round(review_summary['average'] or 0, 1),
            'review_count': review_count,
            'rating_breakdown': rating_breakdown,
            'rating_stars': range(1, 6),
            'rating_options': [{'value': str(rating)} for rating, _ in ListingReview.Rating.choices],
            'listing_reviews': listing_reviews,
            'seller_other_reviews': seller_other_reviews,
            'seller_other_review_average': seller_other_review_summary['average'],
            'seller_other_review_count': seller_other_review_summary['total'],
            'can_review': can_review,
            'user_review': user_review,
            'selected_rating': selected_rating,
            'user_review_photo_count': user_review_photo_count,
            'remaining_review_photos': MAX_REVIEW_PHOTOS - user_review_photo_count,
            'review_photo_limit': MAX_REVIEW_PHOTOS,
            'review_form': review_form,
            'reply_form': ListingReviewReplyForm(),
        },
    )


@login_required
@require_POST
def submit_listing_review(request, item_slug):
    listing = get_object_or_404(Listing, slug=item_slug)
    if listing.lifecycle_state != Listing.Lifecycle.NORMAL:
        raise Http404('Listing not found.')
    if listing.seller_id == request.user.id:
        messages.error(request, 'You cannot review your own listing.')
        return redirect(f'{listing.get_absolute_url()}#listing-reviews')

    existing_review = ListingReview.objects.filter(listing=listing, reviewer=request.user).first()
    form = ListingReviewForm(request.POST, request.FILES, instance=existing_review)
    if not form.is_valid():
        return setup_buyer_item_detail(
            request,
            item_slug,
            review_form=form,
            increment_view=False,
        )

    photos = form.cleaned_data['photos']
    photos_to_remove = list(
        existing_review.photos.filter(pk__in=request.POST.getlist('remove_photo_ids'))
    ) if existing_review else []
    retained_photo_count = (existing_review.photos.count() if existing_review else 0) - len(photos_to_remove)
    if retained_photo_count + len(photos) > MAX_REVIEW_PHOTOS:
        messages.error(request, f'A review can include up to {MAX_REVIEW_PHOTOS} photos in total.')
        return redirect(f'{listing.get_absolute_url()}#listing-reviews')

    review = form.save(commit=False)
    review.listing = listing
    review.reviewer = request.user
    review.save()
    for photo in photos_to_remove:
        photo.image.delete(save=False)
        photo.delete()
    for photo in photos:
        ListingReviewPhoto.objects.create(review=review, image=photo)
    messages.success(request, 'Your review has been updated.' if existing_review else 'Your review has been posted.')
    return redirect(f'{listing.get_absolute_url()}#listing-reviews')


def _review_redirect(request, review):
    destination = request.POST.get('next', '')
    if destination and url_has_allowed_host_and_scheme(
        url=destination,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(destination)
    return redirect(f'{review.listing.get_absolute_url()}#review-{review.pk}')


def _review_participant(review, user):
    return user.pk in (review.reviewer_id, review.listing.seller_id)


def _notify_review_reply(reply):
    try:
        review = reply.review
        recipient = review.reviewer if reply.author_id == review.listing.seller_id else review.listing.seller
        ReviewNotification.objects.create(recipient=recipient, reply=reply)
    except Exception:
        logger.exception('Review reply notification failed for reply=%s', reply.pk)


@login_required
@require_POST
def add_listing_review_reply(request, review_id):
    review = get_object_or_404(
        ListingReview.objects.select_related('listing__seller', 'reviewer'),
        pk=review_id,
    )
    if not _review_participant(review, request.user):
        raise PermissionDenied
    if review.listing.lifecycle_state != Listing.Lifecycle.NORMAL:
        raise Http404('Listing not found.')

    form = ListingReviewReplyForm(request.POST)
    if not form.is_valid():
        messages.error(request, form.errors.as_text())
        return _review_redirect(request, review)

    reply = form.save(commit=False)
    reply.review = review
    reply.author = request.user
    reply.save()
    _notify_review_reply(reply)
    messages.success(request, 'Your reply has been posted.')
    return _review_redirect(request, review)


@login_required
@require_POST
def edit_listing_review_reply(request, reply_id):
    reply = get_object_or_404(
        ListingReviewReply.objects.select_related('review__listing__seller', 'review__reviewer'),
        Q(review__listing__seller=request.user) | Q(review__reviewer=request.user),
        pk=reply_id,
    )
    if reply.author_id != request.user.id:
        raise PermissionDenied
    if reply.review.listing.lifecycle_state != Listing.Lifecycle.NORMAL:
        raise Http404('Listing not found.')

    form = ListingReviewReplyForm(request.POST, instance=reply)
    if not form.is_valid():
        messages.error(request, form.errors.as_text())
        return _review_redirect(request, reply.review)
    form.save()
    messages.success(request, 'Your reply has been updated.')
    return _review_redirect(request, reply.review)


@login_required
@require_POST
def delete_listing_review_reply(request, reply_id):
    reply = get_object_or_404(
        ListingReviewReply.objects.select_related('review__listing__seller', 'review__reviewer'),
        Q(review__listing__seller=request.user) | Q(review__reviewer=request.user),
        pk=reply_id,
    )
    if reply.author_id != request.user.id:
        raise PermissionDenied
    if reply.review.listing.lifecycle_state != Listing.Lifecycle.NORMAL:
        raise Http404('Listing not found.')

    review = reply.review
    reply.delete()
    messages.success(request, 'Your reply has been deleted.')
    return _review_redirect(request, review)


@login_required
@require_POST
def open_review_notification(request, notification_id):
    notification = get_object_or_404(
        ReviewNotification.objects.select_related('reply__review__listing'),
        pk=notification_id,
        recipient=request.user,
    )
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    return redirect(notification.link)


@login_required
@require_POST
def mark_review_notifications_read(request):
    request.user.review_notifications.filter(is_read=False).update(is_read=True)
    destination = request.POST.get('next', '')
    if destination and url_has_allowed_host_and_scheme(
        url=destination,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(destination)
    return redirect('dashboard:buyer')


@login_required
def toggle_saved_item(request, item_slug):
    listing = get_object_or_404(Listing, slug=item_slug)
    if request.method == 'POST':
        saved_item = SavedItem.objects.filter(buyer=request.user, listing=listing).first()
        if saved_item:
            saved_item.delete()
            messages.info(request, 'Listing removed from your saved items.')
        elif listing.seller_id == request.user.id:
            messages.error(request, 'You cannot add your own listing to your cart.')
        elif listing.status == Listing.Status.ACTIVE and listing.lifecycle_state == Listing.Lifecycle.NORMAL:
            SavedItem.objects.create(buyer=request.user, listing=listing)
            messages.success(request, 'Listing saved for later.')
            saved = True
        else:
            messages.error(request, 'This product is no longer available.')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'saved': SavedItem.objects.filter(buyer=request.user, listing=listing).exists(), 'cart_count': request.user.saved_items.count()})
    return redirect(request.POST.get('next') or listing.get_absolute_url())


@login_required
def setup_buyer_cart(request):
    saved_items = SavedItem.objects.filter(buyer=request.user).select_related(
        'listing', 'listing__seller', 'listing__category',
    )
    return render(
        request,
        'buyer/buyer-cart.html',
        {
            'saved_items': saved_items,
            'active_saved_items': saved_items.filter(
                listing__status=Listing.Status.ACTIVE,
                listing__lifecycle_state=Listing.Lifecycle.NORMAL,
            ),
            'sold_saved_items': saved_items.exclude(
                listing__status=Listing.Status.ACTIVE,
                listing__lifecycle_state=Listing.Lifecycle.NORMAL,
            ),
            'categories': _category_context(),
        },
    )


# Everything from here down through conversation_*, delete_message,
# clear_conversation, edit_message, message_history, link_preview and
# unread_message_count -- along with their private helpers (_message_payload,
# _mark_conversation_read, _visible_messages_for_user, etc.) and
# start_conversation -- has moved to apps.messaging.views /
# apps.messaging.services / apps.messaging.selectors.
