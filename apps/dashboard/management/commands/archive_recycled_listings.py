from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.dashboard.models import Listing


class Command(BaseCommand):
    help = 'Archives recycle-bin listings whose configured retention period has expired.'

    def handle(self, *args, **options):
        if not settings.LISTING_RECYCLE_BIN_RETENTION_DAYS:
            self.stdout.write('Recycle-bin expiry is disabled.')
            return

        now = timezone.now()
        archived = Listing.objects.filter(
            lifecycle_state=Listing.Lifecycle.RECYCLE_BIN,
            recycle_bin_expires_at__lte=now,
        ).update(
            lifecycle_state=Listing.Lifecycle.ARCHIVED,
            archived_at=now,
        )
        self.stdout.write(f'Archived {archived} listing(s).')
