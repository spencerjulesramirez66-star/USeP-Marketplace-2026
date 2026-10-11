from django.core.management.base import BaseCommand

from apps.dashboard.services.listing_lifecycle import archive_expired_recycled_listings


class Command(BaseCommand):
    help = 'Archives recycle-bin listings that have been recycled for 30 full days.'

    def handle(self, *args, **options):
        archived = archive_expired_recycled_listings()
        self.stdout.write(f'Archived {archived} listing(s).')
