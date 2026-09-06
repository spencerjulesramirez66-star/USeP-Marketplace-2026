from decimal import Decimal

from django.db import migrations
from django.utils.text import slugify


CATEGORIES = [
    'Textbooks',
    'Electronics',
    'Uniforms',
    'Dorm essentials',
    'Services',
]


def seed_marketplace(apps, schema_editor):
    Category = apps.get_model('dashboard', 'Category')
    Listing = apps.get_model('dashboard', 'Listing')
    User = apps.get_model('accounts', 'User')

    categories = {}
    for name in CATEGORIES:
        category, _ = Category.objects.get_or_create(
            slug=slugify(name),
            defaults={'name': name},
        )
        categories[name] = category

    seller, created = User.objects.get_or_create(
        email='marketplace.demo@usep.edu.ph',
        defaults={
            'first_name': 'Marketplace',
            'last_name': 'Demo',
            'contact_num': '09000000000',
            'email_verified': True,
            'is_first_login': False,
        },
    )
    if created:
        seller.password = '!'
        seller.save(update_fields=['password'])

    Listing.objects.get_or_create(
        slug='engineering-mechanics-textbook',
        defaults={
            'seller': seller,
            'category': categories['Textbooks'],
            'title': 'Engineering Mechanics Textbook',
            'description': '4th edition textbook with minimal highlighting. All pages are intact.',
            'price': Decimal('450.00'),
            'condition': 'Good condition',
            'location': 'USeP campus',
            'status': 'ACTIVE',
        },
    )
    Listing.objects.get_or_create(
        slug='scientific-calculator',
        defaults={
            'seller': seller,
            'category': categories['Electronics'],
            'title': 'Scientific Calculator',
            'description': 'Casio fx-991 in excellent working condition.',
            'price': Decimal('900.00'),
            'condition': 'Barely used',
            'location': 'USeP campus',
            'status': 'ACTIVE',
        },
    )


def remove_marketplace_seed(apps, schema_editor):
    Listing = apps.get_model('dashboard', 'Listing')
    Category = apps.get_model('dashboard', 'Category')
    User = apps.get_model('accounts', 'User')
    Listing.objects.filter(slug__in=['engineering-mechanics-textbook', 'scientific-calculator']).delete()
    Category.objects.filter(slug__in=[slugify(name) for name in CATEGORIES]).delete()
    User.objects.filter(email='marketplace.demo@usep.edu.ph').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0005_emailotp_purpose'),
        ('dashboard', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_marketplace, remove_marketplace_seed),
    ]
