from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.db import transaction
from django.db.models import Count, Exists, F, OuterRef, Q, Subquery
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import logging
import uuid

from apps.accounts.models import User

from .forms import CONDITION_CHOICES, PRODUCT_CONDITIONS, SERVICE_CONDITIONS, ListingForm, MessageForm
from .models import Category, Conversation, ConversationTypingState, ConversationUserState, Listing, ListingImage, Message, MessageAttachment, MessageRevision, SavedItem
from apps.messaging.link_previews import get_link_preview
from apps.messaging.message_urls import extract_meaningful_message_urls
from urllib.parse import urlparse


logger = logging.getLogger(__name__)


# Relative weight of each signal in the "Recommended for you" ranking.
# Tunable without touching the scoring logic itself.
RECOMMENDATION_WEIGHTS = {
    'popularity': 0.5,
    'recency': 0.2,
    'affinity': 0.3,
}


def _conversation_state(conversation, user):
    return ConversationUserState.objects.filter(conversation=conversation, user=user).first()


def _clear_cutoff_for(conversation, user):
    state = _conversation_state(conversation, user)
    return state.cleared_through_message_id if state else None


def _visible_messages_for_user(conversation, user):
    """Messages visible in a participant's local copy of a shared thread."""
    messages = conversation.messages.all()
    cutoff = _clear_cutoff_for(conversation, user)
    return messages.filter(pk__gt=cutoff) if cutoff else messages


def _other_participant_typing(conversation, user):
    other_user_id = conversation.seller_id if user.id == conversation.buyer_id else conversation.buyer_id
    last_activity_at = ConversationTypingState.objects.filter(
        conversation=conversation,
        user_id=other_user_id,
    ).values_list('last_activity_at', flat=True).first()
    now = timezone.now()
    result = bool(last_activity_at and last_activity_at >= now - timedelta(seconds=3))
    age_seconds = (now - last_activity_at).total_seconds() if last_activity_at else None
    logger.warning(
        '[TYPE-SERVER-READ] conversation=%s viewer=%s other=%s last_activity_at=%s now=%s age_seconds=%s freshness_limit=3 result=%s',
        conversation.pk, user.pk, other_user_id,
        last_activity_at.isoformat() if last_activity_at else 'NULL', now.isoformat(),
        round(age_seconds, 3) if age_seconds is not None else 'NULL', result,
    )
    return result


def _visible_participant_messages_for(user):
    """All messages visible to a user across their conversations, without N+1 state lookups."""
    state = ConversationUserState.objects.filter(conversation_id=OuterRef('conversation_id'), user=user)
    return Message.objects.filter(Q(conversation__buyer=user) | Q(conversation__seller=user)).annotate(
        local_cleared_through_id=Subquery(state.values('cleared_through_message_id')[:1]),
        local_cleared_at=Subquery(state.values('cleared_at')[:1]),
    ).filter(
        Q(local_cleared_at__isnull=True) | Q(local_cleared_through_id__isnull=True) | Q(pk__gt=F('local_cleared_through_id')),
    )


def _conversation_resources(conversation, user):
    media = []
    files = []
    links = []
    for message in _visible_messages_for_user(conversation, user).filter(is_deleted=False).prefetch_related('attachments'):
        message_attachments = list(message.attachments.all())
        if message.attachment and not message_attachments:
            message_attachments = [message]
        for attachment in message_attachments:
            resource = {
                'url': attachment.file.url if hasattr(attachment, 'file') else attachment.attachment.url,
                'name': (attachment.file.name if hasattr(attachment, 'file') else attachment.attachment.name).rsplit('/', 1)[-1],
                'is_image': attachment.is_image if hasattr(attachment, 'is_image') else attachment.attachment_is_image,
                'is_video': attachment.is_video if hasattr(attachment, 'is_video') else False,
            }
            (media if resource['is_image'] or resource['is_video'] else files).append(resource)
        links.extend(extract_meaningful_message_urls(message.body))
    return media, files, [_link_card(link) for link in dict.fromkeys(links)]


def _link_card(url, preview=None):
    """Provide a safe Details-card fallback even if metadata cannot be fetched."""
    parsed = urlparse(url)
    domain = (parsed.hostname or '').removeprefix('www.')
    preview = preview or {}
    return {
        'url': url,
        'title': preview.get('title') or domain or url,
        'domain': domain,
        'image': preview.get('image') or '',
        'is_drive': (parsed.hostname or '').lower() in ('drive.google.com', 'www.drive.google.com'),
    }


def _message_payload(message):
    """The shared JSON shape for sent and polled chat messages."""
    if message.is_deleted:
        sender_name = f'{message.sender.first_name} {message.sender.last_name}'.strip() or message.sender.email
        return {
            'id': message.pk,
            'is_deleted': True,
            'sender_id': message.sender_id,
            'sender_name': sender_name,
            'created_at': message.created_at.isoformat(),
        }
    attachments = [{
        'url': attachment.file.url,
        'name': attachment.file.name.rsplit('/', 1)[-1],
        'is_image': attachment.is_image,
        'is_video': attachment.is_video,
    } for attachment in message.attachments.all()]
    if message.attachment and not attachments:
        attachments = [{'url': message.attachment.url, 'name': message.attachment.name.rsplit('/', 1)[-1], 'is_image': message.attachment_is_image, 'is_video': False}]
    return {
        'id': message.pk,
        'body': message.body,
        'attachment_url': message.attachment.url if message.attachment else '',
        'attachment_name': message.attachment.name.rsplit('/', 1)[-1] if message.attachment else '',
        'attachment_is_image': message.attachment_is_image,
        'attachments': attachments,
        'created_at': message.created_at.isoformat(),
        'sender_id': message.sender_id,
        'sender_avatar_url': message.sender.avatar_url,
        'is_edited': message.is_edited,
        'edited_at': message.edited_at.isoformat() if message.edited_at else '',
    }


def _latest_visible_revision_id(conversation, user):
    """Return the revision cursor represented by the currently rendered chat."""
    revisions = MessageRevision.objects.filter(message__conversation=conversation)
    cutoff = _clear_cutoff_for(conversation, user)
    if cutoff:
        revisions = revisions.filter(message_id__gt=cutoff)
    return revisions.order_by('-pk').values_list('pk', flat=True).first() or 0


def _save_message_with_attachments(form, conversation, sender, files):
    message = form.save(commit=False)
    message.conversation = conversation
    message.sender = sender
    # New multi-file uploads live in MessageAttachment; retain Message.attachment
    # solely for existing records and backwards compatibility.
    message.attachment = None
    message.save()
    MessageAttachment.objects.bulk_create([
        MessageAttachment(message=message, file=attachment) for attachment in files.getlist('attachments')
    ])
    return message


def _unread_message_count(user):
    return sum(conversation.unread_count for conversation in _visible_active_conversations_for(user).annotate(
        unread_count=_visible_unread_count_annotation(user),
    ))


def _conversation_groups(conversations, user):
    groups = {}
    for conversation in conversations:
        participant = conversation.seller if conversation.buyer_id == user.id else conversation.buyer
        group = groups.setdefault(participant.id, {'participant': participant, 'conversations': [], 'unread_count': 0})
        group['conversations'].append(conversation)
        group['unread_count'] += conversation.unread_count
    return sorted(groups.values(), key=lambda group: group['conversations'][0].updated_at, reverse=True)


def _visible_unread_count_annotation(user):
    return Count(
        'messages',
        filter=(Q(messages__is_read=False, messages__is_deleted=False) & ~Q(messages__sender=user)
                & (Q(cleared_at__isnull=True) | Q(cleared_through_id__isnull=True) | Q(messages__pk__gt=F('cleared_through_id')))),
    )


def _visible_active_conversations_for(user):
    """Active threads for one participant, respecting that participant's clear cutoff."""
    latest_messages = Message.objects.filter(conversation=OuterRef('pk')).order_by('-pk')
    state = ConversationUserState.objects.filter(conversation=OuterRef('pk'), user=user)
    return Conversation.objects.filter(Q(buyer=user) | Q(seller=user)).annotate(
        latest_message_id=Subquery(latest_messages.values('pk')[:1]),
        cleared_through_id=Subquery(state.values('cleared_through_message_id')[:1]),
        cleared_at=Subquery(state.values('cleared_at')[:1]),
    ).filter(latest_message_id__isnull=False).filter(
        Q(cleared_at__isnull=True) | Q(cleared_through_id__isnull=True) | Q(latest_message_id__gt=F('cleared_through_id')),
    )


def _conversation_summary_groups(user):
    latest_messages = Message.objects.filter(conversation=OuterRef('pk')).order_by('-pk')
    conversations = _visible_active_conversations_for(user).select_related('buyer', 'seller', 'listing').prefetch_related('listing__listing_images').annotate(
        unread_count=_visible_unread_count_annotation(user),
        latest_body=Subquery(latest_messages.values('body')[:1]),
        latest_attachment=Subquery(latest_messages.values('attachment')[:1]),
        latest_deleted=Subquery(latest_messages.values('is_deleted')[:1]),
    ).order_by('-updated_at')
    groups = []
    for group in _conversation_groups(conversations, user):
        conversations = []
        for conversation in group['conversations']:
            if conversation.latest_deleted:
                preview = 'Message deleted'
            elif conversation.latest_body:
                preview = conversation.latest_body.replace('\n', ' ').strip()[:100]
            elif conversation.latest_attachment:
                preview = 'Sent a photo' if str(conversation.latest_attachment).lower().endswith(('.gif', '.jpeg', '.jpg', '.png', '.webp')) else 'Sent an attachment'
            else:
                preview = 'No messages yet'
            conversations.append({
                'id': conversation.pk,
                'url': reverse('dashboard:conversation', args=[conversation.pk]),
                'listing_title': conversation.listing.title,
                'listing_image': conversation.listing.conversation_image_url,
                'unread_count': conversation.unread_count,
                'updated_at': conversation.updated_at.isoformat(),
                'preview': preview,
            })
        groups.append({
            'participant': {
                'id': group['participant'].pk,
                'name': f"{group['participant'].first_name} {group['participant'].last_name}".strip() or group['participant'].email,
                'avatar': group['participant'].avatar_url,
            },
            'unread_count': group['unread_count'],
            'conversations': conversations,
        })
    return groups


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
        if listing.conversations.exists():
            # Conversation.listing intentionally remains a required foreign key.
            # Archive instead of cascading away a buyer and seller's history.
            listing.status = Listing.Status.ARCHIVED
            listing.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'The listing was archived so its message history remains available.')
        else:
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
    if request.method == 'POST' and (request.POST.get('body', '').strip() or request.FILES.getlist('attachments')):
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = _save_message_with_attachments(form, conversation, request.user, request.FILES)
            conversation.save(update_fields=['updated_at'])
            messages.success(request, 'Message sent to the seller.')
        else:
            messages.error(request, 'Your message could not be sent. Please try again.')
    return redirect('dashboard:conversation', conversation_id=conversation.pk)


@login_required
def conversation_list(request):
    conversations = _visible_active_conversations_for(request.user).select_related('buyer', 'seller', 'listing').prefetch_related('listing__listing_images').annotate(
        unread_count=_visible_unread_count_annotation(request.user),
    )
    return render(
        request,
        'messaging/messaging.html',
        {'conversation_groups': _conversation_groups(conversations, request.user), 'categories': _category_context()},
    )


@login_required
@never_cache
def conversation_sidebar_state(request):
    groups = _conversation_summary_groups(request.user)
    return JsonResponse({
        'groups': groups,
        # The sidebar groups are already calculated from the current user's
        # visibility cutoff, so this is the authoritative total for this poll.
        'total_unread_count': sum(group['unread_count'] for group in groups),
    })


def _search_snippet(body, query, radius=48):
    normalized = ' '.join((body or '').split())
    match_start = normalized.lower().find(query.lower())
    if match_start < 0:
        return normalized[: radius * 2]
    start = max(0, match_start - radius)
    end = min(len(normalized), match_start + len(query) + radius)
    return f"{'…' if start else ''}{normalized[start:end]}{'…' if end < len(normalized) else ''}"


@login_required
@never_cache
def conversation_message_search(request, conversation_id):
    query = (request.GET.get('q') or '').strip()
    if len(query) > 100:
        return JsonResponse({'error': 'Search query is too long.'}, status=400)
    conversation = get_object_or_404(
        Conversation.objects.filter(Q(buyer=request.user) | Q(seller=request.user)),
        pk=conversation_id,
    )
    if len(query) < 2:
        return JsonResponse({'query': query, 'count': 0, 'results': []})
    matches = _visible_messages_for_user(conversation, request.user).filter(
        is_deleted=False,
        body__icontains=query,
    ).exclude(body='').select_related('sender').order_by('-created_at', '-pk')
    count = matches.count()
    results = []
    for message in matches[:25]:
        sender_name = f'{message.sender.first_name} {message.sender.last_name}'.strip() or message.sender.email
        results.append({
            'id': message.pk,
            'sender_name': sender_name,
            'sender_avatar_url': message.sender.avatar_url,
            'snippet': _search_snippet(message.body, query),
            'created_at': message.created_at.isoformat(),
        })
    return JsonResponse({
        'query': query,
        'count': count,
        'results': results,
        'match_ids': list(matches.values_list('pk', flat=True)),
        'has_more': count > len(results),
    })


@login_required
@never_cache
def conversation_search(request):
    query = (request.GET.get('q') or '').strip()
    if len(query) > 100:
        return JsonResponse({'error': 'Search query is too long.'}, status=400)
    if len(query) < 2:
        return JsonResponse({'query': query, 'results': []})
    participant_match = (
        (Q(buyer=request.user) & (Q(seller__first_name__icontains=query) | Q(seller__last_name__icontains=query)))
        | (Q(seller=request.user) & (Q(buyer__first_name__icontains=query) | Q(buyer__last_name__icontains=query)))
    )
    conversations = _visible_active_conversations_for(request.user).filter(
        Q(listing__title__icontains=query) | participant_match,
    ).select_related('buyer', 'seller', 'listing').annotate(
        unread_count=_visible_unread_count_annotation(request.user),
    ).order_by('-updated_at')[:30]
    results = []
    for conversation in conversations:
        participant = conversation.seller if conversation.buyer_id == request.user.id else conversation.buyer
        results.append({
            'id': conversation.pk,
            'url': reverse('dashboard:conversation', args=[conversation.pk]),
            'participant_name': f'{participant.first_name} {participant.last_name}'.strip() or participant.email,
            'participant_avatar_url': participant.avatar_url,
            'listing_title': conversation.listing.title,
            'listing_image_url': conversation.listing.conversation_image_url,
            'unread_count': conversation.unread_count,
        })
    return JsonResponse({'query': query, 'results': results, 'has_more': len(results) == 30})


@login_required
@never_cache
def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(
        Conversation.objects.select_related('buyer', 'seller', 'listing').prefetch_related('listing__listing_images'),
        Q(buyer=request.user) | Q(seller=request.user),
        pk=conversation_id,
    )
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = _save_message_with_attachments(form, conversation, request.user, request.FILES)
            conversation.save(update_fields=['updated_at'])
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse(_message_payload(message))
            messages.success(request, 'Message sent.')
            return redirect('dashboard:conversation', conversation_id=conversation.pk)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Your message could not be sent. Please check the message and attachment.'}, status=400)
        messages.error(request, 'Your message could not be sent. Please try again.')
    else:
        form = MessageForm()
    participant = conversation.seller if conversation.buyer_id == request.user.id else conversation.buyer
    media, files, links = _conversation_resources(conversation, request.user)
    visible_messages = _visible_messages_for_user(conversation, request.user).select_related('sender').prefetch_related('attachments')
    visible_messages.exclude(sender=request.user).filter(is_read=False).update(is_read=True)
    return render(
        request,
        'messaging/messaging.html',
        {
            'conversation': conversation,
            'selected_conversation': conversation,
            'conversation_messages': visible_messages,
            'message_form': form,
            'conversation_groups': _conversation_groups(_visible_active_conversations_for(request.user).select_related('buyer', 'seller', 'listing').prefetch_related('listing__listing_images').annotate(
                unread_count=_visible_unread_count_annotation(request.user)
            ), request.user),
            'categories': _category_context(),
            'chat_participant': participant,
            'chat_media': media,
            'chat_files': files,
            'chat_links': links,
            'message_revision_cursor': _latest_visible_revision_id(conversation, request.user),
        },
    )


@login_required
@never_cache
def conversation_new_messages(request, conversation_id):
    """Return new messages and changed existing messages for one active chat."""
    conversation = get_object_or_404(
        Conversation.objects.filter(Q(buyer=request.user) | Q(seller=request.user)),
        pk=conversation_id,
    )
    try:
        after_id = max(int(request.GET.get('after', 0)), 0)
    except (TypeError, ValueError):
        after_id = 0

    cutoff = _clear_cutoff_for(conversation, request.user) or 0
    after_id = max(after_id, cutoff)
    try:
        revision_after = max(int(request.GET.get('revision_after', 0)), 0)
    except (TypeError, ValueError):
        revision_after = 0
    new_messages = list(conversation.messages.filter(pk__gt=after_id).select_related('sender').prefetch_related('attachments'))
    conversation.messages.filter(
        pk__in=[message.pk for message in new_messages], is_read=False,
    ).exclude(sender=request.user).update(is_read=True)
    deleted_messages = _visible_messages_for_user(conversation, request.user).filter(is_deleted=True).select_related('sender')
    revisions = MessageRevision.objects.filter(
        message__conversation=conversation,
        message__is_deleted=False,
        pk__gt=revision_after,
    )
    if cutoff:
        revisions = revisions.filter(message_id__gt=cutoff)
    revisions = list(revisions.select_related('message__sender').prefetch_related('message__attachments').order_by('pk'))
    # One message may have changed several times between polls. Return its
    # current state once, while the highest revision ID remains a durable,
    # server-issued cursor for the next poll.
    changed_messages = {}
    for revision in revisions:
        # A message created after ``after_id`` is already returned with its
        # latest body in ``messages``. It must not be patched as a second
        # change event during the same response.
        if revision.message_id <= after_id:
            changed_messages[revision.message_id] = revision.message
    revision_cursor = revisions[-1].pk if revisions else revision_after
    return JsonResponse({
        'messages': [_message_payload(message) for message in new_messages],
        'deleted_messages': [_message_payload(message) for message in deleted_messages],
        'updated_messages': [_message_payload(message) for message in changed_messages.values()],
        'revision_cursor': revision_cursor,
        'other_user_typing': _other_participant_typing(conversation, request.user),
    })


@login_required
def conversation_typing(request, conversation_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Typing updates must use POST.'}, status=405)
    conversation = get_object_or_404(Conversation.objects.filter(Q(buyer=request.user) | Q(seller=request.user)), pk=conversation_id)
    raw_sequence = request.POST.get('sequence', 0)
    try:
        sequence = max(int(raw_sequence), 0)
    except (TypeError, ValueError):
        logger.warning(
            '[TYPE-SERVER-WRITE] conversation=%s user=%s typing=%s incoming_sequence=%s accepted=false reason=invalid_sequence now=%s',
            conversation.pk, request.user.pk, request.POST.get('typing') == '1', raw_sequence, timezone.now().isoformat(),
        )
        return JsonResponse({'error': 'A valid typing sequence is required.'}, status=400)
    requested_typing = request.POST.get('typing') == '1'
    raw_client_session_id = request.POST.get('client_session_id', '')
    try:
        client_session_id = str(uuid.UUID(raw_client_session_id))
    except (AttributeError, TypeError, ValueError):
        logger.warning(
            '[TYPE-SERVER-WRITE] conversation=%s user=%s typing=%s incoming_sequence=%s accepted=false reason=invalid_client_session',
            conversation.pk, request.user.pk, requested_typing, sequence,
        )
        return JsonResponse({'error': 'A valid typing client session is required.'}, status=400)
    with transaction.atomic():
        state, _ = ConversationTypingState.objects.select_for_update().get_or_create(
            conversation=conversation,
            user=request.user,
        )
        previous_sequence = state.last_sequence
        previous_client_session_id = state.client_session_id
        last_activity_before = state.last_activity_at
        is_new_client_session = client_session_id != state.client_session_id
        # A browser serializes requests within a page session. Page-local
        # sequences intentionally restart after a reload, so a new validated
        # client session replaces the previous ordering namespace.
        accepted = is_new_client_session or sequence > state.last_sequence
        if accepted:
            state.client_session_id = client_session_id
            state.last_sequence = sequence
            state.last_activity_at = timezone.now() if requested_typing else None
            state.save(update_fields=['client_session_id', 'last_sequence', 'last_activity_at'])
        logger.warning(
            '[TYPE-SERVER-WRITE] conversation=%s user=%s typing=%s client_session=%s previous_client_session=%s incoming_sequence=%s previous_sequence=%s accepted=%s reason=%s last_activity_before=%s last_activity_after=%s now=%s',
            conversation.pk, request.user.pk, requested_typing,
            client_session_id, previous_client_session_id or 'NULL', sequence, previous_sequence,
            accepted, 'new_client_session' if is_new_client_session else ('accepted' if accepted else 'stale_sequence'),
            last_activity_before.isoformat() if last_activity_before else 'NULL',
            state.last_activity_at.isoformat() if state.last_activity_at else 'NULL', timezone.now().isoformat(),
        )
    return JsonResponse({'ok': True, 'sequence': sequence})


@login_required
def delete_message(request, conversation_id, message_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Delete requests must use POST.'}, status=405)
    conversation = get_object_or_404(
        Conversation.objects.filter(Q(buyer=request.user) | Q(seller=request.user)),
        pk=conversation_id,
    )
    message = get_object_or_404(
        Message.objects.select_related('sender'), pk=message_id, conversation=conversation,
    )
    if message.sender_id != request.user.id:
        return HttpResponseForbidden('You can only unsend your own messages.')
    if not message.is_deleted:
        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
        conversation.save(update_fields=['updated_at'])
    return JsonResponse(_message_payload(message))


@login_required
def clear_conversation(request, conversation_id):
    """Clear only request.user's local history; shared messages are never deleted."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Delete requests must use POST.'}, status=405)
    conversation = get_object_or_404(
        Conversation.objects.filter(Q(buyer=request.user) | Q(seller=request.user)), pk=conversation_id,
    )
    with transaction.atomic():
        latest_message_id = conversation.messages.order_by('-pk').values_list('pk', flat=True).first()
        state, _ = ConversationUserState.objects.select_for_update().get_or_create(
            conversation=conversation, user=request.user,
        )
        state.cleared_through_message_id = latest_message_id
        state.cleared_at = timezone.now()
        state.save(update_fields=['cleared_through_message', 'cleared_at', 'updated_at'])
    return JsonResponse({'conversation_id': conversation.pk, 'cleared_through_message_id': latest_message_id})


@login_required
def edit_message(request, conversation_id, message_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Edit requests must use POST.'}, status=405)
    conversation = get_object_or_404(Conversation.objects.filter(Q(buyer=request.user) | Q(seller=request.user)), pk=conversation_id)
    message = get_object_or_404(Message.objects.select_related('sender'), pk=message_id, conversation=conversation)
    if message.sender_id != request.user.id:
        return HttpResponseForbidden('You can only edit your own messages.')
    if message.is_deleted:
        return JsonResponse({'error': 'Deleted messages cannot be edited.'}, status=400)
    body = (request.POST.get('body') or '').strip()
    if not body or len(body) > 2000:
        return JsonResponse({'error': 'Message text must be between 1 and 2000 characters.'}, status=400)
    revision = None
    if body != message.body:
        with transaction.atomic():
            revision = MessageRevision.objects.create(message=message, body=message.body, editor=request.user)
            message.body, message.is_edited, message.edited_at = body, True, timezone.now()
            message.save(update_fields=['body', 'is_edited', 'edited_at', 'updated_at'])
    payload = _message_payload(message)
    if revision:
        payload['revision_cursor'] = revision.pk
    return JsonResponse(payload)


@login_required
def message_history(request, conversation_id, message_id):
    conversation = get_object_or_404(Conversation.objects.filter(Q(buyer=request.user) | Q(seller=request.user)), pk=conversation_id)
    message = get_object_or_404(_visible_messages_for_user(conversation, request.user).prefetch_related('revisions'), pk=message_id, is_deleted=False)
    return JsonResponse({'history': [revision.body for revision in message.revisions.all()] + [message.body]})


@login_required
def link_preview(request):
    preview = get_link_preview(request.GET.get('url', ''))
    return JsonResponse({'preview': preview})


@login_required
@never_cache
def conversation_links(request, conversation_id):
    """Return current, non-deleted shared links for one authorised conversation."""
    conversation = get_object_or_404(
        Conversation.objects.filter(Q(buyer=request.user) | Q(seller=request.user)),
        pk=conversation_id,
    )
    links = []
    for message in _visible_messages_for_user(conversation, request.user).filter(is_deleted=False).order_by('created_at', 'pk'):
        links.extend(extract_meaningful_message_urls(message.body))
    return JsonResponse({
        'links': [_link_card(link, get_link_preview(link)) for link in dict.fromkeys(links)],
    })


@login_required
@never_cache
def unread_message_count(request):
    try:
        after_id = max(int(request.GET.get('after', 0)), 0)
    except (TypeError, ValueError):
        after_id = 0
    incoming = _visible_participant_messages_for(request.user).filter(
        is_read=False, is_deleted=False, pk__gt=after_id,
    ).exclude(sender=request.user).select_related('sender', 'conversation__listing').order_by('pk')[:20]
    return JsonResponse({
        'unread_count': _unread_message_count(request.user),
        'latest_message_id': _visible_participant_messages_for(request.user).exclude(sender=request.user).order_by('-pk').values_list('pk', flat=True).first() or 0,
        'new_messages': [{
            'id': message.pk, 'conversation_id': message.conversation_id,
            'sender_name': f'{message.sender.first_name} {message.sender.last_name}'.strip() or message.sender.email,
            'listing_title': message.conversation.listing.title, 'preview': message.body[:100],
        } for message in incoming],
    })
