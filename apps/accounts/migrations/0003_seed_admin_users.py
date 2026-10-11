
from django.db import migrations
from django.contrib.auth.hashers import make_password


def seed_admin_user(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    db = schema_editor.connection.alias

    User.objects.using(db).create(
        email='sjlramirez03202400076@usep.edu.ph',
        password=make_password('TestPassword123!'),
        first_name='System',
        middle_name='',
        last_name='Administrator',
        contact_num='09323456709',
        role='ADMIN',
        is_staff=True,
        is_superuser=True,
        is_active=True,
        email_verified=True,
        is_first_login=False,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_database_seeder'),
    ]

    operations = [
        migrations.RunPython(
            seed_admin_user,
            migrations.RunPython.noop,
        ),
    ]
