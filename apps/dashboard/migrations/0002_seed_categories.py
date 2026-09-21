from django.db import migrations
from django.utils.text import slugify


CATEGORIES = [
    'Textbooks',
    'Electronics',
    'Uniforms',
    'Dorm essentials',
    'Services',
]


def seed_categories(apps, schema_editor):
    Category = apps.get_model('dashboard', 'Category')

    for name in CATEGORIES:
        Category.objects.get_or_create(
            slug=slugify(name),
            defaults={'name': name},
        )


def remove_categories(apps, schema_editor):
    Category = apps.get_model('dashboard', 'Category')

    Category.objects.filter(
        slug__in=[slugify(name) for name in CATEGORIES]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_categories, remove_categories),
    ]
