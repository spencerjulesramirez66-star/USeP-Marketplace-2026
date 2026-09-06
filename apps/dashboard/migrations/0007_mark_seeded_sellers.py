from django.db import migrations


SELLER_EMAILS = [
    'test.seller@usep.edu.ph',
    'maria.santos@usep.edu.ph',
    'juan.reyes@usep.edu.ph',
    'elena.gutierrez@usep.edu.ph',
]


def mark_sellers(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(email__in=SELLER_EMAILS).update(is_seller=True)


def unmark_sellers(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(email__in=SELLER_EMAILS).update(is_seller=False)


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0006_user_is_seller'),
        ('dashboard', '0006_seed_named_sellers'),
    ]

    operations = [
        migrations.RunPython(mark_sellers, unmark_sellers),
    ]
