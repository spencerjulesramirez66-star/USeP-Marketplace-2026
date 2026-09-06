from importlib import import_module

from django.db import migrations


def apply_profile_backfill(apps, schema_editor):
    normalize_profiles = import_module(
        'apps.accounts.migrations.0007_normalize_account_profiles'
    ).normalize_profiles
    normalize_profiles(apps, schema_editor)


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0007_normalize_account_profiles'),
    ]

    operations = [
        migrations.RunPython(apply_profile_backfill, migrations.RunPython.noop),
    ]