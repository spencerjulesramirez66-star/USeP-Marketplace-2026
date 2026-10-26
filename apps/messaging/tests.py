from datetime import datetime, time, timedelta, timezone as datetime_timezone

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from django.template.loader import render_to_string

from apps.accounts.models import SellerProfile
from apps.dashboard.models import Category, Listing
from apps.messaging.forms import PurchaseVerificationForm, validate_schedule_times
from apps.messaging.models import Conversation, Message, PurchaseRequest
from apps.messaging.schedule import ProposalForm
from apps.messaging.schedule_config import SCHEDULE_TIMEZONE
from apps.messaging.services import busy_slots

User = get_user_model()


class ScheduleTimeValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seller = cls.create_user('schedule-seller@example.test')
        SellerProfile.objects.create(user=cls.seller)
        cls.buyer = cls.create_user('schedule-buyer@example.test')
        category = Category.objects.create(name='Schedule category', slug='schedule-category')
        cls.listing = Listing.objects.create(
            seller=cls.seller,
            category=category,
            title='Schedule listing',
            slug='schedule-listing',
            description='Schedule test listing',
            price='100.00',
            condition='Good',
        )
        cls.conversation = Conversation.objects.create(
            seller=cls.seller,
            buyer=cls.buyer,
            listing=cls.listing,
        )

    @staticmethod
    def create_user(email):
        return User.objects.create_user(
            email=email,
            password='Test-password-123',
            first_name=email.split('@')[0],
            last_name='User',
            contact_num=f'09{User.objects.count():09d}',
            is_first_login=False,
        )

    def schedule_date(self):
        return timezone.localdate(timezone=SCHEDULE_TIMEZONE) + timedelta(days=10)

    def form_for(self, start, end):
        day = self.schedule_date()
        return ProposalForm(data={
            'start': f'{day.isoformat()}T{start}',
            'end': f'{day.isoformat()}T{end}',
        })

    def create_purchase(self, *, status=PurchaseRequest.Status.SUBMITTED, start=None, end=None,
                        proposed_by=None, proposed_start=None, proposed_end=None):
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.seller,
            body='Purchase confirmation request',
            kind=Message.Kind.PURCHASE_REQUEST,
        )
        return PurchaseRequest.objects.create(
            message=message,
            conversation=self.conversation,
            status=status,
            is_service=True,
            unit_price='100.00',
            total_amount='100.00',
            scheduled_start=start,
            scheduled_end=end,
            proposed_by=proposed_by,
            proposed_start=proposed_start,
            proposed_end=proposed_end,
        )

    def local_datetime(self, day, hour, minute=0):
        return timezone.make_aware(datetime.combine(day, time(hour, minute)), SCHEDULE_TIMEZONE)

    def test_valid_schedule_and_exact_open_close_boundaries_are_accepted(self):
        for start, end in [('07:00', '08:00'), ('16:00', '17:00')]:
            with self.subTest(start=start, end=end):
                self.assertTrue(self.form_for(start, end).is_valid())

    def test_out_of_range_order_and_cross_day_schedules_are_rejected(self):
        cases = [
            ('06:45', '07:45', 'Schedules must be between 7:00 AM and 5:00 PM.'),
            ('16:00', '17:15', 'Schedules must be between 7:00 AM and 5:00 PM.'),
            ('10:00', '09:00', 'The schedule end must be after the start.'),
        ]
        for start, end, expected in cases:
            with self.subTest(start=start, end=end):
                form = self.form_for(start, end)
                self.assertFalse(form.is_valid())
                self.assertIn(expected, str(form.errors))

        day = self.schedule_date()
        form = ProposalForm(data={
            'start': f'{day.isoformat()}T16:00',
            'end': f'{(day + timedelta(days=1)).isoformat()}T08:00',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('same day', str(form.errors))

    def test_schedule_form_interprets_input_as_manila_time(self):
        day = self.schedule_date()
        form = self.form_for('08:00', '09:00')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['start'].astimezone(datetime_timezone.utc).hour, 0)

        utc_start = timezone.make_aware(datetime.combine(day, time(10)), datetime_timezone.utc)
        utc_end = timezone.make_aware(datetime.combine(day, time(11)), datetime_timezone.utc)
        with self.assertRaises(ValidationError):
            validate_schedule_times(utc_start, utc_end)

        rejected = ProposalForm(data={
            'start': f'{day.isoformat()}T18:00',
            'end': f'{day.isoformat()}T19:00',
        })
        self.assertFalse(rejected.is_valid())
        self.assertIn('Schedules must be between 7:00 AM and 5:00 PM.', str(rejected.errors))

    def test_purchase_verification_schedule_input_is_manila_time(self):
        purchase = self.create_purchase(status=PurchaseRequest.Status.REQUESTED)
        day = self.schedule_date()
        form = PurchaseVerificationForm(data={
            'quantity': '1',
            'payment_method': PurchaseRequest.PaymentMethod.CASH,
            'scheduled_start': f'{day.isoformat()}T08:00',
            'scheduled_end': f'{day.isoformat()}T09:00',
        }, purchase=purchase)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['scheduled_start'].astimezone(datetime_timezone.utc).hour, 0)

    def test_busy_calendar_slots_are_serialized_as_manila_wall_time(self):
        day = self.schedule_date()
        self.create_purchase(
            status=PurchaseRequest.Status.CONFIRMED,
            start=self.local_datetime(day, 8),
            end=self.local_datetime(day, 9),
        )
        self.assertEqual(busy_slots(self.seller.pk)[0]['start'], f'{day.isoformat()}T08:00:00')

    def test_schedule_events_include_out_of_hours_and_midnight_events_in_manila_time(self):
        day = self.schedule_date()
        overnight = self.create_purchase(
            status=PurchaseRequest.Status.CONFIRMED,
            start=self.local_datetime(day, 21),
            end=self.local_datetime(day + timedelta(days=1), 1),
        )
        utc_start = timezone.make_aware(datetime.combine(day, time(17)), datetime_timezone.utc)
        utc_end = utc_start + timedelta(hours=1)
        utc_event = self.create_purchase(
            status=PurchaseRequest.Status.CONFIRMED,
            start=utc_start,
            end=utc_end,
        )
        self.client.force_login(self.seller)

        response = self.client.get(reverse('messaging:schedule_events'))

        self.assertEqual(response.status_code, 200)
        events = {event['id']: event for event in response.json()['events']}
        self.assertEqual(
            events[overnight.pk]['start'],
            self.local_datetime(day, 21).isoformat(),
        )
        self.assertEqual(
            events[overnight.pk]['end'],
            self.local_datetime(day + timedelta(days=1), 1).isoformat(),
        )
        self.assertEqual(
            events[utc_event.pk]['start'],
            self.local_datetime(day + timedelta(days=1), 1).isoformat(),
        )

    def test_reschedule_endpoint_uses_the_same_schedule_validation(self):
        day = self.schedule_date()
        purchase = self.create_purchase(
            status=PurchaseRequest.Status.CONFIRMED,
            start=self.local_datetime(day, 10),
            end=self.local_datetime(day, 11),
        )
        self.client.force_login(self.seller)
        url = reverse('messaging:schedule_propose', args=[purchase.pk])

        invalid = self.client.post(url, {'start': f'{day.isoformat()}T18:00', 'end': f'{day.isoformat()}T19:00'})
        self.assertEqual(invalid.status_code, 400)
        self.assertIn('Schedules must be between 7:00 AM and 5:00 PM.', invalid.json()['error'])

        valid = self.client.post(url, {'start': f'{day.isoformat()}T08:00', 'end': f'{day.isoformat()}T09:00'})
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(valid.json()['event']['proposed_start'], self.local_datetime(day, 8).isoformat())

    def test_only_the_non_proposer_can_accept(self):
        day = self.schedule_date()
        purchase = self.create_purchase(
            status=PurchaseRequest.Status.PROPOSED,
            start=self.local_datetime(day, 10),
            end=self.local_datetime(day, 11),
            proposed_by=self.seller,
            proposed_start=self.local_datetime(day, 12),
            proposed_end=self.local_datetime(day, 13),
        )
        url = reverse('messaging:schedule_accept', args=[purchase.pk])
        self.client.force_login(self.seller)
        proposer_response = self.client.post(url)
        self.assertEqual(proposer_response.status_code, 400)
        self.assertIn('Waiting for the other person to respond.', proposer_response.json()['error'])

        self.client.force_login(self.buyer)
        recipient_response = self.client.post(url)
        self.assertEqual(recipient_response.status_code, 200)
        self.assertEqual(recipient_response.json()['event']['status'], PurchaseRequest.Status.CONFIRMED)
        self.assertIn('PHT', recipient_response.json()['html'])

    def test_proposed_purchase_card_shows_confirm_only_to_non_proposer(self):
        day = self.schedule_date()
        purchase = self.create_purchase(
            status=PurchaseRequest.Status.PROPOSED,
            proposed_by=self.seller,
            proposed_start=self.local_datetime(day, 12),
            proposed_end=self.local_datetime(day, 13),
        )
        factory = RequestFactory()
        template = 'messaging/components/message.html'
        seller_request = factory.get('/', HTTP_HOST='testserver')
        seller_request.user = self.seller

        seller_html = render_to_string(template, {
            'message': purchase.message,
            'chat_participant': self.buyer,
            'seen_message_id': None,
        }, request=seller_request)
        buyer_request = factory.get('/', HTTP_HOST='testserver')
        buyer_request.user = self.buyer
        buyer_html = render_to_string(template, {
            'message': purchase.message,
            'chat_participant': self.seller,
            'seen_message_id': None,
        }, request=buyer_request)

        self.assertIn('Waiting for the other party to respond.', seller_html)
        self.assertNotIn('>Confirm</button>', seller_html)
        self.assertIn('>Confirm</button>', buyer_html)
        self.assertIn('PHT', buyer_html)

    def test_existing_out_of_hours_schedule_is_returned_for_calendar_display(self):
        day = self.schedule_date()
        purchase = self.create_purchase(
            status=PurchaseRequest.Status.CONFIRMED,
            start=self.local_datetime(day, 19),
            end=self.local_datetime(day, 20),
        )
        self.client.force_login(self.seller)
        page = self.client.get(reverse('messaging:schedule'))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'data-open="7"')
        self.assertContains(page, 'data-close="17"')

        response = self.client.get(reverse('messaging:schedule_events'))
        self.assertEqual(response.status_code, 200)
        event = next(item for item in response.json()['events'] if item['id'] == purchase.pk)
        self.assertIn('19:00:00+08:00', event['start'])
