from collections import Counter
from datetime import datetime, time, timedelta, timezone as datetime_timezone
from decimal import Decimal
from io import StringIO
import os
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core import mail
from django.core.management import call_command, CommandError
from django.db.models.signals import post_save
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import SellerProfile, User
from apps.dashboard.management.commands.seed_demo_marketplace import (
    GENERIC_MESSAGE_BODY,
    SEED_DOMAIN,
)
from apps.dashboard.models import (
    Category,
    Listing,
    ListingReview,
    ListingReviewReply,
    ReviewNotification,
)
from apps.messaging import signals as message_signals
from apps.messaging.models import Conversation, Message, PurchaseRequest

LOCAL_TIMEZONE = ZoneInfo('Asia/Manila')
SEED_OPTIONS = {
    'transactions': 70,
    'days': 90,
    'seed': 2026,
    'password': 'TestPassword123!',
}


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SeedDemoMarketplaceCommandTests(TestCase):
    def setUp(self):
        self.categories = {
            category.slug: category
            for category in Category.objects.all()
        }
        self.assertTrue(self.categories)

    def create_non_seed_data(self):
        user = User.objects.create_user(
            email='preserved.user@example.test',
            password='Preserve-me-123!',
            first_name='Preserved',
            last_name='User',
            contact_num='09123456789',
            email_verified=True,
            is_first_login=False,
        )
        listing = Listing.objects.create(
            seller=user,
            category=self.categories['textbooks'],
            title='Non-seed listing remains',
            slug='non-seed-listing-remains',
            description='Do not modify.',
            price=Decimal('300.00'),
            condition='Good condition',
            location='USeP campus library',
        )
        review = ListingReview.objects.create(
            listing=listing,
            reviewer=user,
            rating=5,
            body='Non-seed review remains.',
        )
        return user, listing, review

    def run_seed(self, **kwargs):
        options = {**SEED_OPTIONS, **kwargs, 'confirm': True}
        output = StringIO()
        call_command('seed_demo_marketplace', stdout=output, **options)
        return output.getvalue()

    def test_seed_integrity_edge_cases_idempotence_and_safe_reset(self):
        mail.outbox.clear()
        preserved_user, preserved_listing, preserved_review = self.create_non_seed_data()
        preserved_snapshot = (
            preserved_user.email,
            preserved_user.first_name,
            preserved_user.contact_num,
            preserved_listing.title,
            preserved_listing.price,
            preserved_review.body,
            preserved_review.rating,
        )

        with patch('apps.messaging.signals.get_channel_layer') as get_channel_layer:
            with self.captureOnCommitCallbacks(execute=True):
                output = self.run_seed()
            self.assertFalse(get_channel_layer.called)

        seeded_users = User.objects.filter(email__endswith=SEED_DOMAIN)
        seeded_requests = PurchaseRequest.objects.filter(
            conversation__buyer__email__endswith=SEED_DOMAIN,
        )
        seeded_listings = Listing.objects.filter(seller__email__endswith=SEED_DOMAIN)
        self.assertEqual(seeded_users.count(), 15)
        self.assertEqual(SellerProfile.objects.filter(user__email__endswith=SEED_DOMAIN).count(), 6)
        self.assertEqual(seeded_listings.count(), 40)
        self.assertEqual(seeded_requests.count(), SEED_OPTIONS['transactions'])
        self.assertEqual(
            Conversation.objects.filter(buyer__email__endswith=SEED_DOMAIN).count(),
            Conversation.objects.filter(seller__email__endswith=SEED_DOMAIN).count(),
        )
        self.assertEqual(
            Listing.objects.filter(seller__email__endswith=SEED_DOMAIN, title__startswith='+').count(),
            1,
        )
        self.assertIn('STALLED_PENDING transaction IDs:', output)
        self.assertIn('REPEAT_CANCELLER transaction IDs:', output)
        self.assertIn('TIMEZONE_BOUNDARY transaction IDs:', output)

        self.assertEqual(seeded_users.filter(is_superuser=True).count(), 0)
        self.assertEqual(
            seeded_users.filter(is_deleted=True, deleted_at__isnull=False).count(),
            1,
        )
        self.assertFalse(
            seeded_users.get(email=f'ana.cruz{SEED_DOMAIN}').is_active,
        )
        self.assertEqual(seeded_users.filter(is_active=False, is_deleted=False).count(), 1)
        self.assertEqual(
            seeded_users.filter(contact_num__startswith='09').exclude(contact_num__regex=r'^09[0-9]{9}$').count(),
            0,
        )
        self.assertEqual(
            seeded_users.values('contact_num').distinct().count(),
            seeded_users.count(),
        )

        messages = Message.objects.filter(sender__email__endswith=SEED_DOMAIN)
        self.assertEqual(messages.count(), seeded_requests.count())
        for request in seeded_requests.select_related(
            'message',
            'conversation__buyer',
            'conversation__seller',
            'conversation__listing__category',
        ):
            conversation = request.conversation
            self.assertEqual(request.total_amount, request.unit_price * request.quantity)
            self.assertNotEqual(conversation.buyer_id, conversation.seller_id)
            self.assertEqual(conversation.seller_id, conversation.listing.seller_id)
            self.assertEqual(request.message.conversation_id, conversation.pk)
            self.assertEqual(request.message.sender_id, conversation.seller_id)
            self.assertEqual(request.message.kind, Message.Kind.PURCHASE_REQUEST)
            self.assertEqual(request.message.body, GENERIC_MESSAGE_BODY)
            self.assertTrue(request.message.is_read)
            self.assertFalse(request.message.attachment)
            self.assertEqual(
                request.is_service,
                conversation.listing.category.slug == 'services',
            )
            if request.payment_method == PurchaseRequest.PaymentMethod.GCASH:
                self.assertTrue(request.payment_reference)
            else:
                self.assertEqual(request.payment_reference, '')
            if request.status != PurchaseRequest.Status.REQUESTED:
                self.assertIsNotNone(request.submitted_at)
                self.assertGreaterEqual(request.submitted_at, request.created_at)
            if request.status in {
                PurchaseRequest.Status.CONFIRMED,
                PurchaseRequest.Status.DECLINED,
                PurchaseRequest.Status.CANCELLED,
                PurchaseRequest.Status.PROPOSED,
                PurchaseRequest.Status.COMPLETED,
            }:
                self.assertIsNotNone(request.responded_at)
                self.assertGreaterEqual(request.responded_at, request.submitted_at)
            if request.status == PurchaseRequest.Status.COMPLETED:
                self.assertIsNotNone(request.completed_at)
                self.assertGreaterEqual(request.completed_at, request.responded_at)
                self.assertLess(request.scheduled_end, request.completed_at)
            if request.status == PurchaseRequest.Status.PROPOSED:
                self.assertIsNotNone(request.proposed_start)
                self.assertIsNotNone(request.proposed_end)
                self.assertEqual(request.proposed_by_id, conversation.seller_id)

        now = timezone.now()
        pending_stalled = seeded_requests.filter(
            status__in=(PurchaseRequest.Status.REQUESTED, PurchaseRequest.Status.SUBMITTED),
            created_at__lt=now - timedelta(hours=48),
        )
        fresh_pending = seeded_requests.filter(
            status__in=(PurchaseRequest.Status.REQUESTED, PurchaseRequest.Status.SUBMITTED),
            created_at__gte=now - timedelta(hours=24),
        )
        self.assertGreaterEqual(pending_stalled.count(), 5)
        self.assertGreaterEqual(fresh_pending.count(), 3)

        stalled_delivery = seeded_requests.filter(
            status=PurchaseRequest.Status.CONFIRMED,
            scheduled_end__lt=now,
            completed_at__isnull=True,
        )
        future_confirmed = seeded_requests.filter(
            status=PurchaseRequest.Status.CONFIRMED,
            scheduled_end__gt=now,
            completed_at__isnull=True,
        )
        self.assertGreaterEqual(stalled_delivery.count(), 4)
        self.assertGreaterEqual(future_confirmed.count(), 3)

        high_value = seeded_requests.filter(total_amount__gte=Decimal('5000.00'))
        self.assertGreaterEqual(high_value.count(), 4)
        self.assertGreaterEqual(
            high_value.values('conversation__listing_id').distinct().count(),
            3,
        )
        self.assertEqual(
            seeded_requests.filter(total_amount=Decimal('4999.00')).count(),
            1,
        )
        self.assertEqual(
            seeded_requests.filter(total_amount=Decimal('4500.00')).count(),
            1,
        )
        self.assertGreaterEqual(
            high_value.values('status').distinct().count(),
            3,
        )

        repeat_buyer = seeded_users.get(email=f'juan.garcia{SEED_DOMAIN}')
        repeat_requests = seeded_requests.filter(
            conversation__buyer=repeat_buyer,
            status=PurchaseRequest.Status.CANCELLED,
        )
        self.assertEqual(
            repeat_requests.filter(created_at__gte=now - timedelta(days=30)).count(),
            4,
        )
        self.assertEqual(
            repeat_requests.filter(created_at__lt=now - timedelta(days=30)).count(),
            1,
        )

        boundary_requests = list(seeded_requests)
        local_times = [
            timezone.localtime(item.created_at, LOCAL_TIMEZONE)
            for item in boundary_requests
        ]
        first_boundary = next(
            item for item in boundary_requests
            if item.created_at.astimezone(datetime_timezone.utc).time() == time(15, 30)
        )
        second_boundary = next(
            item for item in boundary_requests
            if item.created_at.astimezone(datetime_timezone.utc).time() == time(16, 30)
        )
        self.assertEqual(
            first_boundary.created_at.astimezone(datetime_timezone.utc).date(),
            second_boundary.created_at.astimezone(datetime_timezone.utc).date(),
        )
        self.assertNotEqual(
            timezone.localtime(first_boundary.created_at, LOCAL_TIMEZONE).date(),
            timezone.localtime(second_boundary.created_at, LOCAL_TIMEZONE).date(),
        )
        self.assertIn(time(23, 59), [value.time() for value in local_times])

        soft_deleted_buyer = seeded_users.get(email=f'ana.cruz{SEED_DOMAIN}')
        inactive_seller = seeded_users.get(email=f'jose.reyes{SEED_DOMAIN}')
        self.assertGreaterEqual(seeded_requests.filter(conversation__buyer=soft_deleted_buyer).count(), 3)
        self.assertGreaterEqual(seeded_requests.filter(conversation__seller=inactive_seller).count(), 3)

        review_five = seeded_listings.get(title='Engineering Mechanics 5th Ed.')
        review_three = seeded_listings.get(title='Calculus Early Transcendentals')
        zero_review_listing = seeded_listings.get(title='Scientific Calculator Casio fx-991')
        self.assertEqual(seeded_requests.filter(conversation__listing=review_five).count(), 6)
        self.assertEqual(ListingReview.objects.filter(listing=review_five).count(), 5)
        self.assertEqual(seeded_requests.filter(conversation__listing=review_three).count(), 3)
        self.assertEqual(ListingReview.objects.filter(listing=review_three).count(), 3)
        self.assertEqual(
            seeded_requests.filter(
                conversation__listing=review_three,
                status=PurchaseRequest.Status.COMPLETED,
            ).values('conversation__buyer_id').distinct().count(),
            3,
        )
        self.assertEqual(seeded_requests.filter(conversation__listing=zero_review_listing).count(), 4)
        self.assertEqual(ListingReview.objects.filter(listing=zero_review_listing).count(), 0)
        for review in ListingReview.objects.filter(reviewer__email__endswith=SEED_DOMAIN):
            self.assertTrue(
                PurchaseRequest.objects.filter(
                    conversation__listing=review.listing,
                    conversation__buyer=review.reviewer,
                    status=PurchaseRequest.Status.COMPLETED,
                ).exists()
            )
        self.assertGreater(ListingReviewReply.objects.filter(
            review__reviewer__email__endswith=SEED_DOMAIN,
        ).count(), 0)
        self.assertEqual(
            ReviewNotification.objects.filter(
                recipient__email__endswith=SEED_DOMAIN,
            ).count(),
            0,
        )

        recycle_listing = seeded_listings.get(
            title='Scientific Calculator Casio fx-991',
            lifecycle_state=Listing.Lifecycle.RECYCLE_BIN,
        )
        archived_listing = seeded_listings.get(
            title='Compact Study Desk Organizer',
            lifecycle_state=Listing.Lifecycle.ARCHIVED,
        )
        self.assertTrue(seeded_requests.filter(conversation__listing=recycle_listing).exists())
        self.assertTrue(seeded_requests.filter(conversation__listing=archived_listing).exists())
        self.assertIsNotNone(recycle_listing.recycled_at)
        self.assertIsNotNone(recycle_listing.recycle_bin_expires_at)
        self.assertIsNotNone(archived_listing.archived_at)

        long_title = seeded_listings.get(
            title__startswith='Engineering Mechanics Reference Edition',
        )
        long_note_request = seeded_requests.exclude(buyer_note='').order_by('-pk').first()
        self.assertGreaterEqual(len(long_title.title), 115)
        self.assertIsNotNone(long_note_request)
        self.assertLessEqual(len(long_note_request.buyer_note), 500)
        exact_long_note = seeded_requests.get(
            buyer_note__startswith='Please coordinate pickup.',
        )
        self.assertEqual(len(exact_long_note.buyer_note), 500)
        self.assertIn('=SUM(1+1)', seeded_requests.values_list('buyer_note', flat=True))
        self.assertIn('BELOW_HIGH_VALUE transaction IDs:', output)
        self.assertIn('LONG_NOTE transaction IDs:', output)

        local_dates = Counter(
            timezone.localtime(item.created_at, LOCAL_TIMEZONE).date()
            for item in boundary_requests
        )
        local_today = timezone.localtime(now, LOCAL_TIMEZONE).date()
        for offset in range(7):
            self.assertGreaterEqual(
                local_dates[local_today - timedelta(days=offset)],
                3,
            )
        self.assertEqual(local_dates[local_today - timedelta(days=40)], 0)
        self.assertEqual(local_dates[local_today - timedelta(days=55)], 0)

        high_volume_seller = seeded_users.get(email=f'maria.santos{SEED_DOMAIN}')
        new_seller = seeded_users.get(email=f'liza.mendoza{SEED_DOMAIN}')
        self.assertEqual(seeded_listings.filter(seller=new_seller).count(), 1)
        self.assertEqual(seeded_requests.filter(conversation__seller=new_seller).count(), 0)
        self.assertGreater(
            seeded_requests.filter(conversation__seller=high_volume_seller).count(),
            10,
        )

        preserved_user.refresh_from_db()
        preserved_listing.refresh_from_db()
        preserved_review.refresh_from_db()
        self.assertEqual(
            (
                preserved_user.email,
                preserved_user.first_name,
                preserved_user.contact_num,
                preserved_listing.title,
                preserved_listing.price,
                preserved_review.body,
                preserved_review.rating,
            ),
            preserved_snapshot,
        )

        before_second_run = (
            seeded_users.count(),
            seeded_listings.count(),
            seeded_requests.count(),
            Message.objects.filter(sender__email__endswith=SEED_DOMAIN).count(),
            ListingReview.objects.filter(reviewer__email__endswith=SEED_DOMAIN).count(),
        )
        second_output = self.run_seed()
        self.assertIn('skipping without changes', second_output)
        self.assertEqual(
            (
                seeded_users.count(),
                seeded_listings.count(),
                seeded_requests.count(),
                Message.objects.filter(sender__email__endswith=SEED_DOMAIN).count(),
                ListingReview.objects.filter(reviewer__email__endswith=SEED_DOMAIN).count(),
            ),
            before_second_run,
        )
        self.assertEqual(mail.outbox, [])

        seed_user_ids = list(seeded_users.values_list('pk', flat=True))
        seed_listing_ids = list(seeded_listings.values_list('pk', flat=True))
        reset_output = StringIO()
        call_command('seed_demo_marketplace', reset=True, confirm=True, stdout=reset_output)
        self.assertIn('Deleted only users with the @seed.usep.test email domain.', reset_output.getvalue())
        self.assertFalse(User.objects.filter(pk__in=seed_user_ids).exists())
        self.assertFalse(Listing.objects.filter(pk__in=seed_listing_ids).exists())
        self.assertFalse(Conversation.objects.filter(
            buyer_id__in=seed_user_ids,
        ).exists())
        self.assertFalse(Conversation.objects.filter(
            seller_id__in=seed_user_ids,
        ).exists())
        self.assertFalse(Message.objects.filter(sender_id__in=seed_user_ids).exists())
        self.assertFalse(ListingReview.objects.filter(reviewer_id__in=seed_user_ids).exists())
        self.assertFalse(Listing.objects.filter(conversations__isnull=True, pk__in=seed_listing_ids).exists())
        self.assertTrue(User.objects.filter(pk=preserved_user.pk).exists())
        self.assertTrue(Listing.objects.filter(pk=preserved_listing.pk).exists())
        self.assertTrue(ListingReview.objects.filter(pk=preserved_review.pk).exists())
        self.assertEqual(mail.outbox, [])

    @patch.dict(os.environ, {'DJANGO_SETTINGS_MODULE': 'config.settings.production'})
    def test_command_refuses_production_settings(self):
        output = StringIO()
        with self.assertRaises(CommandError):
            call_command('seed_demo_marketplace', confirm=True, stdout=output)
        self.assertIn('Active settings: config.settings.production', output.getvalue())
