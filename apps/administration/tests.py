import csv
from datetime import datetime, timedelta, timezone as datetime_timezone
from decimal import Decimal
from io import StringIO

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Roles, SellerProfile
from apps.dashboard.models import Category, Listing
from apps.messaging.models import Conversation, Message, PurchaseRequest
from . import transaction_queries

User = get_user_model()


class TransactionHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = cls.create_user('admin@example.test', role=Roles.ADMIN)
        cls.buyer = cls.create_user('buyer@example.test')
        cls.seller = cls.create_user('seller@example.test')
        SellerProfile.objects.create(user=cls.seller)
        cls.category = Category.objects.create(name='Books', slug='books')
        cls.listing = Listing.objects.create(
            seller=cls.seller,
            category=cls.category,
            title='Sample listing',
            slug='sample-listing',
            description='Listing description',
            price='1250.00',
            condition='Good',
        )

    @staticmethod
    def create_user(email, **kwargs):
        return User.objects.create_user(
            email=email,
            password='Test-password-123',
            first_name=email.split('@')[0],
            last_name='User',
            contact_num=f'09{User.objects.count():09d}',
            is_first_login=False,
            **kwargs,
        )

    def create_transaction(self, *, status=PurchaseRequest.Status.REQUESTED, title=None):
        listing_number = Listing.objects.count()
        listing = Listing.objects.create(
            seller=self.seller,
            category=self.category,
            title=title or f'Sample listing {listing_number}',
            slug=f'transaction-listing-{listing_number}',
            description='Listing description',
            price='1250.00',
            condition='Good',
        )
        conversation = Conversation.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            listing=listing,
        )
        message = Message.objects.create(
            conversation=conversation,
            sender=self.seller,
            body='private-message-body-must-not-leak',
            kind=Message.Kind.PURCHASE_REQUEST,
        )
        return PurchaseRequest.objects.create(
            message=message,
            conversation=conversation,
            status=status,
            unit_price='1250.00',
            quantity=2,
            total_amount='2500.00',
            payment_method=PurchaseRequest.PaymentMethod.GCASH,
            payment_reference='REF-1234',
        )

    def login_admin(self):
        self.client.force_login(self.admin)

    def test_access_control_for_all_phase_a_routes(self):
        purchase = self.create_transaction()
        paths = (
            reverse('administration:transactions_monitoring'),
            reverse('administration:transactions_monitoring_data'),
            reverse('administration:transactions_history'),
            reverse('administration:transactions_data'),
            reverse('administration:transaction_detail', args=[purchase.pk]),
            reverse('administration:transactions_export'),
        )

        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertIn(response.status_code, (302, 401))

        self.client.force_login(self.buyer)
        buyer_responses = []
        for path in paths:
            with self.subTest(path=path, user='regular'):
                response = self.client.get(path)
                self.assertIn(response.status_code, (302, 403))
                buyer_responses.append((
                    response.status_code,
                    response.content,
                    response.get('Location'),
                    response.get('Content-Type'),
                ))

        self.client.force_login(self.seller)
        for path, buyer_response in zip(paths, buyer_responses):
            with self.subTest(path=path, user='seller'):
                response = self.client.get(path)
                seller_response = (
                    response.status_code,
                    response.content,
                    response.get('Location'),
                    response.get('Content-Type'),
                )
                self.assertEqual(seller_response, buyer_response)

        self.login_admin()
        for path in paths:
            with self.subTest(path=path, user='admin'):
                response = self.client.get(path)
                self.assertNotIn(response.status_code, (302, 401, 403))

    def test_history_filters_search_sort_pagination_and_out_of_range_page(self):
        first = self.create_transaction(title='Alpha listing')
        second = self.create_transaction(status=PurchaseRequest.Status.COMPLETED, title='Beta listing')
        second.total_amount = '5000.00'
        second.save(update_fields=['total_amount'])
        self.login_admin()
        response = self.client.get(
            reverse('administration:transactions_data'),
            {'q': str(first.pk), 'status': 'pending', 'sort': 'oldest'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['id'] for row in response.json()['results']], [first.pk])

        filtered = self.client.get(
            reverse('administration:transactions_data'),
            {'status': 'completed', 'sort': 'highest_amount'},
        ).json()
        self.assertEqual([row['id'] for row in filtered['results']], [second.pk])

        filtered = self.client.get(
            reverse('administration:transactions_data'),
            {
                'type': 'product',
                'seller': self.seller.pk,
                'category': self.category.pk,
                'payment_method': PurchaseRequest.PaymentMethod.GCASH,
                'amount_min': '4000',
                'sort': 'highest_amount',
            },
        ).json()
        self.assertEqual([row['id'] for row in filtered['results']], [second.pk])

        sorted_rows = self.client.get(
            reverse('administration:transactions_data'),
            {'sort': 'highest_amount'},
        ).json()
        self.assertEqual([row['id'] for row in sorted_rows['results']], [second.pk, first.pk])

        page = self.client.get(
            reverse('administration:transactions_data'),
            {'page': '100'},
        ).json()
        self.assertEqual(page['page'], 1)
        self.assertEqual(page['total'], 2)

    def test_ajax_and_normal_filters_are_identical(self):
        self.create_transaction()
        self.create_transaction(status=PurchaseRequest.Status.COMPLETED)
        self.login_admin()
        url = reverse('administration:transactions_data')
        params = {'status': 'pending'}

        normal = self.client.get(url, params).json()
        ajax = self.client.get(url, params, HTTP_X_REQUESTED_WITH='XMLHttpRequest').json()
        self.assertEqual(normal, ajax)

    def test_csv_is_filtered_safe_and_audited_once(self):
        self.create_transaction(title='=HYPERLINK("https://example.test")')
        self.create_transaction(status=PurchaseRequest.Status.COMPLETED, title='Normal listing')
        self.login_admin()
        response = self.client.get(
            reverse('administration:transactions_export'),
            {'status': 'pending'},
        )
        contents = b''.join(response.streaming_content).decode('utf-8')
        self.assertTrue(contents.startswith('\ufeff'))
        rows = list(csv.reader(StringIO(contents.lstrip('\ufeff'))))
        self.assertEqual(rows[0][0], 'Transaction ID')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][12], '2')
        self.assertEqual(rows[1][13], '1250.00')
        self.assertEqual(rows[1][14], '2500.00')
        self.assertEqual(rows[1][6], '\'=HYPERLINK("https://example.test")')
        table_data = self.client.get(
            reverse('administration:transactions_data'),
            {'status': 'pending'},
        ).json()
        self.assertEqual(len(rows) - 1, table_data['total'])

        entry = LogEntry.objects.get(action_flag=CHANGE)
        self.assertEqual(entry.content_type, ContentType.objects.get_for_model(User))
        self.assertEqual(entry.user_id, self.admin.pk)
        self.assertEqual(entry.object_id, str(self.admin.pk))
        self.assertEqual(entry.action_flag, CHANGE)
        self.assertIn('Exported transactions CSV', entry.change_message)
        self.assertIn('rows: 1', entry.change_message)
        self.assertEqual(LogEntry.objects.count(), 1)

    def test_non_get_csv_and_json_requests_are_rejected_for_non_admins(self):
        purchase = self.create_transaction()
        paths = (
            reverse('administration:transactions_data'),
            reverse('administration:transaction_detail', args=[purchase.pk]),
            reverse('administration:transactions_export'),
        )

        self.client.logout()
        for path in paths:
            with self.subTest(path=path, user='anonymous'):
                response = self.client.post(path)
                self.assertEqual(response.status_code, 401)

        for user, username in ((self.buyer, 'buyer'), (self.seller, 'seller')):
            self.client.force_login(user)
            for path in paths:
                with self.subTest(path=path, user=username):
                    response = self.client.post(path)
                    self.assertEqual(response.status_code, 403)

    def test_soft_deleted_and_inactive_parties_render_without_message_body(self):
        purchase = self.create_transaction()
        self.buyer.is_deleted = True
        self.buyer.save(update_fields=['is_deleted'])
        self.seller.is_active = False
        self.seller.save(update_fields=['is_active'])
        self.login_admin()

        page = self.client.get(reverse('administration:transactions_history'))
        detail = self.client.get(reverse('administration:transaction_detail', args=[purchase.pk]))
        data = self.client.get(reverse('administration:transactions_data'))
        monitoring = self.client.get(reverse('administration:transactions_monitoring_data'))
        export = self.client.get(reverse('administration:transactions_export'))
        page_text = page.content.decode()
        detail_text = detail.content.decode()
        data_text = data.content.decode()
        monitoring_text = monitoring.content.decode()
        export_text = b''.join(export.streaming_content).decode('utf-8')
        for content in (page_text, detail_text, data_text, monitoring_text, export_text):
            self.assertNotIn('private-message-body-must-not-leak', content)
        self.assertContains(page, 'Buyer')
        self.assertContains(page, 'Deleted')
        self.assertContains(page, 'Inactive')
        self.assertEqual(detail.json()['transaction']['buyer_account_status'], 'Deleted')
        self.assertEqual(detail.json()['transaction']['seller_account_status'], 'Inactive')
        latest = monitoring.json()['latest_transactions'][0]
        self.assertEqual(latest['buyer_account_status'], 'Deleted')
        self.assertEqual(latest['seller_account_status'], 'Inactive')
        self.assertEqual(detail.json()['transaction']['payment_proof_uploaded'], False)
        self.assertNotIn('purchase_proofs/', detail_text)

    def test_query_count_is_constant_for_five_and_fifty_rows(self):
        self.login_admin()
        url = reverse('administration:transactions_data')

        def query_count_for(row_count):
            PurchaseRequest.objects.all().delete()
            Conversation.objects.all().delete()
            for _ in range(row_count):
                self.create_transaction()
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            return len(queries)

        count_for_five = query_count_for(5)
        count_for_fifty = query_count_for(50)
        self.assertEqual(count_for_five, count_for_fifty)
        self.assertEqual(count_for_five, 5)
        self.assertLessEqual(count_for_five, transaction_queries.TRANSACTION_QUERY_CEILING)

    def test_created_at_filter_uses_manila_day_boundary(self):
        purchase = self.create_transaction()
        utc_time = datetime(2026, 10, 25, 17, 0, tzinfo=datetime_timezone.utc)
        PurchaseRequest.objects.filter(pk=purchase.pk).update(created_at=utc_time)
        self.login_admin()

        next_day = self.client.get(
            reverse('administration:transactions_data'),
            {'date_from': '2026-10-26', 'date_to': '2026-10-26'},
        ).json()
        prior_day = self.client.get(
            reverse('administration:transactions_data'),
            {'date_from': '2026-10-25', 'date_to': '2026-10-25'},
        ).json()
        self.assertEqual([row['id'] for row in next_day['results']], [purchase.pk])
        self.assertEqual(prior_day['results'], [])
        self.assertTrue(next_day['results'][0]['created_display'].endswith('PHT'))

    def test_monitoring_kpis_buckets_completed_period_and_deltas(self):
        today = timezone.localdate(timezone=transaction_queries.ADMIN_TIMEZONE)
        current_day = transaction_queries.local_day_boundary(today)
        previous_day = transaction_queries.local_day_boundary(today - timedelta(days=7))
        pending = self.create_transaction(status=PurchaseRequest.Status.REQUESTED)
        in_progress = self.create_transaction(status=PurchaseRequest.Status.CONFIRMED)
        closed = self.create_transaction(status=PurchaseRequest.Status.DECLINED)
        completed = self.create_transaction(status=PurchaseRequest.Status.COMPLETED)
        completed_before_period = self.create_transaction(status=PurchaseRequest.Status.COMPLETED)
        previous = self.create_transaction(status=PurchaseRequest.Status.REQUESTED)
        PurchaseRequest.objects.filter(pk__in=[
            pending.pk, in_progress.pk, closed.pk, completed.pk,
        ]).update(created_at=current_day)
        PurchaseRequest.objects.filter(pk=completed.pk).update(completed_at=current_day)
        PurchaseRequest.objects.filter(pk=completed_before_period.pk).update(
            created_at=transaction_queries.local_day_boundary(today - timedelta(days=40)),
            completed_at=current_day,
            total_amount=Decimal('3500.00'),
        )
        PurchaseRequest.objects.filter(pk=previous.pk).update(created_at=previous_day)
        self.login_admin()

        response = self.client.get(reverse('administration:transactions_monitoring_data'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['kpis']['total'], 4)
        self.assertEqual(data['kpis']['pending'], 1)
        self.assertEqual(data['kpis']['in_progress'], 1)
        self.assertEqual(data['kpis']['closed_failed'], 1)
        self.assertEqual(data['kpis']['completed_count'], 2)
        self.assertEqual(data['kpis']['completed_value'], '6000.00')
        self.assertEqual(data['kpis']['completed_value_display'], '₱6,000')
        self.assertEqual(data['kpis']['deltas']['total']['percent'], 300.0)
        self.assertEqual(data['kpis']['deltas']['pending']['percent'], 0.0)
        self.assertEqual(data['daily_series'], [{
            'day': today.isoformat(),
            'pending': 1,
            'in_progress': 1,
            'completed': 1,
            'closed_failed': 1,
        }])
        self.assertEqual(data['period']['range'], '7d')

    def test_monitoring_attention_rules_use_exact_thresholds_and_dates(self):
        now = timezone.now()
        stalled = self.create_transaction(status=PurchaseRequest.Status.REQUESTED)
        fresh = self.create_transaction(status=PurchaseRequest.Status.SUBMITTED)
        stalled_delivery = self.create_transaction(status=PurchaseRequest.Status.CONFIRMED)
        future_delivery = self.create_transaction(status=PurchaseRequest.Status.CONFIRMED)
        high_value = self.create_transaction(status=PurchaseRequest.Status.REQUESTED)
        repeated_cancellations = [
            self.create_transaction(status=PurchaseRequest.Status.CANCELLED)
            for _ in range(3)
        ]
        too_old = self.create_transaction(status=PurchaseRequest.Status.CANCELLED)
        decline = self.create_transaction(status=PurchaseRequest.Status.DECLINED)
        PurchaseRequest.objects.filter(pk=stalled.pk).update(created_at=now - timedelta(hours=49))
        PurchaseRequest.objects.filter(pk=fresh.pk).update(created_at=now - timedelta(hours=1))
        PurchaseRequest.objects.filter(pk=stalled_delivery.pk).update(
            scheduled_end=now - timedelta(minutes=1),
        )
        PurchaseRequest.objects.filter(pk=future_delivery.pk).update(
            scheduled_end=now + timedelta(days=2),
        )
        PurchaseRequest.objects.filter(pk=high_value.pk).update(total_amount=Decimal('5000.00'))
        for offset, purchase in enumerate(repeated_cancellations, start=1):
            PurchaseRequest.objects.filter(pk=purchase.pk).update(
                responded_at=now - timedelta(days=offset),
            )
        PurchaseRequest.objects.filter(pk=too_old.pk).update(
            responded_at=now - timedelta(days=31),
        )
        PurchaseRequest.objects.filter(pk=decline.pk).update(
            responded_at=now - timedelta(days=1),
        )
        self.login_admin()

        data = self.client.get(reverse('administration:transactions_monitoring_data')).json()
        self.assertEqual(data['attention_counts'], {
            'stalled_pending': 1,
            'stalled_delivery': 1,
            'high_value': 1,
            'repeat_canceller': 1,
        })
        ids_by_rule = {}
        for item in data['attention_items']:
            ids_by_rule.setdefault(item['rule'], set()).add(item['transaction']['id'])
        self.assertEqual(ids_by_rule['stalled_pending'], {stalled.pk})
        self.assertEqual(ids_by_rule['stalled_delivery'], {stalled_delivery.pk})
        self.assertEqual(ids_by_rule['high_value'], {high_value.pk})
        self.assertEqual(ids_by_rule['repeat_canceller'], {repeated_cancellations[0].pk})
        self.assertNotIn(fresh.pk, ids_by_rule.get('stalled_pending', set()))
        self.assertNotIn(future_delivery.pk, ids_by_rule.get('stalled_delivery', set()))
        self.assertEqual(data['cancellation_note'], 'Cancellation party is not recorded.')

    def test_monitoring_chart_uses_manila_calendar_day(self):
        purchase = self.create_transaction()
        utc_boundary = datetime(2026, 10, 25, 17, 0, tzinfo=datetime_timezone.utc)
        PurchaseRequest.objects.filter(pk=purchase.pk).update(created_at=utc_boundary)
        self.login_admin()
        data = self.client.get(
            reverse('administration:transactions_monitoring_data'),
            {
                'range': 'custom',
                'date_from': '2026-10-26',
                'date_to': '2026-10-26',
            },
        ).json()
        self.assertEqual(data['daily_series'][0]['day'], '2026-10-26')
        self.assertEqual(data['daily_series'][0]['pending'], 1)
        self.assertEqual(data['period']['label'], 'Oct 26 – Oct 26, 2026 PHT')

    def test_monitoring_query_count_is_constant_for_five_and_fifty_rows(self):
        self.login_admin()
        url = reverse('administration:transactions_monitoring_data')

        def query_count_for(row_count):
            PurchaseRequest.objects.all().delete()
            Conversation.objects.all().delete()
            for _ in range(row_count):
                self.create_transaction()
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get(url, {'range': '7d'})
            self.assertEqual(response.status_code, 200)
            return len(queries)

        count_for_five = query_count_for(5)
        count_for_fifty = query_count_for(50)
        self.assertEqual(
            count_for_five,
            count_for_fifty,
            f'Monitoring query counts were {count_for_five} and {count_for_fifty}.',
        )
        self.assertEqual(count_for_five, 17)
        self.assertLessEqual(count_for_five, transaction_queries.MONITORING_QUERY_CEILING)

    def test_monitoring_custom_range_rejects_invalid_dates(self):
        self.login_admin()
        response = self.client.get(
            reverse('administration:transactions_monitoring_data'),
            {'range': 'custom', 'date_from': '2026-11-02', 'date_to': '2026-11-01'},
        )
        self.assertEqual(response.status_code, 400)

    def test_monitoring_dashboard_and_stock_note_are_present(self):
        self.login_admin()
        response = self.client.get(reverse('administration:transactions_monitoring'))
        self.assertContains(response, 'Transactions by day')
        self.assertContains(response, 'Needs attention')
        self.assertContains(response, 'Cancellation party is not recorded.')
        history = self.client.get(reverse('administration:transactions_history'))
        self.assertContains(
            history,
            'Stock decreases when product delivery is confirmed as complete; it does not decrease when a request is created or accepted.',
        )
