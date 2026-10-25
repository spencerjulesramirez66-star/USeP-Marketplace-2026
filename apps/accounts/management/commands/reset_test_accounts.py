from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Resets account passwords for development testing.'

    def add_arguments(self, parser):
        parser.add_argument('--password', default='TestPassword123!')
        parser.add_argument('--confirm', action='store_true')
        parser.add_argument('--restore-deleted', action='store_true')
        parser.add_argument('--exclude-admins', action='store_true')

    def handle(self, *args, **options):
        settings_module = settings.SETTINGS_MODULE
        database = settings.DATABASES['default']
        self.stdout.write(f'Active settings: {settings_module}')
        self.stdout.write(f'Database NAME: {database.get("NAME")}')
        self.stdout.write(f'Database HOST: {database.get("HOST")}')

        if settings_module != 'config.settings.development':
            self.stdout.write('Accounts that will be affected: not queried.')
            raise CommandError('Refusing to run unless development settings are active.')

        accounts = User.objects.all()
        admin_accounts = accounts.filter(Q(is_superuser=True) | Q(role='ADMIN'))
        if options['exclude_admins']:
            accounts = accounts.exclude(Q(is_superuser=True) | Q(role='ADMIN'))

        account_count = accounts.count()
        inactive_count = accounts.filter(is_active=False).count()
        deleted_count = accounts.filter(is_deleted=True).count()
        admin_count = admin_accounts.filter(pk__in=accounts.values('pk')).count()
        excluded_admin_count = admin_accounts.count() - admin_count
        self.stdout.write(f'Accounts that will be affected: {account_count}')

        if not options['confirm']:
            self.stdout.write('Dry run only; no accounts were changed.')
            self.stdout.write(f'Admins in scope: {admin_count}')
            if options['exclude_admins']:
                self.stdout.write(f'Admins skipped: {excluded_admin_count}')
            self.stdout.write(f'Inactive accounts in scope (left unchanged): {inactive_count}')
            self.stdout.write(
                f'Soft-deleted accounts in scope '
                f'({"will be restored" if options["restore_deleted"] else "left unchanged"}): '
                f'{deleted_count}'
            )
            return

        updated_count = 0
        with transaction.atomic():
            for user in accounts:
                user.set_password(options['password'])
                user.email_verified = True
                user.is_first_login = False
                update_fields = ['password', 'email_verified', 'is_first_login']
                if options['restore_deleted'] and user.is_deleted:
                    user.is_deleted = False
                    user.deleted_at = None
                    update_fields.extend(['is_deleted', 'deleted_at'])
                # User.save() can implicitly change is_staff for admin-role accounts.
                super(User, user).save(update_fields=update_fields)
                updated_count += 1

        self.stdout.write(f'Total accounts updated: {updated_count}')
        self.stdout.write(f'Admins updated: {admin_count}')
        if options['exclude_admins']:
            self.stdout.write(f'Admins skipped: {excluded_admin_count}')
        self.stdout.write(f'Inactive accounts (left inactive): {inactive_count}')
        self.stdout.write(
            f'Soft-deleted accounts '
            f'({"restored" if options["restore_deleted"] else "left unchanged"}): '
            f'{deleted_count}'
        )
