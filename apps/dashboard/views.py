from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.models import User

from .forms import ListingForm, MessageForm
from .models import Category, Conversation, Listing, ListingImage, Message, SavedItem


SELLERS = {
    1: {'name': 'Maria Santos', 'role': 'Teaching Staff', 'avatar': 'https://api.dicebear.com/7.x/avataaars/svg?seed=Maria'},
    2: {'name': 'Juan Reyes', 'role': 'Teaching Staff', 'avatar': 'https://api.dicebear.com/7.x/avataaars/svg?seed=Juan'},
    3: {'name': 'Mrs. Elena Gutierrez', 'role': 'Non-Teaching Staff', 'avatar': 'https://api.dicebear.com/7.x/avataaars/svg?seed=Elena'},
    4: {'name': 'Carlos Mendoza', 'role': 'Non-Teaching Staff', 'avatar': 'https://api.dicebear.com/7.x/avataaars/svg?seed=Carlos'},
    5: {'name': 'Alex Torres', 'role': 'Teaching Staff', 'avatar': 'https://api.dicebear.com/7.x/avataaars/svg?seed=Alex'},
    6: {'name': 'Dr. Patricia Lim', 'role': 'Teaching Staff', 'avatar': 'https://api.dicebear.com/7.x/avataaars/svg?seed=Patricia'},
}


def _normalize_seller_data(items):
    normalized = []
    for item in items:
        updated = dict(item)
        seller = SELLERS.get(item.get('seller_id'))
        if seller:
            updated['seller'] = seller['name']
            updated['seller_role'] = seller['role']
        normalized.append(updated)
    return normalized


FAKE_LISTINGS = [
    {
        'id': 1,
        'slug': 'engineering-mechanics-textbook',
        'title': 'Engineering Mechanics Textbook',
        'category': 'Textbooks',
        'price': 450,
        'price_label': '₱450',
        'condition': 'Good condition',
        'location': '3 mins away',
        'seller_id': 1,
        'seller': 'Maria Santos',
        'seller_role': 'Bachelor of Science in Agricultural and Biosystems Engineering',
        'views': 34,
        'image_url': 'https://placehold.co/640x480?text=Engineering+Mechanics+Textbook',
        'images': [
            'https://placehold.co/640x480?text=Engineering+Mechanics+Textbook+Front',
            'https://placehold.co/640x480?text=Engineering+Mechanics+Textbook+Inside',
            'https://placehold.co/640x480?text=Engineering+Mechanics+Textbook+Detail',
        ],
        'description': '4th edition textbook with minimal highlighting. All pages are intact and the cover is still in good shape.',
        'highlights': ['4th edition', 'Minimal notes', 'All pages intact'],
    },
    {
        'id': 2,
        'slug': 'scientific-calculator',
        'title': 'Scientific Calculator',
        'category': 'Electronics',
        'price': 900,
        'price_label': '₱900',
        'condition': 'Barely used',
        'location': '8 mins away',
        'seller_id': 2,
        'seller': 'Juan Reyes',
        'seller_role': 'Bachelor of Science in Information Technology',
        'views': 61,
        'image_url': 'https://placehold.co/640x480?text=Scientific+Calculator',
        'images': [
            'https://placehold.co/640x480?text=Scientific+Calculator+Front',
            'https://placehold.co/640x480?text=Scientific+Calculator+Side',
            'https://placehold.co/640x480?text=Scientific+Calculator+Case',
        ],
        'description': 'Casio fx-991 in excellent working condition, complete with original case and charging cable.',
        'highlights': ['Barely used', 'Original case included', 'Fully working'],
    },
    {
        'id': 3,
        'slug': 'pe-uniform-medium',
        'title': 'PE Uniform (Medium)',
        'category': 'Uniforms',
        'price': 250,
        'price_label': '₱250',
        'condition': 'Clean and wearable',
        'location': '5 mins away',
        'seller_id': 3,
        'seller': 'Mrs. Elena Gutierrez',
        'seller_role': 'Bachelor of Early Childhood Education',
        'views': 12,
        'image_url': 'https://placehold.co/640x480?text=PE+Uniform',
        'images': [
            'https://placehold.co/640x480?text=PE+Uniform+Front',
            'https://placehold.co/640x480?text=PE+Uniform+Back',
            'https://placehold.co/640x480?text=PE+Uniform+Fit',
        ],
        'description': 'Campus-ready PE uniform in good condition. Clean fit, easy to wash, and comfortable for daily use.',
        'highlights': ['Comfortable fit', 'Easy to wash', 'Campus-ready'],
    },
    {
        'id': 4,
        'slug': 'study-desk-lamp',
        'title': 'Study Desk Lamp',
        'category': 'Dorm essentials',
        'price': 1200,
        'price_label': '₱1,200',
        'condition': 'Excellent condition',
        'location': '11 mins away',
        'seller_id': 4,
        'seller': 'Carlos Mendoza',
        'seller_role': 'Bachelor of Elementary Education',
        'views': 48,
        'image_url': 'https://placehold.co/640x480?text=Desk+Lamp',
        'images': [
            'https://placehold.co/640x480?text=Desk+Lamp+Front',
            'https://placehold.co/640x480?text=Desk+Lamp+Glow',
            'https://placehold.co/640x480?text=Desk+Lamp+Side',
        ],
        'description': 'Adjustable LED desk lamp with soft lighting for late-night study sessions and reading.',
        'highlights': ['Adjustable brightness', 'LED lighting', 'Perfect for dorm rooms'],
    },
    {
        'id': 5,
        'slug': 'mobile-wifi-device',
        'title': 'Mobile Wi-Fi Device',
        'category': 'Electronics',
        'price': 600,
        'price_label': '₱600',
        'condition': 'Good condition',
        'location': '10 mins away',
        'seller_id': 5,
        'seller': 'Alex Torres',
        'seller_role': 'Bachelor of Secondary Education – English',
        'views': 27,
        'image_url': 'https://placehold.co/640x480?text=Mobile+WiFi',
        'images': [
            'https://placehold.co/640x480?text=Mobile+WiFi+Front',
            'https://placehold.co/640x480?text=Mobile+WiFi+Display',
            'https://placehold.co/640x480?text=Mobile+WiFi+Setup',
        ],
        'description': 'Portable internet device for travel and dorm use, tested and ready to connect with campus activities.',
        'highlights': ['Portable', 'Ready to use', 'Great for dorm internet'],
    },
    {
        'id': 6,
        'slug': 'resume-editing-service',
        'title': 'Resume Editing Service',
        'category': 'Services',
        'price': 250,
        'price_label': '₱250/hr',
        'condition': 'Available this week',
        'location': '1 day lead time',
        'seller_id': 6,
        'seller': 'Dr. Patricia Lim',
        'seller_role': 'Bachelor of Secondary Education – Filipino',
        'views': 19,
        'image_url': 'https://placehold.co/640x480?text=Resume+Editing+Service',
        'images': [
            'https://placehold.co/640x480?text=Resume+Editing+Service+Cover',
            'https://placehold.co/640x480?text=Resume+Editing+Service+Mockup',
            'https://placehold.co/640x480?text=Resume+Editing+Service+Checklist',
        ],
        'description': 'Professional resume polishing and internship application support for students seeking internships or jobs.',
        'highlights': ['CV review', 'ATS-friendly format', 'Fast turnaround'],
    },
    {
        'id': 7,
        'slug': 'calculus-textbook',
        'title': 'Calculus Textbook (Stewart)',
        'category': 'Textbooks',
        'price': 550,
        'price_label': '₱550',
        'condition': 'Like new',
        'location': '3 mins away',
        'seller_id': 1,
        'seller': 'Maria Santos',
        'seller_role': 'Bachelor of Science in Agricultural and Biosystems Engineering',
        'views': 28,
        'image_url': 'https://placehold.co/640x480?text=Calculus+Textbook',
        'images': [
            'https://placehold.co/640x480?text=Calculus+Textbook+Cover',
            'https://placehold.co/640x480?text=Calculus+Textbook+Inside',
        ],
        'description': 'Early Transcendentals edition. Used for only one semester, practically new.',
        'highlights': ['Early Transcendentals', 'One semester use', 'Clean pages'],
    },
    {
        'id': 8,
        'slug': 'programming-book-python',
        'title': 'Python Programming Book',
        'category': 'Textbooks',
        'price': 380,
        'price_label': '₱380',
        'condition': 'Good',
        'location': '8 mins away',
        'seller_id': 2,
        'seller': 'Juan Reyes',
        'seller_role': 'Bachelor of Science in Information Technology',
        'views': 45,
        'image_url': 'https://placehold.co/640x480?text=Python+Programming',
        'images': [
            'https://placehold.co/640x480?text=Python+Programming+Cover',
            'https://placehold.co/640x480?text=Python+Programming+Pages',
        ],
        'description': 'Complete guide to Python programming. Great for beginners and intermediate programmers.',
        'highlights': ['Python 3', 'Practical examples', 'Exercise solutions included'],
    },
    {
        'id': 9,
        'slug': 'mechanical-pencil-set',
        'title': 'Mechanical Pencil Set',
        'category': 'Electronics',
        'price': 350,
        'price_label': '₱350',
        'condition': 'New',
        'location': '8 mins away',
        'seller_id': 2,
        'seller': 'Juan Reyes',
        'seller_role': 'Bachelor of Science in Information Technology',
        'views': 33,
        'image_url': 'https://placehold.co/640x480?text=Mechanical+Pencils',
        'images': [
            'https://placehold.co/640x480?text=Mechanical+Pencils+Set',
            'https://placehold.co/640x480?text=Mechanical+Pencils+Detail',
        ],
        'description': 'High-quality mechanical pencil set with extra leads. Perfect for engineering and technical drawing.',
        'highlights': ['5 pencils', 'Extra leads included', 'Precision tips'],
    },
    {
        'id': 10,
        'slug': 'pe-uniform-large',
        'title': 'PE Uniform (Large)',
        'category': 'Uniforms',
        'price': 250,
        'price_label': '₱250',
        'condition': 'New',
        'location': '5 mins away',
        'seller_id': 3,
        'seller': 'Mrs. Elena Gutierrez',
        'seller_role': 'Bachelor of Early Childhood Education',
        'views': 19,
        'image_url': 'https://placehold.co/640x480?text=PE+Uniform+Large',
        'images': [
            'https://placehold.co/640x480?text=PE+Uniform+Large+Front',
            'https://placehold.co/640x480?text=PE+Uniform+Large+Back',
        ],
        'description': 'Brand new PE uniform in size large. Never worn. Perfect condition.',
        'highlights': ['New', 'Size Large', 'Official USeP design'],
    },
    {
        'id': 11,
        'slug': 'monitor-lamp',
        'title': 'Monitor Lamp (USB)',
        'category': 'Dorm essentials',
        'price': 650,
        'price_label': '₱650',
        'condition': 'Good',
        'location': '11 mins away',
        'seller_id': 4,
        'seller': 'Carlos Mendoza',
        'seller_role': 'Bachelor of Elementary Education',
        'views': 37,
        'image_url': 'https://placehold.co/640x480?text=Monitor+Lamp',
        'images': [
            'https://placehold.co/640x480?text=Monitor+Lamp+Front',
            'https://placehold.co/640x480?text=Monitor+Lamp+Setup',
        ],
        'description': 'USB-powered monitor lamp. Reduces screen glare and eye strain during long study sessions.',
        'highlights': ['USB powered', 'Reduces glare', 'Adjustable brightness'],
    },
    {
        'id': 12,
        'slug': 'usb-charger-cable',
        'title': 'USB-C Multi-Charger',
        'category': 'Electronics',
        'price': 450,
        'price_label': '₱450',
        'condition': 'New',
        'location': '10 mins away',
        'seller_id': 5,
        'seller': 'Alex Torres',
        'seller_role': 'Bachelor of Secondary Education – English',
        'views': 52,
        'image_url': 'https://placehold.co/640x480?text=USB+Charger',
        'images': [
            'https://placehold.co/640x480?text=USB+Charger+Front',
            'https://placehold.co/640x480?text=USB+Charger+Cables',
        ],
        'description': 'Compact multi-port USB-C charger that powers multiple devices simultaneously.',
        'highlights': ['4 ports', 'Fast charging', 'Compact design'],
    },
    {
        'id': 13,
        'slug': 'career-coaching-session',
        'title': 'Career Coaching Session',
        'category': 'Services',
        'price': 500,
        'price_label': '₱500/session',
        'condition': 'Available',
        'location': '1-2 days',
        'seller_id': 6,
        'seller': 'Dr. Patricia Lim',
        'seller_role': 'Bachelor of Secondary Education – Filipino',
        'views': 24,
        'image_url': 'https://placehold.co/640x480?text=Career+Coaching',
        'images': [
            'https://placehold.co/640x480?text=Career+Coaching+Session',
        ],
        'description': '1-hour personalized career guidance and mentorship session. Help with internship prep and career planning.',
        'highlights': ['1-hour session', 'Personalized', 'Expert guidance'],
    },
]


BUYER_CATEGORIES = [
    {'label': 'All items', 'slug': 'all'},
    {'label': 'Textbooks', 'slug': 'textbooks'},
    {'label': 'Electronics', 'slug': 'electronics'},
    {'label': 'Uniforms', 'slug': 'uniforms'},
    {'label': 'Dorm essentials', 'slug': 'dorm-essentials'},
    {'label': 'Services', 'slug': 'services'},
]


def _build_category_options():
    counts = {'all': len(FAKE_LISTINGS)}
    for item in FAKE_LISTINGS:
        slug = item['category'].lower().replace(' ', '-')
        counts[slug] = counts.get(slug, 0) + 1

    categories = []
    for category in BUYER_CATEGORIES:
        categories.append({
            'label': category['label'],
            'slug': category['slug'],
            'count': counts.get(category['slug'], 0),
        })

    return categories


def _filter_listings(query=None, category='all'):
    filtered = list(FAKE_LISTINGS)
    query_text = (query or '').strip().lower()
    category_slug = (category or 'all').strip().lower()

    if category_slug != 'all':
        filtered = [
            item for item in filtered
            if item['category'].lower().replace(' ', '-') == category_slug
            or item['category'].lower() == category_slug
        ]

    if query_text:
        filtered = [
            item for item in filtered
            if query_text in item['title'].lower()
            or query_text in item['category'].lower()
            or query_text in item['description'].lower()
        ]

    return filtered


# Create your views here.
def setup_seller_dashboard(request):
    return render(request, 'seller/seller-dashboard.html')


def setup_buyer_dashboard(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', 'all')
    seller_id = request.GET.get('seller')
    items = _filter_listings(query=query, category=category)
    seller_profile = None

    if seller_id:
        try:
            seller_id_int = int(seller_id)
            seller_profile = SELLERS.get(seller_id_int, {})
            items = [item for item in items if item.get('seller_id') == seller_id_int]
        except (TypeError, ValueError):
            pass

    items = _normalize_seller_data(items)
    categories = _build_category_options()

    return render(
        request,
        'buyer/buyer-dashboard.html',
        {
            'items': items,
            'categories': categories,
            'selected_category': category,
            'query': query,
            'category_count': len(items),
            'seller_filter': seller_id,
            'seller_profile': seller_profile,
        }
    )


def setup_buyer_item_detail(request, item_slug):
    item = next((listing for listing in FAKE_LISTINGS if listing['slug'] == item_slug), None)
    if not item:
        raise Http404('Listing not found.')

    seller_id = item.get('seller_id')
    seller_info = SELLERS.get(seller_id, {})
    item = dict(item)
    item['seller'] = seller_info.get('name', item.get('seller'))
    item['seller_role'] = seller_info.get('role', item.get('seller_role'))

    other_products = [
        p for p in FAKE_LISTINGS
        if p.get('seller_id') == seller_id and p['slug'] != item_slug
    ]
    other_products = _normalize_seller_data(other_products)

    return render(
        request,
        'buyer/buyer-detail.html',
        {
            'item': item,
            'seller_info': seller_info,
            'other_products': other_products,
            'categories': BUYER_CATEGORIES,
            'selected_category': item['category'].lower().replace(' ', '-'),
            'query': request.GET.get('q', ''),
        }
    )


def setup_buyer_cart(request):
    return render(request, 'buyer/buyer-cart.html')


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
        form.save()
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

    return render(
        request,
        'buyer/buyer-dashboard.html',
        {
            'items': listings,
            'categories': _category_context(),
            'selected_category': category_slug,
            'query': query,
            'category_count': listings.count(),
            'seller_filter': seller_id,
            'seller_profile': seller_profile,
        },
    )


def setup_buyer_item_detail(request, item_slug):
    listing = get_object_or_404(
        Listing.objects.select_related('seller', 'category'),
        slug=item_slug,
    )
    saved_by_request_user = request.user.is_authenticated and SavedItem.objects.filter(
        buyer=request.user,
        listing=listing,
    ).exists()
    if listing.status not in (Listing.Status.ACTIVE, Listing.Status.RESERVED, Listing.Status.SOLD) and listing.seller != request.user and not saved_by_request_user:
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
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            conversation.save(update_fields=['updated_at'])
            messages.success(request, 'Message sent to the seller.')
    return redirect('dashboard:conversation', conversation_id=conversation.pk)


@login_required
def conversation_list(request):
    conversations = Conversation.objects.filter(
        Q(buyer=request.user) | Q(seller=request.user)
    ).select_related('buyer', 'seller', 'listing')
    return render(
        request,
        'dashboard/conversations.html',
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
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            conversation.save(update_fields=['updated_at'])
            return redirect('dashboard:conversation', conversation_id=conversation.pk)
    else:
        form = MessageForm()
    conversation.messages.exclude(sender=request.user).filter(is_read=False).update(is_read=True)
    return render(
        request,
        'dashboard/conversation-detail.html',
        {
            'conversation': conversation,
            'messages': conversation.messages.select_related('sender'),
            'message_form': form,
            'categories': _category_context(),
        },
    )