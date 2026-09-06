from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.db import migrations


PASSWORD = 'TestPassword123!'

SELLERS = [
    {
        'email': 'maria.santos@usep.edu.ph',
        'first_name': 'Maria',
        'last_name': 'Santos',
        'contact_num': '09000000003',
        'listing': {
            'slug': 'maria-engineering-notes',
            'category': 'textbooks',
            'title': 'Engineering Mechanics Notes',
            'description': 'Organized review notes for engineering mechanics.',
            'price': Decimal('180.00'),
            'condition': 'Good condition',
            'location': 'Engineering building',
        },
    },
    {
        'email': 'juan.reyes@usep.edu.ph',
        'first_name': 'Juan',
        'last_name': 'Reyes',
        'contact_num': '09000000004',
        'listing': {
            'slug': 'juan-programming-book',
            'category': 'textbooks',
            'title': 'Python Programming Book',
            'description': 'Beginner-friendly Python reference book.',
            'price': Decimal('380.00'),
            'condition': 'Like new',
            'location': 'ICT building',
        },
    },
    {
        'email': 'elena.gutierrez@usep.edu.ph',
        'first_name': 'Elena',
        'last_name': 'Gutierrez',
        'contact_num': '09000000005',
        'listing': {
            'slug': 'elena-pe-uniform',
            'category': 'uniforms',
            'title': 'PE Uniform, Medium',
            'description': 'Clean campus PE uniform in medium size.',
            'price': Decimal('250.00'),
            'condition': 'Good condition',
            'location': 'Student center',
        },
    },
]


def seed_named_sellers(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Category = apps.get_model('dashboard', 'Category')
    Listing = apps.get_model('dashboard', 'Listing')

    test_seller = User.objects.filter(email='test.seller@usep.edu.ph').first()
    if test_seller:
        test_seller.first_name = 'Miguel'
        test_seller.last_name = 'Rivera'
        test_seller.is_seller = True
        test_seller.save(update_fields=['first_name', 'last_name', 'is_seller'])

    categories = {category.slug: category for category in Category.objects.all()}
    created_emails = []
    created_slugs = []

    for seller_data in SELLERS:
        seller, created = User.objects.get_or_create(
            email=seller_data['email'],
            defaults={
                'password': make_password(PASSWORD),
                'email_verified': True,
                'is_first_login': False,
                'first_name': seller_data['first_name'],
                'last_name': seller_data['last_name'],
                'contact_num': seller_data['contact_num'],
                'role': 'USER',
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
                'is_seller': True,
            },
        )
        listing_data = seller_data['listing']
        Listing.objects.get_or_create(
            slug=listing_data['slug'],
            defaults={
                'seller': seller,
                'category': categories[listing_data['category']],
                'title': listing_data['title'],
                'description': listing_data['description'],
                'price': listing_data['price'],
                'condition': listing_data['condition'],
                'location': listing_data['location'],
                'status': 'ACTIVE',
            },
        )
        if created:
            created_emails.append(seller_data['email'])
        created_slugs.append(listing_data['slug'])


def remove_named_sellers(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Listing = apps.get_model('dashboard', 'Listing')
    Listing.objects.filter(slug__in=[seller['listing']['slug'] for seller in SELLERS]).delete()
    User.objects.filter(email__in=[seller['email'] for seller in SELLERS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0005_emailotp_purpose'),
        ('dashboard', '0005_listingimage'),
    ]

    operations = [
        migrations.RunPython(seed_named_sellers, remove_named_sellers),
    ]
