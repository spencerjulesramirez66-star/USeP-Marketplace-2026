from django.db import migrations


SELLER_EMAILS = [
    'test.seller@usep.edu.ph',
    'maria.santos@usep.edu.ph',
    'juan.reyes@usep.edu.ph',
    'elena.gutierrez@usep.edu.ph',
]


def mark_sellers(apps, schema_editor):
    # 0006 already gives each of these a SellerProfile; this just guarantees
    # it for any of these emails that predate that migration (get_or_create
    # makes it a no-op where 0006 already ran).
    User = apps.get_model('accounts', 'User')
    SellerProfile = apps.get_model('accounts', 'SellerProfile')
    for user in User.objects.filter(email__in=SELLER_EMAILS):
        SellerProfile.objects.get_or_create(user=user)


def unmark_sellers(apps, schema_editor):
    SellerProfile = apps.get_model('accounts', 'SellerProfile')
    SellerProfile.objects.filter(user__email__in=SELLER_EMAILS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0005_seller_profile_and_catalog_cleanup'),
        ('dashboard', '0006_seed_named_sellers'),
    ]

    operations = [
        migrations.RunPython(mark_sellers, unmark_sellers),
    ]