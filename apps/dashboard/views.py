import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User

from .forms import CONDITION_CHOICES, PRODUCT_CONDITIONS, SERVICE_CONDITIONS, ListingForm, MessageForm
from .models import Category, Conversation, Listing, ListingImage, Message, SavedItem


# Relative weight of each signal in the "Recommended for you" ranking.
# Tunable without touching the scoring logic itself.
RECOMMENDATION_WEIGHTS = {
    'popularity': 0.5,
    'recency': 0.2,
    'affinity': 0.3,
}


def _conversation_resources(conversation):
    media = []
    files = []
    links = []
    for message in conversation.messages.all():
        if message.attachment:
            resource = {
                'url': message.attachment.url,
                'name': message.attachment.name.rsplit('/', 1)[-1],
                'is_image': message.attachment_is_image,
            }
            (media if resource['is_image'] else files).append(resource)
        links.extend(re.findall(r'https?://[^\s<]+', message.body or ''))
    return media, files, list(dict.fromkeys(links))


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
        'count': Listing.objects.filter(status=Listing.Status.ACTIVE).count(),
    }]
    category_context.extend([
        {
            'id': category.id,
            'label': category.name,
            'slug': category.slug,
            'count': Listing.objects.filter(
                category=category,
                status=Listing.Status.ACTIVE,
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
    }


@login_required
def setup_seller_dashboard(request):
    listings = Listing.objects.filter(seller=request.user).select_related('category')
    active_listings = listings.filter(status=Listing.Status.ACTIVE)
    context = {
        'listings': listings,
        'listing_form': ListingForm(),
        'categories': _category_context(),
        'condition_choices': [value for value, _ in CONDITION_CHOICES],
        'condition_options': _condition_options(),
        'active_count': active_listings.count(),
        'total_views': sum(listing.views for listing in listings),
        'sold_count': listings.filter(status=Listing.Status.SOLD).count(),
        'manage_listing_id': request.GET.get('manage'),
    }
    return render(request, 'seller/seller-dashboard.html', context)


@login_required
def become_seller(request):
    messages.success(request, 'Your seller workspace is ready.')
    return redirect('dashboard:seller')


@login_required
def create_listing(request):
    if request.method != 'POST':
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
        uploaded_images = request.FILES.getlist('images')[:8]
        if uploaded_images:
            listing.image = uploaded_images[0]
            listing.save(update_fields=['image', 'updated_at'])
            _save_listing_images(listing, uploaded_images)
        messages.success(request, 'Your listing has been saved.')
    else:
        messages.error(request, f'Listing was not saved: {form.errors.as_text()}')
    return redirect('dashboard:seller')


@login_required
def edit_listing(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id, seller=request.user)
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

    form = ListingForm(request.POST, instance=listing)
    if form.is_valid():
        updated_listing = form.save(commit=False)
        if updated_listing.category and updated_listing.category.slug.lower() == 'services':
            updated_listing.stock_quantity = 0
        elif updated_listing.stock_quantity is None:
            updated_listing.stock_quantity = 0
        updated_listing.save()
        remove_ids = [value for value in request.POST.getlist('remove_image_ids') if value.isdigit()]
        remove_urls = request.POST.getlist('remove_image_urls')
        if remove_urls:
            listing.image_urls = [url for url in listing.image_urls if url not in remove_urls]
            listing.save(update_fields=['image_urls', 'updated_at'])
        if remove_ids:
            _remove_listing_images(listing, remove_ids)
        if not listing.listing_images.exists() and not listing.image_urls:
            listing.image = None
            listing.save(update_fields=['image', 'updated_at'])
        uploaded_images = request.FILES.getlist('images')
        if uploaded_images:
            _save_listing_images(listing, uploaded_images)
        messages.success(request, 'Your listing has been updated.')
    else:
        messages.error(request, f'Listing was not updated: {form.errors.as_text()}')
    return redirect(request.POST.get('next') or 'dashboard:seller')


@login_required
def delete_listing_image(request, listing_id, image_id):
    if request.method == 'POST':
        image = get_object_or_404(ListingImage, pk=image_id, listing_id=listing_id, listing__seller=request.user)
        _remove_listing_images(image.listing, [image.id])
        messages.success(request, 'Photo removed from the listing.')
    return redirect(request.POST.get('next') or 'dashboard:seller')


def _save_listing_images(listing, uploaded_images):
    for image in uploaded_images:
        if not listing.image:
            listing.image = image
            listing.save(update_fields=['image', 'updated_at'])
        ListingImage.objects.create(listing=listing, image=image)


def _remove_listing_images(listing, image_ids):
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


@login_required
def delete_listing(request, listing_id):
    if request.method == 'POST':
        listing = get_object_or_404(Listing, pk=listing_id, seller=request.user)
        listing.delete()
        messages.success(request, 'The listing was deleted.')
    return redirect('dashboard:seller')


def _buyer_affinity_categories(user):
    """Category IDs a buyer has shown interest in: saved or messaged about.
    Returns an empty set for anonymous visitors or buyers with no history,
    which naturally reduces the ranking below to popularity + recency only.
    """
    if not user.is_authenticated:
        return set()
    saved_categories = SavedItem.objects.filter(buyer=user).values_list('listing__category_id', flat=True)
    messaged_categories = Conversation.objects.filter(buyer=user).values_list('listing__category_id', flat=True)
    return set(saved_categories) | set(messaged_categories)


def _rank_listings_for_buyer(listings, user):
    """Score and order listings for the "Recommended for you" feed.

    score = 0.5 * popularity + 0.2 * recency + 0.3 * affinity

    - popularity: views normalized against the highest view count in this
      result set, so no single outlier listing skews everything else.
    - recency: 1 / (1 + days_since_created), a soft decay rather than a
      hard cutoff, so a brand-new listing with 0 views still ranks
      reasonably instead of sinking to the bottom.
    - affinity: 1 if the listing's category matches one the buyer has
      saved or messaged about before, else 0.

    Evaluates the queryset once into a list and scores in Python. Simple
    and portable across DB backends; if the catalog grows large enough
    for this to matter, move the popularity/recency math into the query
    itself and keep only affinity lookups in Python.
    """
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
    listings = Listing.objects.filter(status=Listing.Status.ACTIVE).select_related('seller', 'category')

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

    context = {
        'items': items,
        'categories': _category_context(),
        'selected_category': category_slug,
        'query': query,
        'category_count': item_count,
        'seller_filter': seller_id,
        'seller_profile': seller_profile,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'buyer/product-feed.html', context)

    return render(request, 'buyer/buyer-dashboard.html', context)


def setup_buyer_item_detail(request, item_slug):
    listing = get_object_or_404(
        Listing.objects.select_related('seller', 'category'),
        slug=item_slug,
    )
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
    Listing.objects.filter(pk=listing.pk).update(views=listing.views + 1)
    listing.views += 1
    other_products = Listing.objects.filter(
        seller=listing.seller,
        status=Listing.Status.ACTIVE,
    ).exclude(pk=listing.pk).select_related('category')
    gallery_images = [
        {'id': image.id, 'url': image.image.url}
        for image in listing.listing_images.all()
    ]
    if not gallery_images:
        gallery_images = [{'id': None, 'url': image} for image in listing.gallery_urls]
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
        },
    )


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
        elif listing.status == Listing.Status.ACTIVE:
            SavedItem.objects.create(buyer=request.user, listing=listing)
            messages.success(request, 'Listing saved for later.')
        else:
            messages.error(request, 'This product is no longer available.')
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
            'active_saved_items': saved_items.exclude(listing__status=Listing.Status.SOLD),
            'sold_saved_items': saved_items.filter(listing__status=Listing.Status.SOLD),
            'categories': _category_context(),
        },
    )


@login_required
def start_conversation(request, item_slug):
    listing = get_object_or_404(Listing, slug=item_slug)
    if listing.seller_id == request.user.id:
        messages.error(request, 'You cannot message yourself about your own listing.')
        return redirect(listing.get_absolute_url())
    conversation, _ = Conversation.objects.get_or_create(
        buyer=request.user,
        seller=listing.seller,
        listing=listing,
    )
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            conversation.save(update_fields=['updated_at'])
            messages.success(request, 'Message sent to the seller.')
        else:
            messages.error(request, 'Your message could not be sent. Please try again.')
    return redirect('dashboard:conversation', conversation_id=conversation.pk)


@login_required
def conversation_list(request):
    conversations = Conversation.objects.filter(
        Q(buyer=request.user) | Q(seller=request.user)
    ).select_related('buyer', 'seller', 'listing')
    return render(
        request,
        'messaging/messaging.html',
        {'conversations': conversations, 'categories': _category_context()},
    )


@login_required
def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(
        Conversation.objects.select_related('buyer', 'seller', 'listing'),
        Q(buyer=request.user) | Q(seller=request.user),
        pk=conversation_id,
    )
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            conversation.save(update_fields=['updated_at'])
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'body': message.body,
                    'attachment_url': message.attachment.url if message.attachment else '',
                    'attachment_name': message.attachment.name.rsplit('/', 1)[-1] if message.attachment else '',
                    'attachment_is_image': message.attachment_is_image,
                    'created_at': message.created_at.isoformat(),
                    'sender_id': message.sender_id,
                    'sender_avatar_url': message.sender.avatar_url,
                })
            messages.success(request, 'Message sent.')
            return redirect('dashboard:conversation', conversation_id=conversation.pk)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Your message could not be sent. Please check the message and attachment.'}, status=400)
        messages.error(request, 'Your message could not be sent. Please try again.')
    else:
        form = MessageForm()
    participant = conversation.seller if conversation.buyer_id == request.user.id else conversation.buyer
    media, files, links = _conversation_resources(conversation)
    conversation.messages.exclude(sender=request.user).filter(is_read=False).update(is_read=True)
    return render(
        request,
        'messaging/messaging.html',
        {
            'conversation': conversation,
            'selected_conversation': conversation,
            'conversation_messages': conversation.messages.select_related('sender'),
            'message_form': form,
            'conversations': Conversation.objects.filter(
                Q(buyer=request.user) | Q(seller=request.user)
            ).select_related('buyer', 'seller', 'listing'),
            'categories': _category_context(),
            'chat_participant': participant,
            'chat_media': media,
            'chat_files': files,
            'chat_links': links,
        },
    )