
from django.db import migrations
from django.contrib.auth.hashers import make_password
from django.db.models import Q


ADMIN_EMAIL = 'biratacador03202400139@usep.edu.ph'
ADMIN_CONTACT_NUM = '09913341553'


def seed_admin_user(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    db = schema_editor.connection.alias

    if User.objects.using(db).filter(
        Q(email=ADMIN_EMAIL) | Q(contact_num=ADMIN_CONTACT_NUM)
    ).exists():
        return

    User.objects.using(db).create(
        email=ADMIN_EMAIL,
        password=make_password(None),
        first_name='System',
        middle_name='',
        last_name='Administrator',
        contact_num=ADMIN_CONTACT_NUM,
        role='ADMIN',
        is_staff=True,
        is_superuser=True,
        is_active=True,
        email_verified=True,
        is_first_login=False,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_reconcile_user_soft_delete_columns'),
    ]

    operations = [
        migrations.RunPython(
            seed_admin_user,
            migrations.RunPython.noop,
        ),
    ]
