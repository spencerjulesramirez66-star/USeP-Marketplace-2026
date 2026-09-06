from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.db import migrations
from django.utils.text import slugify


TEST_BUYER_EMAIL = 'test.buyer@usep.edu.ph'
TEST_SELLER_EMAIL = 'test.seller@usep.edu.ph'
TEST_PASSWORD = 'TestPassword123!'


def seed_test_marketplace_accounts(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Category = apps.get_model('dashboard', 'Category')
    Listing = apps.get_model('dashboard', 'Listing')

    categories = {
        category.slug: category
        for category in Category.objects.all()
    }

    buyer, _ = User.objects.get_or_create(
        email=TEST_BUYER_EMAIL,
        defaults={
            'password': make_password(TEST_PASSWORD),
            'email_verified': True,
            'is_first_login': False,
            'first_name': 'Test',
            'last_name': 'Buyer',
            'contact_num': '09000000001',
            'role': 'USER',
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
        },
    )

    seller, _ = User.objects.get_or_create(
        email=TEST_SELLER_EMAIL,
        defaults={
            'password': make_password(TEST_PASSWORD),
            'email_verified': True,
            'is_first_login': False,
            'first_name': 'Test',
            'last_name': 'Seller',
            'contact_num': '09000000002',
            'role': 'USER',
            'is_active': True,
            'is_staff': False,
            'is_superuser': False,
        },
    )

    listings = [
        {
            'slug': 'test-seller-calculus-book',
            'category': 'textbooks',
            'title': 'Calculus Textbook',
            'description': 'A clean calculus textbook ready for another student.',
            'price': Decimal('550.00'),
            'condition': 'Good condition',
            'location': 'USeP campus library',
        },
        {
            'slug': 'test-seller-usb-charger',
            'category': 'electronics',
            'title': 'USB-C Multi-Charger',
            'description': 'Compact charger with multiple ports for campus use.',
            'price': Decimal('450.00'),
            'condition': 'Like new',
            'location': 'USeP campus library',
        },
        {
            'slug': 'test-seller-study-lamp',
            'category': 'dorm-essentials',
            'title': 'Adjustable Study Lamp',
            'description': 'Desk lamp with adjustable brightness for late-night study.',
            'price': Decimal('650.00'),
            'condition': 'Barely used',
            'location': 'USeP campus library',
        },
        {
            'slug': 'test-seller-resume-help',
            'category': 'services',
            'title': 'Resume Review Service',
            'description': 'One-on-one resume review and improvement suggestions.',
            'price': Decimal('250.00'),
            'condition': 'Available by appointment',
            'location': 'Online or USeP campus',
        },
    ]

    for listing in listings:
        Listing.objects.get_or_create(
            slug=listing['slug'],
            defaults={
                'seller': seller,
                'category': categories[listing['category']],
                'title': listing['title'],
                'description': listing['description'],
                'price': listing['price'],
                'condition': listing['condition'],
                'location': listing['location'],
                'status': 'ACTIVE',
            },
        )


def remove_test_marketplace_accounts(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Listing = apps.get_model('dashboard', 'Listing')
    Listing.objects.filter(slug__startswith='test-seller-').delete()
    User.objects.filter(email__in=[TEST_BUYER_EMAIL, TEST_SELLER_EMAIL]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0005_emailotp_purpose'),
        ('dashboard', '0003_listing_image_urls'),
    ]

    operations = [
        migrations.RunPython(seed_test_marketplace_accounts, remove_test_marketplace_accounts),
    ]
