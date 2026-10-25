import random
import os
from collections import defaultdict
from datetime import datetime, time, timedelta, timezone as datetime_timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models.signals import post_save
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import SellerProfile, User
from apps.dashboard.models import (
    Category,
    Listing,
    ListingImage,
    ListingReview,
    ListingReviewReply,
    ListingReviewPhoto,
    ReviewNotification,
    SavedItem,
)
from apps.dashboard.services.listing_lifecycle import recycle_bin_deadline
from apps.messaging import signals as message_signals
from apps.messaging.models import Conversation, Message, PurchaseRequest

SEED_DOMAIN = '@seed.usep.test'
SEED_PASSWORD = 'TestPassword123!'
LOCAL_TIMEZONE = ZoneInfo('Asia/Manila')
GENERIC_MESSAGE_BODY = 'Purchase request'
MIN_TRANSACTIONS = 47
MIN_HISTORY_DAYS = 60

STATUS_WEIGHTS = (
    (PurchaseRequest.Status.COMPLETED, 40),
    (PurchaseRequest.Status.CONFIRMED, 12),
    (PurchaseRequest.Status.SUBMITTED, 8),
    (PurchaseRequest.Status.REQUESTED, 5),
    (PurchaseRequest.Status.PROPOSED, 5),
    (PurchaseRequest.Status.CANCELLED, 18),
    (PurchaseRequest.Status.DECLINED, 12),
)

FIRST_NAMES = (
    'Maria', 'Juan', 'Angelica', 'Jericho', 'Miguel', 'Sofia', 'Paolo',
    'Bianca', 'Ethan', 'Grace', 'Rafael', 'Liza', 'Carlo', 'Isabella',
    'Gabriel', 'Camille', 'Andres', 'Patricia', 'Nico', 'Beatriz',
    'Marco', 'Hannah', 'Luis', 'Therese', 'Adrian', 'Mikaela', 'Joshua',
    'Clarisse', 'Nathan', 'Diana',
)
SURNAMES = (
    'Santos', 'Reyes', 'Dela Cruz', 'Villanueva', 'Garcia', 'Cruz',
    'Ramos', 'Flores', 'Navarro', 'Lim', 'Castillo', 'Aquino', 'Torres',
    'Mendoza', 'Bautista', 'Gonzales', 'Fernandez', 'Rivera', 'Mercado',
    'Perez', 'Soriano', 'Valdez', 'Mabini', 'Del Rosario', 'Francisco',
    'Manalo', 'Abad', 'Ocampo', 'Tan', 'Luna',
)

USER_SPECS = (
    ('seller', 'maria.santos', 'Maria', 'Santos', True, True, False),
    ('seller', 'jose.reyes', 'Jose', 'Reyes', True, False, False),
    ('seller', 'angelica.delacruz', 'Angelica', 'Dela Cruz', True, True, False),
    ('seller', 'jericho.villanueva', 'Jericho', 'Villanueva', True, True, False),
    ('seller', 'carlo.bautista', 'Carlo', 'Bautista', True, True, False),
    ('seller', 'liza.mendoza', 'Liza', 'Mendoza', True, True, False),
    ('buyer', 'juan.garcia', 'Juan', 'Garcia', False, True, False),
    ('buyer', 'ana.cruz', 'Ana', 'Cruz', False, True, True),
    ('buyer', 'miguel.ramos', 'Miguel', 'Ramos', False, True, False),
    ('buyer', 'sofia.flores', 'Sofia', 'Flores', False, True, False),
    ('buyer', 'paolo.navarro', 'Paolo', 'Navarro', False, True, False),
    ('buyer', 'bianca.lim', 'Bianca', 'Lim', False, True, False),
    ('buyer', 'ethan.castillo', 'Ethan', 'Castillo', False, True, False),
    ('buyer', 'grace.aquino', 'Grace', 'Aquino', False, True, False),
    ('buyer', 'rafael.torres', 'Rafael', 'Torres', False, True, False),
)

LISTING_SPECS = (
    ('review_five', 'textbooks', 'Engineering Mechanics 5th Ed.', '850.00', 'Like new'),
    ('review_three', 'textbooks', 'Calculus Early Transcendentals', '780.00', 'Barely used'),
    ('archive_transaction', 'dorm-essentials', 'Compact Study Desk Organizer', '320.00', 'Good condition'),
    ('recycle_extra', 'uniforms', 'PE Uniform Medium', '350.00', 'Good condition'),
    ('long_title', 'textbooks', 'Engineering Mechanics Reference Edition with Worked Examples and Campus Study Notes for Engineering Students and Instructors', '900.00', 'Good condition'),
    ('laptop', 'electronics', 'Student Laptop 14-inch Core i5', '28900.00', 'Good condition'),
    ('tablet', 'electronics', 'Android Study Tablet 10-inch', '9800.00', 'Like new'),
    ('camera', 'electronics', 'Mirrorless Camera with Kit Lens', '18500.00', 'Barely used'),
    ('highvalue_focus', 'electronics', 'Scientific Calculator Casio fx-991', '8500.00', 'Good condition'),
    ('formula_title', 'services', '+Math Tutoring Promo', '450.00', 'Available by appointment'),
    ('textbook_02', 'textbooks', 'Introduction to Python Programming Study Book', '620.00', 'Barely used'),
    ('textbook_03', 'textbooks', 'Data Structures and Algorithms Textbook', '740.00', 'Like new'),
    ('textbook_04', 'textbooks', 'College Physics Problem Workbook', '520.00', 'Good condition'),
    ('textbook_05', 'textbooks', 'Accounting Principles Reviewer', '480.00', 'Good condition'),
    ('textbook_06', 'textbooks', 'Philippine Literature Anthology', '390.00', 'Like new'),
    ('textbook_07', 'textbooks', 'General Chemistry Laboratory Manual', '425.00', 'Barely used'),
    ('textbook_08', 'textbooks', 'Engineering Mathematics Reviewer', '560.00', 'Good condition'),
    ('textbook_09', 'textbooks', 'Microeconomics Student Edition', '650.00', 'For parts'),
    ('electronics_02', 'electronics', 'USB-C Hub 6-in-1', '1450.00', 'Like new'),
    ('electronics_03', 'electronics', 'Scientific Calculator with Protective Cover', '1250.00', 'Good condition'),
    ('electronics_04', 'electronics', 'Wireless Keyboard and Mouse Set', '980.00', 'Barely used'),
    ('electronics_05', 'electronics', 'USB Rechargeable Desk Fan', '720.00', 'Good condition'),
    ('electronics_06', 'electronics', 'Portable SSD 500GB', '3200.00', 'Like new'),
    ('electronics_07', 'electronics', 'Bluetooth Headphones', '1850.00', 'Good condition'),
    ('electronics_08', 'electronics', 'Webcam with Built-in Microphone', '1350.00', 'Barely used'),
    ('uniform_02', 'uniforms', 'White School Uniform Shirt Size Large', '280.00', 'Like new'),
    ('uniform_03', 'uniforms', 'USeP PE Pants Size Small', '320.00', 'Good condition'),
    ('uniform_04', 'uniforms', 'Laboratory Coat Size Medium', '390.00', 'Barely used'),
    ('uniform_05', 'uniforms', 'School ID Lace and Holder', '160.00', 'Good condition'),
    ('uniform_06', 'uniforms', 'NSTP Shirt Size Large', '250.00', 'For parts'),
    ('uniform_07', 'uniforms', 'Department Polo Shirt Size Medium', '350.00', 'Like new'),
    ('dorm_02', 'dorm-essentials', 'Electric Fan 16 inch', '1150.00', 'Good condition'),
    ('dorm_03', 'dorm-essentials', 'USB Rechargeable LED Study Lamp', '460.00', 'Like new'),
    ('dorm_04', 'dorm-essentials', 'Foldable Laundry Basket', '280.00', 'Barely used'),
    ('dorm_05', 'dorm-essentials', 'Electric Kettle 1.5L', '850.00', 'Good condition'),
    ('dorm_06', 'dorm-essentials', 'Foam Mattress Single Size', '1200.00', 'Good condition'),
    ('dorm_07', 'dorm-essentials', 'Compact Desk Organizer Set', '340.00', 'Like new'),
    ('service_02', 'services', 'Resume Review', '350.00', 'Available by appointment'),
    ('service_03', 'services', 'Thesis Proofreading', '700.00', 'On-site service'),
    ('service_04', 'services', 'Laptop Setup and Basic Software Help', '600.00', 'On-site service'),
)

LOCATIONS = (
    'USeP campus library',
    'Obrero Campus library or online',
    'Mintal Campus, Davao City',
    'Tagum Campus, Tagum City',
    'Student center',
    'ICT building',
    'Engineering building',
)

BUYER_NOTES = (
    'Can we meet at the library at 3pm?',
    'Pwede po ba ang GCash?',
    'I can pick this up after class.',
    'Please let me know which campus gate is convenient.',
    'Can we arrange pickup this afternoon?',
)

REVIEW_BODIES = (
    'Item was in good condition and the seller was easy to coordinate with.',
    'Smooth transaction, salamat po!',
    'The book is useful for class and matches the description.',
    'Mabilis kausap and maayos ang item. Thank you!',
    'Great experience. We met at the campus library on time.',
    'Good quality for the price. Would recommend.',
    'Maayos ang service at malinaw ang instructions.',
)


def _slug_part(value):
    return slugify(value.replace('Dela Cruz', 'Dela-Cruz'))


class Command(BaseCommand):
    help = 'Creates reproducible, tagged marketplace data for development/testing.'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true')
        parser.add_argument('--reset', action='store_true')
        parser.add_argument('--transactions', type=int, default=150)
        parser.add_argument('--days', type=int, default=90)
        parser.add_argument('--seed', type=int, default=2026)
        parser.add_argument('--password', default=SEED_PASSWORD)

    def handle(self, *args, **options):
        settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '')
        database = settings.DATABASES['default']
        self.stdout.write(f'Active settings: {settings_module}')
        self.stdout.write(f'Database NAME: {database.get("NAME")}')
        self.stdout.write(f'Database HOST: {database.get("HOST")}')

        if settings_module not in {
            'config.settings.development',
            'config.settings.testing',
        }:
            raise CommandError(
                'Refusing to run unless development or testing settings are active.'
            )

        if options['transactions'] < MIN_TRANSACTIONS:
            raise CommandError(
                f'--transactions must be at least {MIN_TRANSACTIONS} to include all required edge cases.'
            )
        if options['days'] < MIN_HISTORY_DAYS:
            raise CommandError(
                f'--days must be at least {MIN_HISTORY_DAYS} to preserve the older chart gaps.'
            )
        if options['reset'] and not options['confirm']:
            self.stdout.write('Reset dry run only; no rows were deleted.')

        with transaction.atomic():
            if options['reset']:
                self._reset_seed_data(confirm=options['confirm'])
                return

            existing = User.objects.filter(email__endswith=SEED_DOMAIN)
            if existing.exists():
                self.stdout.write(
                    'Seed-tagged accounts already exist; skipping without changes. '
                    'Use --reset --confirm to remove the seed set first.'
                )
                return

            categories = self._get_categories()
            self._print_plan(
                options,
                categories,
            )
            if not options['confirm']:
                self.stdout.write('Dry run only; no marketplace rows were created.')
                return

            rng = random.Random(options['seed'])
            users = self._create_users(options['password'])
            listings = self._create_listings(categories, users, rng, options['days'])
            created_requests, edge_ids = self._create_transactions(
                users,
                listings,
                rng,
                options['transactions'],
                options['days'],
            )
            self._create_reviews(users, created_requests, rng)
            self._print_summary(users, listings, created_requests, edge_ids)

    def _get_categories(self):
        categories = {category.slug: category for category in Category.objects.all()}
        if not categories:
            raise CommandError(
                'No Category rows exist. Add marketplace categories before seeding.'
            )
        missing = sorted({row[1] for row in LISTING_SPECS} - categories.keys())
        if missing:
            raise CommandError(
                f'Required existing categories are missing: {", ".join(missing)}. '
                'The command will not create categories.'
            )
        return categories

    def _print_plan(self, options, categories):
        self.stdout.write('Seed plan:')
        self.stdout.write('  Users: 15 total (6 sellers, 12 buyers, 3 shared accounts)')
        self.stdout.write(f'  Listings: {len(LISTING_SPECS)}')
        self.stdout.write(f'  Purchase requests: {options["transactions"]}')
        self.stdout.write(f'  History span: {options["days"]} days')
        self.stdout.write(f'  Random seed: {options["seed"]}')
        self.stdout.write(
            '  Existing categories: '
            + ', '.join(sorted(category.name for category in categories.values()))
        )
        self.stdout.write(
            '  Status weights: '
            + ', '.join(f'{status}={weight}%' for status, weight in STATUS_WEIGHTS)
        )
        self.stdout.write('  Seed tag: *@seed.usep.test')
        self.stdout.write('  Planned writes: users, seller profiles, listings, conversations, purchase requests, messages, reviews, and replies.')

    def _create_users(self, password):
        by_key = {}
        sellers = []
        buyers = []
        for index, (group, key, first_name, last_name, is_seller, active, deleted) in enumerate(USER_SPECS, 1):
            contact_num = self._available_contact_num(index)
            user = User(
                email=f'{key}{SEED_DOMAIN}',
                first_name=first_name,
                last_name=last_name,
                contact_num=contact_num,
                email_verified=True,
                is_first_login=False,
                is_active=active and not deleted,
                is_deleted=deleted,
                deleted_at=timezone.now() - timedelta(days=5) if deleted else None,
            )
            user.set_password(password)
            user.save()
            if is_seller:
                SellerProfile.objects.create(user=user)
                sellers.append(user)
            by_key[key] = user
            if group == 'buyer':
                buyers.append(user)

        # Three regular sellers are also buyers in the marketplace.
        buyers = [
            by_key['juan.garcia'],
            by_key['ana.cruz'],
            by_key['jose.reyes'],
            by_key['angelica.delacruz'],
            by_key['jericho.villanueva'],
            by_key['miguel.ramos'],
            by_key['sofia.flores'],
            by_key['paolo.navarro'],
            by_key['bianca.lim'],
            by_key['ethan.castillo'],
            by_key['grace.aquino'],
            by_key['rafael.torres'],
        ]
        return {
            'by_key': by_key,
            'sellers': sellers,
            'buyers': buyers,
            'repeat_canceller': by_key['juan.garcia'],
            'soft_deleted_buyer': by_key['ana.cruz'],
            'inactive_seller': by_key['jose.reyes'],
            'high_volume_seller': by_key['maria.santos'],
            'new_seller': by_key['liza.mendoza'],
        }

    def _available_contact_num(self, index):
        candidate = 970000000 + index
        while User.objects.filter(contact_num=f'09{candidate:09d}').exists():
            candidate += len(USER_SPECS)
        return f'09{candidate:09d}'

    def _create_listings(self, categories, users, rng, days):
        now = timezone.now()
        today = timezone.localtime(now, LOCAL_TIMEZONE).date()
        sellers = users['sellers']
        result = {}
        for index, (key, category_slug, title, price, condition) in enumerate(LISTING_SPECS):
            if index < 15:
                seller = sellers[0]
            elif index < 21:
                seller = sellers[1]
            elif index < 27:
                seller = sellers[2]
            elif index < 33:
                seller = sellers[3]
            elif index < 39:
                seller = sellers[4]
            else:
                seller = sellers[5]

            created_at = self._random_created_at(rng, today, days, allow_today=True)
            status = Listing.Status.ACTIVE
            lifecycle = Listing.Lifecycle.NORMAL
            recycled_at = None
            recycle_expires_at = None
            archived_at = None
            stock = rng.choice((1, 1, 1, 2, 3, 5, 8))
            if index % 9 == 6:
                status = Listing.Status.SOLD
                stock = 0
            if key in {'highvalue_focus', 'recycle_extra'}:
                lifecycle = Listing.Lifecycle.RECYCLE_BIN
                recycled_at = now - timedelta(days=2)
                recycle_expires_at = recycle_bin_deadline(recycled_at)
            if key == 'archive_transaction':
                lifecycle = Listing.Lifecycle.ARCHIVED
                status = Listing.Status.ARCHIVED
                archived_at = now - timedelta(days=10)

            listing = Listing(
                seller=seller,
                category=categories[category_slug],
                title=title,
                description=self._listing_description(title, category_slug),
                price=Decimal(price),
                condition=condition,
                location=rng.choice(LOCATIONS),
                status=status,
                stock_quantity=stock,
                views=rng.choice((0, 0, 2, 15, 40, 85, 160, 275, 400)),
                lifecycle_state=lifecycle,
                recycled_at=recycled_at,
                recycle_bin_expires_at=recycle_expires_at,
                archived_at=archived_at,
            )
            listing.save()
            Listing.objects.filter(pk=listing.pk).update(
                created_at=created_at,
                updated_at=min(
                    timezone.now(),
                    created_at + timedelta(minutes=rng.randint(5, 240)),
                ),
            )
            result[key] = listing
        return result

    @staticmethod
    def _listing_description(title, category_slug):
        if category_slug == 'services':
            return f'{title}. Please message to arrange a convenient schedule.'
        return f'{title}. Pre-owned campus marketplace item; see condition and arrange pickup.'

    @staticmethod
    def _weighted_hour(rng):
        return rng.choices(
            (2, 8, 11, 12, 16, 17, 18, 19, 21),
            weights=(1, 2, 5, 5, 4, 5, 5, 4, 1),
            k=1,
        )[0]

    def _random_created_at(self, rng, today, days, allow_today=False):
        available_offsets = list(range(1 if not allow_today else 0, days))
        day_offsets = [offset for offset in available_offsets if offset not in {40, 55}]
        weights = [3 if offset < 30 else 1 for offset in day_offsets]
        age = rng.choices(day_offsets, weights=weights, k=1)[0]
        local_day = today - timedelta(days=age)
        hour = self._weighted_hour(rng)
        candidate = timezone.make_aware(
            datetime.combine(local_day, time(hour, rng.randint(0, 59))),
            LOCAL_TIMEZONE,
        )
        return min(candidate, timezone.now() - timedelta(minutes=2))

    def _create_transactions(self, users, listings, rng, target_count, days):
        buyers = users['buyers']
        sellers = users['sellers'][:5]
        now = timezone.now()
        local_now = timezone.localtime(now, LOCAL_TIMEZONE)
        today = local_now.date()
        specs = []

        def add(status, age_days, *, listing=None, buyer=None, created_at=None, labels=(),
                schedule_kind='', price=None, quantity=1, note=None):
            if created_at is None:
                created_at = self._created_for_age(rng, today, age_days, now)
            if listing is None:
                listing = rng.choice(self._eligible_listings(listings, buyers))
            if buyer is None:
                candidates = [person for person in buyers if person.pk != listing.seller_id]
                buyer = rng.choice(candidates)
            if note is None and rng.random() < 0.30:
                note = rng.choice(BUYER_NOTES)
            specs.append({
                'status': status,
                'listing': listing,
                'buyer': buyer,
                'created_at': created_at,
                'labels': set(labels),
                'schedule_kind': schedule_kind,
                'price': Decimal(price) if price is not None else listing.price,
                'quantity': quantity,
                'note': note or '',
            })
            return specs[-1]

        # Three requests per Manila calendar day for the latest seven days.
        weekly = {
            -6: (PurchaseRequest.Status.REQUESTED, PurchaseRequest.Status.SUBMITTED, PurchaseRequest.Status.DECLINED),
            -5: (PurchaseRequest.Status.REQUESTED, PurchaseRequest.Status.CONFIRMED, PurchaseRequest.Status.CANCELLED),
            -4: (PurchaseRequest.Status.SUBMITTED, PurchaseRequest.Status.CONFIRMED, PurchaseRequest.Status.PROPOSED),
            -3: (PurchaseRequest.Status.REQUESTED, PurchaseRequest.Status.CONFIRMED, PurchaseRequest.Status.COMPLETED),
            -2: (PurchaseRequest.Status.SUBMITTED, PurchaseRequest.Status.CONFIRMED, PurchaseRequest.Status.COMPLETED),
            -1: (PurchaseRequest.Status.COMPLETED, PurchaseRequest.Status.PROPOSED, PurchaseRequest.Status.REQUESTED),
            0: (PurchaseRequest.Status.REQUESTED, PurchaseRequest.Status.SUBMITTED, PurchaseRequest.Status.REQUESTED),
        }
        weekly_specs = {}
        for age, statuses in weekly.items():
            for slot, status in enumerate(statuses):
                labels = set()
                schedule_kind = ''
                buyer = None
                listing = None
                created_at = None
                price = None
                if status in (PurchaseRequest.Status.REQUESTED, PurchaseRequest.Status.SUBMITTED) and age in {-6, -5, -4, -3, -2} and slot == 0:
                    labels.add('STALLED_PENDING')
                if status == PurchaseRequest.Status.CONFIRMED and age in {-5, -4, -3, -2}:
                    schedule_kind = 'past'
                    labels.add('STALLED_DELIVERY')
                if age == 0 and slot < 3:
                    labels.add('FRESH_PENDING')
                if age == -6 and slot == 2:
                    buyer = users['soft_deleted_buyer']
                    labels.add('SOFT_DELETED_BUYER')
                if age == -5 and slot == 1:
                    listing = self._listing_for_seller(listings, users['inactive_seller'])
                    labels.add('INACTIVE_SELLER')
                if age == -4 and slot == 2:
                    buyer = users['soft_deleted_buyer']
                    listing = self._listing_for_seller(listings, users['inactive_seller'])
                    labels.add('SOFT_DELETED_BUYER')
                    labels.add('INACTIVE_SELLER')
                if age == -3 and slot == 0:
                    buyer = users['soft_deleted_buyer']
                    labels.add('SOFT_DELETED_BUYER')
                if age == -6 and slot == 2:
                    listing = listings['recycle_extra']
                    labels.add('RECYCLE_BIN_TRANSACTION')
                if age == -3 and slot == 1:
                    listing = self._listing_for_seller(listings, users['inactive_seller'])
                    labels.add('INACTIVE_SELLER')
                if age == -1 and slot == 1:
                    listing = listings['archive_transaction']
                    labels.add('ARCHIVED_TRANSACTION')
                if age == -1 and slot == 2:
                    created_at = self._specific_local_time(today - timedelta(days=1), time(23, 59))
                    labels.add('TIMEZONE_BOUNDARY')
                    labels.add('FRESH_PENDING')
                    listing = listings['formula_title']
                    labels.add('FORMULA_INJECTION')
                if age == -1 and slot == 0:
                    listing = listings['long_title']
                    labels.add('LONG_TITLE')
                if age == -6 and slot == 1:
                    price = Decimal('4999.00')
                    labels.add('BELOW_HIGH_VALUE')
                if age == -5 and slot == 2:
                    price = Decimal('4500.00')
                    labels.add('BELOW_HIGH_VALUE')
                created = add(
                    status,
                    age,
                    listing=listing,
                    buyer=buyer,
                    created_at=created_at,
                    labels=labels,
                    schedule_kind=schedule_kind,
                    price=price,
                )
                weekly_specs[(age, slot)] = created

        utc_boundary_day = timezone.now().astimezone(datetime_timezone.utc).date() - timedelta(days=3)
        add(
            PurchaseRequest.Status.REQUESTED,
            3,
            created_at=self._specific_utc_time(utc_boundary_day, time(15, 30)),
            labels=('TIMEZONE_BOUNDARY',),
        )
        add(
            PurchaseRequest.Status.SUBMITTED,
            3,
            created_at=self._specific_utc_time(utc_boundary_day, time(16, 30)),
            labels=('TIMEZONE_BOUNDARY',),
        )

        # Future appointments remain confirmed and must not match stalled delivery.
        for age in (-1, 0, 0):
            add(
                PurchaseRequest.Status.CONFIRMED,
                age,
                schedule_kind='future',
                labels=('FUTURE_CONFIRMED',),
            )

        repeat_buyer = users['repeat_canceller']
        for age in (8, 14, 22, 29, 35):
            labels = {'REPEAT_CANCELLER'}
            if age <= 30:
                labels.add('REPEAT_CANCELLER_30D')
            add(
                PurchaseRequest.Status.CANCELLED,
                age,
                buyer=repeat_buyer,
                labels=labels,
            )

        # Join-inflation fixtures: 6 completed requests, 5 reviews; 3 completed
        # requests, 3 distinct reviewers; 4 requests and no reviews.
        for buyer in buyers[:6]:
            add(
                PurchaseRequest.Status.COMPLETED,
                rng.randint(12, min(days - 1, 28)),
                listing=listings['review_five'],
                buyer=buyer,
                labels=('JOIN_FIVE_REVIEWS',),
            )
        for buyer in buyers[6:9]:
            add(
                PurchaseRequest.Status.COMPLETED,
                rng.randint(12, min(days - 1, 28)),
                listing=listings['review_three'],
                buyer=buyer,
                labels=('JOIN_THREE_REVIEWS',),
            )
        for status in (
            PurchaseRequest.Status.CONFIRMED,
            PurchaseRequest.Status.SUBMITTED,
            PurchaseRequest.Status.CANCELLED,
            PurchaseRequest.Status.DECLINED,
        ):
            add(
                status,
                rng.randint(10, min(days - 1, 25)),
                listing=listings['highvalue_focus'],
                buyer=rng.choice([buyer for buyer in buyers if buyer.pk != listings['highvalue_focus'].seller_id]),
                labels=('HIGH_VALUE', 'JOIN_ZERO_REVIEWS'),
            )
        specs[-4]['note'] = '=SUM(1+1)'
        specs[-4]['labels'].add('FORMULA_INJECTION')
        specs[-1]['note'] = 'Please coordinate pickup. ' + ('The long note is for layout testing. ' * 13)
        specs[-1]['note'] = specs[-1]['note'][:500]
        specs[-1]['labels'].add('LONG_NOTE')

        for key, status in (
            ('laptop', PurchaseRequest.Status.COMPLETED),
            ('tablet', PurchaseRequest.Status.CONFIRMED),
            ('camera', PurchaseRequest.Status.SUBMITTED),
        ):
            add(
                status,
                rng.randint(10, min(days - 1, 25)),
                listing=listings[key],
                labels=('HIGH_VALUE',),
            )

        if len(specs) > target_count:
            raise CommandError(
                f'{target_count} transactions are not enough to fit the required fixed edge cases.'
            )

        eligible_listings = self._eligible_listings(listings, buyers)
        while len(specs) < target_count:
            status = rng.choices(
                [item[0] for item in STATUS_WEIGHTS],
                weights=[item[1] for item in STATUS_WEIGHTS],
                k=1,
            )[0]
            age = rng.randrange(0, days)
            while age in {40, 55}:
                age = rng.randrange(0, days)
            listing = rng.choice(eligible_listings)
            buyer = rng.choice([person for person in buyers if person.pk != listing.seller_id])
            add(status, age, listing=listing, buyer=buyer)

        if len(specs) > target_count:
            raise CommandError(
                f'{target_count} transactions are not enough to fit the required fixed edge cases.'
            )

        created = self._save_request_specs(specs, rng, now)
        edge_ids = defaultdict(list)
        for item in created:
            for label in item['labels']:
                edge_ids[label].append(item['purchase'].pk)
        return created, edge_ids

    @staticmethod
    def _eligible_listings(listings, buyers):
        new_seller_id = users_new_seller_id(listings)
        return [
            listing for listing in listings.values()
            if listing.seller_id != new_seller_id
            and listing.pk not in {
                listings['review_five'].pk,
                listings['review_three'].pk,
                listings['highvalue_focus'].pk,
            }
        ]

    @staticmethod
    def _listing_for_seller(listings, seller):
        matches = [listing for listing in listings.values() if listing.seller_id == seller.pk]
        if not matches:
            raise CommandError(f'No seeded listing belongs to seller {seller.email}.')
        return matches[0]

    @staticmethod
    def _created_for_age(rng, today, age_days, now):
        local_day = (
            today + timedelta(days=age_days)
            if age_days <= 0
            else today - timedelta(days=age_days)
        )
        if age_days == 0:
            return now - timedelta(minutes=rng.randint(5, 180))
        hour = rng.choices((2, 8, 11, 12, 16, 17, 18, 19, 21), (1, 2, 5, 5, 4, 5, 5, 4, 1), k=1)[0]
        return timezone.make_aware(
            datetime.combine(local_day, time(hour, rng.randint(0, 59))),
            LOCAL_TIMEZONE,
        )

    @staticmethod
    def _specific_local_time(day, local_time):
        return timezone.make_aware(datetime.combine(day, local_time), LOCAL_TIMEZONE)

    @staticmethod
    def _specific_utc_time(utc_day, utc_time):
        return datetime.combine(utc_day, utc_time, tzinfo=datetime_timezone.utc)

    def _save_request_specs(self, specs, rng, now):
        conversations = {}
        messages = []
        requests = []
        created = []
        receiver = message_signals.notify_recipient_of_new_message
        disconnected = post_save.disconnect(receiver=receiver, sender=Message)
        try:
            for spec in specs:
                buyer = spec['buyer']
                listing = spec['listing']
                key = (buyer.pk, listing.seller_id, listing.pk)
                conversation = conversations.get(key)
                if conversation is None:
                    conversation = Conversation.objects.create(
                        buyer=buyer,
                        seller=listing.seller,
                        listing=listing,
                    )
                    conversations[key] = conversation

                message = Message.objects.create(
                    conversation=conversation,
                    sender=listing.seller,
                    body=GENERIC_MESSAGE_BODY,
                    kind=Message.Kind.PURCHASE_REQUEST,
                    is_read=True,
                )
                submitted_at, responded_at, completed_at = self._timestamps_for_status(
                    spec['status'],
                    spec['created_at'],
                    now,
                    rng,
                )
                schedule = self._schedule_for_spec(spec, completed_at, now)
                purchase = PurchaseRequest.objects.create(
                    message=message,
                    conversation=conversation,
                    status=spec['status'],
                    is_service=listing.category.slug == 'services',
                    unit_price=spec['price'],
                    quantity=spec['quantity'],
                    total_amount=spec['price'] * spec['quantity'],
                    payment_method=rng.choice((
                        PurchaseRequest.PaymentMethod.GCASH,
                        PurchaseRequest.PaymentMethod.CASH,
                    )),
                    payment_reference='',
                    buyer_note=spec['note'],
                    **schedule,
                )
                if purchase.payment_method == PurchaseRequest.PaymentMethod.GCASH:
                    purchase.payment_reference = f'{rng.randrange(100000000000, 999999999999)}'
                    PurchaseRequest.objects.filter(pk=purchase.pk).update(
                        payment_reference=purchase.payment_reference,
                    )

                Message.objects.filter(pk=message.pk).update(
                    created_at=spec['created_at'],
                    updated_at=spec['created_at'],
                )
                PurchaseRequest.objects.filter(pk=purchase.pk).update(
                    created_at=spec['created_at'],
                    submitted_at=submitted_at,
                    responded_at=responded_at,
                    completed_at=completed_at,
                )
                created.append({
                    **spec,
                    'conversation': conversation,
                    'message': message,
                    'purchase': purchase,
                    'submitted_at': submitted_at,
                    'responded_at': responded_at,
                    'completed_at': completed_at,
                })
                messages.append(message)
                requests.append(purchase)
        finally:
            if disconnected:
                post_save.connect(receiver=receiver, sender=Message)

        for conversation in conversations.values():
            conversation_requests = [
                item for item in created if item['conversation'].pk == conversation.pk
            ]
            times = [item['created_at'] for item in conversation_requests]
            Conversation.objects.filter(pk=conversation.pk).update(
                created_at=min(times),
                updated_at=max(times),
            )
        return created

    @staticmethod
    def _timestamps_for_status(status, created_at, now, rng):
        duration = max(now - created_at, timedelta(minutes=2))
        submitted_at = responded_at = completed_at = None
        if status != PurchaseRequest.Status.REQUESTED:
            submitted_at = created_at + duration * 0.2
        if status in {
            PurchaseRequest.Status.CONFIRMED,
            PurchaseRequest.Status.DECLINED,
            PurchaseRequest.Status.CANCELLED,
            PurchaseRequest.Status.PROPOSED,
            PurchaseRequest.Status.COMPLETED,
        }:
            submitted_at = submitted_at or created_at + duration * 0.2
            responded_at = submitted_at + (now - submitted_at) * 0.45
        if status == PurchaseRequest.Status.COMPLETED:
            responded_at = responded_at or created_at + duration * 0.6
            completed_at = responded_at + (now - responded_at) * 0.6
        return submitted_at, responded_at, completed_at

    @staticmethod
    def _schedule_for_spec(spec, completed_at, now):
        status = spec['status']
        schedule_kind = spec['schedule_kind']
        if status == PurchaseRequest.Status.COMPLETED:
            scheduled_end = completed_at - timedelta(minutes=30)
            return {
                'scheduled_start': scheduled_end - timedelta(hours=1),
                'scheduled_end': scheduled_end,
            }
        if status == PurchaseRequest.Status.CONFIRMED:
            if schedule_kind == 'past':
                scheduled_end = now - timedelta(days=1)
                return {
                    'scheduled_start': scheduled_end - timedelta(hours=2),
                    'scheduled_end': scheduled_end,
                }
            return {
                'scheduled_start': now + timedelta(days=2),
                'scheduled_end': now + timedelta(days=2, hours=1),
            }
        if status == PurchaseRequest.Status.PROPOSED:
            start = now + timedelta(days=3)
            return {
                'proposed_start': start,
                'proposed_end': start + timedelta(hours=1),
                'proposed_by_id': spec['listing'].seller_id,
                'proposal_note': 'Proposed a convenient campus meeting time.',
            }
        return {}

    def _create_reviews(self, users, created_requests, rng):
        completed = [
            item for item in created_requests
            if item['status'] == PurchaseRequest.Status.COMPLETED
        ]
        guaranteed = []
        five_listing = next(
            item['listing'] for item in created_requests
            if 'JOIN_FIVE_REVIEWS' in item['labels']
        )
        three_listing = next(
            item['listing'] for item in created_requests
            if 'JOIN_THREE_REVIEWS' in item['labels']
        )
        for listing, expected_count in ((five_listing, 5), (three_listing, 3)):
            matches = [
                item for item in completed
                if item['listing'].pk == listing.pk
            ]
            guaranteed.extend(matches[:expected_count])

        candidates = list(guaranteed)
        guaranteed_keys = {(item['listing'].pk, item['buyer'].pk) for item in guaranteed}
        fixed_review_listing_ids = {five_listing.pk, three_listing.pk}
        for item in completed:
            key = (item['listing'].pk, item['buyer'].pk)
            if (
                item['listing'].pk not in fixed_review_listing_ids
                and key not in guaranteed_keys
                and rng.random() < 0.40
            ):
                candidates.append(item)

        reviewed = set()
        reviews_by_listing = defaultdict(list)
        for review_index, item in enumerate(candidates):
            listing = item['listing']
            buyer = item['buyer']
            key = (listing.pk, buyer.pk)
            if key in reviewed:
                continue
            reviewed.add(key)
            completion_time = item['completed_at'] or item['created_at']
            possible_date = min(completion_time + timedelta(hours=rng.randint(1, 72)), timezone.now())
            review = ListingReview.objects.create(
                listing=listing,
                reviewer=buyer,
                rating=rng.choices((1, 2, 3, 4, 5), (2, 3, 8, 30, 57), k=1)[0],
                body=rng.choice(REVIEW_BODIES),
            )
            ListingReview.objects.filter(pk=review.pk).update(
                created_at=possible_date,
                updated_at=possible_date,
            )
            reviews_by_listing[listing.pk].append(review)

        reply_index = 0
        for listing_id, reviews in reviews_by_listing.items():
            for review in reviews:
                force_reply = reply_index < 3
                force_back_and_forth = reply_index < 2
                reply_index += 1
                if force_reply or rng.random() < 0.40:
                    seller = review.listing.seller
                    ListingReviewReply.objects.create(
                        review=review,
                        author=seller,
                        body=rng.choice((
                            'Thank you for your review!',
                            'Salamat po, glad the item worked well for you.',
                            'Thanks for choosing my listing.',
                        )),
                    )
                    if force_back_and_forth or rng.random() < 0.20:
                        ListingReviewReply.objects.create(
                            review=review,
                            author=review.reviewer,
                            body='Thank you for the quick coordination.',
                        )

    def _print_summary(self, users, listings, created, edge_ids):
        self.stdout.write(f'Created users: {len(users["by_key"])}')
        self.stdout.write(f'Created seller profiles: {len(users["sellers"])}')
        self.stdout.write(f'Created listings: {len(listings)}')
        self.stdout.write(f'Created purchase requests: {len(created)}')
        self.stdout.write(f'Created conversations: {Conversation.objects.filter(buyer__email__endswith=SEED_DOMAIN).count()}')
        self.stdout.write(f'Created messages: {Message.objects.filter(sender__email__endswith=SEED_DOMAIN, body=GENERIC_MESSAGE_BODY).count()}')
        self.stdout.write(f'Created reviews: {ListingReview.objects.filter(reviewer__email__endswith=SEED_DOMAIN).count()}')
        self.stdout.write(f'Created replies: {ListingReviewReply.objects.filter(author__email__endswith=SEED_DOMAIN).count()}')
        self.stdout.write(f'High-volume seller: {users["high_volume_seller"].email}')
        self.stdout.write(f'Brand-new seller with no transactions: {users["new_seller"].email}')
        self.stdout.write(f'Soft-deleted buyer: {users["soft_deleted_buyer"].email}')
        self.stdout.write(f'Inactive seller: {users["inactive_seller"].email}')
        for label in (
            'STALLED_PENDING', 'FRESH_PENDING', 'STALLED_DELIVERY',
            'FUTURE_CONFIRMED', 'HIGH_VALUE', 'REPEAT_CANCELLER',
            'TIMEZONE_BOUNDARY', 'SOFT_DELETED_BUYER', 'INACTIVE_SELLER',
            'JOIN_FIVE_REVIEWS', 'JOIN_THREE_REVIEWS', 'JOIN_ZERO_REVIEWS',
            'BELOW_HIGH_VALUE', 'FORMULA_INJECTION', 'RECYCLE_BIN_TRANSACTION',
            'ARCHIVED_TRANSACTION', 'LONG_TITLE', 'LONG_NOTE',
        ):
            self.stdout.write(f'{label} transaction IDs: {", ".join(map(str, edge_ids.get(label, [])))}')
        for age in range(6, -1, -1):
            day = timezone.localdate(timezone=LOCAL_TIMEZONE) - timedelta(days=age)
            ids = []
            for item in created:
                if timezone.localtime(item['created_at'], LOCAL_TIMEZONE).date() == day:
                    ids.append(item['purchase'].pk)
            self.stdout.write(f'CHART {day.isoformat()} transaction IDs: {", ".join(map(str, ids))}')
        for age in (40, 55):
            day = timezone.localdate(timezone=LOCAL_TIMEZONE) - timedelta(days=age)
            self.stdout.write(f'CHART GAP {day.isoformat()} transaction IDs: none')

    def _reset_seed_data(self, confirm):
        from django.db.models import Q
        from apps.messaging.models import (
            Conversation as MessagingConversation,
            ConversationReadState,
            ConversationTypingState,
            ConversationUserState,
            MessageAttachment,
            MessageRevision,
        )

        users = User.objects.filter(email__endswith=SEED_DOMAIN)
        user_ids = list(users.values_list('pk', flat=True))
        listing_ids = list(Listing.objects.filter(seller_id__in=user_ids).values_list('pk', flat=True))
        conversation_ids = list(MessagingConversation.objects.filter(
            models_q(user_ids, listing_ids)
        ).values_list('pk', flat=True))
        reviews = ListingReview.objects.filter(
            models_q(user_ids, listing_ids, review=True)
        )

        counts = {
            'users': users.count(),
            'seller profiles': SellerProfile.objects.filter(user_id__in=user_ids).count(),
            'listings': Listing.objects.filter(pk__in=listing_ids).count(),
            'listing images': ListingImage.objects.filter(listing_id__in=listing_ids).count(),
            'conversations': MessagingConversation.objects.filter(pk__in=conversation_ids).count(),
            'purchase requests': PurchaseRequest.objects.filter(conversation_id__in=conversation_ids).count(),
            'messages': Message.objects.filter(conversation_id__in=conversation_ids).count(),
            'message attachments': MessageAttachment.objects.filter(message__conversation_id__in=conversation_ids).count(),
            'message revisions': MessageRevision.objects.filter(message__conversation_id__in=conversation_ids).count(),
            'conversation states': ConversationUserState.objects.filter(conversation_id__in=conversation_ids).count(),
            'conversation read states': ConversationReadState.objects.filter(conversation_id__in=conversation_ids).count(),
            'conversation typing states': ConversationTypingState.objects.filter(conversation_id__in=conversation_ids).count(),
            'reviews': reviews.count(),
            'review replies': ListingReviewReply.objects.filter(review__in=reviews).count(),
            'review photos': ListingReviewPhoto.objects.filter(review__in=reviews).count(),
            'review notifications': ReviewNotification.objects.filter(reply__review__in=reviews).count(),
            'saved items': SavedItem.objects.filter(
                Q(listing_id__in=listing_ids) | Q(buyer_id__in=user_ids)
            ).count(),
        }
        non_seed_review_count = reviews.exclude(reviewer_id__in=user_ids).count()
        non_seed_reply_count = ListingReviewReply.objects.filter(
            review__in=reviews,
        ).exclude(author_id__in=user_ids).count()
        non_seed_message_count = Message.objects.filter(
            conversation_id__in=conversation_ids,
        ).exclude(sender_id__in=user_ids).count()
        non_seed_participant_count = MessagingConversation.objects.filter(
            pk__in=conversation_ids,
        ).exclude(buyer_id__in=user_ids, seller_id__in=user_ids).count()
        non_seed_saved_item_count = SavedItem.objects.filter(
            listing_id__in=listing_ids,
        ).exclude(buyer_id__in=user_ids).count()
        non_seed_state_count = (
            ConversationUserState.objects.filter(conversation_id__in=conversation_ids)
            .exclude(user_id__in=user_ids)
            .count()
            + ConversationReadState.objects.filter(conversation_id__in=conversation_ids)
            .exclude(user_id__in=user_ids)
            .count()
            + ConversationTypingState.objects.filter(conversation_id__in=conversation_ids)
            .exclude(user_id__in=user_ids)
            .count()
        )
        non_seed_notification_count = ReviewNotification.objects.filter(
            reply__review__in=reviews,
        ).exclude(recipient_id__in=user_ids).count()
        self.stdout.write('Seed reset impact:')
        for label, count in counts.items():
            self.stdout.write(f'  {label}: {count}')
        self.stdout.write(f'  non-seed-user reviews on seed listings: {non_seed_review_count} (will cascade; reported)')
        self.stdout.write(f'  non-seed-user replies on seed reviews: {non_seed_reply_count}')
        self.stdout.write(f'  non-seed-user messages in seed conversations: {non_seed_message_count}')
        self.stdout.write(f'  conversations with non-seed participants: {non_seed_participant_count}')
        self.stdout.write(f'  non-seed-user saved items on seed listings: {non_seed_saved_item_count}')
        self.stdout.write(f'  non-seed-user conversation states: {non_seed_state_count}')
        self.stdout.write(f'  non-seed-user review notifications on seed reviews: {non_seed_notification_count}')
        if not confirm:
            self.stdout.write('Reset dry run only; no rows were deleted.')
            return
        if (
            non_seed_reply_count
            or non_seed_message_count
            or non_seed_participant_count
            or non_seed_saved_item_count
            or non_seed_state_count
            or non_seed_notification_count
        ):
            raise CommandError(
                'Reset aborted because it would delete data authored by or belonging to a non-seed user.'
            )
        users.delete()
        self.stdout.write('Deleted only users with the @seed.usep.test email domain.')
        self.stdout.write('Seed reset completed; related rows were removed by the existing cascade relationships.')


def users_new_seller_id(listings):
    seller_counts = defaultdict(int)
    for listing in listings.values():
        seller_counts[listing.seller_id] += 1
    return min(seller_counts, key=seller_counts.get) if seller_counts else None


def models_q(user_ids, listing_ids, review=False):
    from django.db.models import Q
    if review:
        return Q(reviewer_id__in=user_ids) | Q(listing_id__in=listing_ids)
    return (
        Q(buyer_id__in=user_ids)
        | Q(seller_id__in=user_ids)
        | Q(listing_id__in=listing_ids)
    )
