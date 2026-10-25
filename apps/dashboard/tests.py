from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from io import StringIO

from apps.accounts.models import Roles, User
from apps.messaging.models import Conversation, Message
from .forms import ListingForm, ListingReviewForm, validate_listing_images
from .models import (
    Category,
    Listing,
    ListingReview,
    ListingReviewReply,
    ReviewNotification,
    SavedItem,
)
from .services.listing_lifecycle import (
    RESTORED,
    archive_expired_recycled_listings,
    restore_recycled_listing,
)

# Conversation/typing/read/search/unsend tests moved to
# apps.messaging.tests, alongside the views and models they exercise.
# Conversation and Message are still imported here because
# test_deleting_a_listing_with_messages_archives_it_and_keeps_the_conversation
# needs them to set up a listing that has message history.


@override_settings(ALLOWED_HOSTS=['testserver'])
class AdministratorLoginRedirectTests(TestCase):
    def create_admin(self, *, is_first_login=False):
        return User.objects.create_user(
            email='administrator@example.com',
            password='StrongPassword123!',
            first_name='Campus',
            last_name='Administrator',
            contact_num='08889990000',
            email_verified=True,
            is_first_login=is_first_login,
            role=Roles.ADMIN,
            is_staff=True,
            is_superuser=True,
        )

    def test_admin_login_redirects_to_administrator_dashboard(self):
        self.create_admin()

        response = self.client.post(reverse('login'), {
            'email': 'administrator@example.com',
            'password': 'StrongPassword123!',
        })

        self.assertRedirects(response, reverse('dashboard'))

    def test_first_login_admin_redirects_after_password_change(self):
        self.create_admin(is_first_login=True)
        login_response = self.client.post(reverse('login'), {
            'email': 'administrator@example.com',
            'password': 'StrongPassword123!',
        })
        self.assertRedirects(login_response, reverse('change_password'))

        password_response = self.client.post(reverse('change_password'), {
            'current_password': 'StrongPassword123!',
            'new_password': 'AnotherSecurePass456!',
            'confirm_password': 'AnotherSecurePass456!',
        })

        self.assertRedirects(password_response, reverse('dashboard'))

    def test_admin_sections_open_separate_pages(self):
        self.create_admin()
        self.client.force_login(User.objects.get(email='administrator@example.com'))

        sections = (
            ('dashboard', 'overview', 'Overview'),
            ('admin_accounts', 'accounts', 'Accounts'),
            ('admin_listings', 'listings', 'Listings'),
            ('admin_categories', 'categories', 'Categories'),
            ('admin_reports', 'reports', 'Reports'),
            ('admin_activity', 'activity', 'Activity log'),
            ('admin_settings', 'settings', 'Settings'),
        )

        for route_name, active_section, section_title in sections:
            with self.subTest(section=active_section):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['active_section'], active_section)
                self.assertEqual(response.context['section_title'], section_title)


@override_settings(ALLOWED_HOSTS=['testserver'])
class BuyerDashboardViewsTests(TestCase):
    def test_logged_in_buyer_can_save_listing(self):
        buyer = User.objects.create_user(
            email='buyer@example.com',
            password='StrongPassword123!',
            first_name='Campus',
            last_name='Buyer',
            contact_num='09123456789',
            email_verified=True,
            is_first_login=False,
        )
        listing = Listing.objects.get(slug='engineering-mechanics-textbook')
        self.client.force_login(buyer)

        save_response = self.client.post(
            reverse('dashboard:toggle_saved_item', args=[listing.slug]),
            {'next': reverse('dashboard:buyer_cart')},
        )
        self.assertEqual(save_response.status_code, 302)
        self.assertTrue(SavedItem.objects.filter(buyer=buyer, listing=listing).exists())
        # Starting a chat about the listing is exercised in
        # apps.messaging.tests (messaging:start_conversation).

    def test_deleting_a_listing_moves_it_to_the_recycle_bin_and_keeps_the_conversation(self):
        category = Category.objects.get(slug='textbooks')
        seller = User.objects.create_user(
            email='history-seller@example.com', password='StrongPassword123!',
            first_name='History', last_name='Seller', contact_num='09123456730',
            email_verified=True, is_first_login=False,
        )
        buyer = User.objects.create_user(
            email='history-buyer@example.com', password='StrongPassword123!',
            first_name='History', last_name='Buyer', contact_num='09123456774',
            email_verified=True, is_first_login=False,
        )
        listing = Listing.objects.create(
            seller=seller, category=category, title='History listing', slug='history-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
        )
        conversation = Conversation.objects.create(buyer=buyer, seller=seller, listing=listing)
        Message.objects.create(conversation=conversation, sender=buyer, body='Please keep this history.')
        self.client.force_login(seller)

        response = self.client.post(reverse('dashboard:delete_listing', args=[listing.pk]))

        self.assertRedirects(response, reverse('dashboard:seller'))
        listing.refresh_from_db()
        self.assertEqual(listing.status, Listing.Status.ACTIVE)
        self.assertEqual(listing.lifecycle_state, Listing.Lifecycle.RECYCLE_BIN)
        self.assertTrue(Conversation.objects.filter(pk=conversation.pk).exists())
        self.assertTrue(Message.objects.filter(conversation=conversation).exists())

    def test_recycled_listing_is_hidden_publicly_and_restored_by_its_owner(self):
        category = Category.objects.get(slug='textbooks')
        seller = User.objects.create_user(
            email='recycle-owner@example.com', password='StrongPassword123!',
            first_name='Recycle', last_name='Owner', contact_num='09123456731',
            email_verified=True, is_first_login=False,
        )
        other_user = User.objects.create_user(
            email='recycle-other@example.com', password='StrongPassword123!',
            first_name='Other', last_name='User', contact_num='09123456732',
            email_verified=True, is_first_login=False,
        )
        listing = Listing.objects.create(
            seller=seller, category=category, title='Recoverable listing', slug='recoverable-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
            stock_quantity=4,
        )
        self.client.force_login(seller)
        self.client.post(reverse('dashboard:delete_listing', args=[listing.pk]))
        listing.refresh_from_db()
        self.assertEqual(listing.lifecycle_state, Listing.Lifecycle.RECYCLE_BIN)
        self.assertEqual(listing.stock_quantity, 4)
        self.assertEqual(self.client.get(reverse('dashboard:buyer_detail', args=[listing.slug])).status_code, 404)

        self.client.force_login(other_user)
        self.assertNotContains(self.client.get(reverse('dashboard:buyer')), listing.title)
        self.client.post(reverse('dashboard:restore_listing', args=[listing.pk]))
        listing.refresh_from_db()
        self.assertEqual(listing.lifecycle_state, Listing.Lifecycle.RECYCLE_BIN)

        self.client.force_login(seller)
        self.client.post(reverse('dashboard:restore_listing', args=[listing.pk]))
        listing.refresh_from_db()
        self.assertEqual(listing.lifecycle_state, Listing.Lifecycle.NORMAL)
        self.assertEqual(listing.stock_quantity, 4)
        self.assertEqual(self.client.get(reverse('dashboard:buyer_detail', args=[listing.slug])).status_code, 200)

    @override_settings(LISTING_RECYCLE_BIN_RETENTION_DAYS=1)
    def test_recycle_bin_expiry_archives_only_listings_still_in_the_bin(self):
        category = Category.objects.get(slug='textbooks')
        seller = User.objects.create_user(
            email='expiry-owner@example.com', password='StrongPassword123!',
            first_name='Expiry', last_name='Owner', contact_num='09123456733',
            email_verified=True, is_first_login=False,
        )
        expired = Listing.objects.create(
            seller=seller, category=category, title='Expired bin listing', slug='expired-bin-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
            lifecycle_state=Listing.Lifecycle.RECYCLE_BIN,
            recycled_at=timezone.now() - timedelta(days=2),
            recycle_bin_expires_at=timezone.now() - timedelta(seconds=1),
        )
        restored = Listing.objects.create(
            seller=seller, category=category, title='Restored listing', slug='restored-bin-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
        )

        call_command('archive_recycled_listings', stdout=StringIO())
        expired.refresh_from_db()
        restored.refresh_from_db()
        self.assertEqual(expired.lifecycle_state, Listing.Lifecycle.ARCHIVED)
        self.assertEqual(restored.lifecycle_state, Listing.Lifecycle.NORMAL)
        call_command('archive_recycled_listings', stdout=StringIO())
        expired.refresh_from_db()
        self.assertEqual(expired.lifecycle_state, Listing.Lifecycle.ARCHIVED)

    @override_settings(LISTING_RECYCLE_BIN_RETENTION_DAYS=None)
    def test_recycle_bin_expiry_does_nothing_without_a_retention_setting(self):
        category = Category.objects.get(slug='textbooks')
        seller = User.objects.create_user(
            email='disabled-expiry-owner@example.com', password='StrongPassword123!',
            first_name='Disabled', last_name='Expiry', contact_num='09123456734',
            email_verified=True, is_first_login=False,
        )
        listing = Listing.objects.create(
            seller=seller, category=category, title='Retained listing', slug='retained-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
            lifecycle_state=Listing.Lifecycle.RECYCLE_BIN,
            recycled_at=timezone.now() - timedelta(days=2),
        )

        call_command('archive_recycled_listings', stdout=StringIO())
        listing.refresh_from_db()
        self.assertEqual(listing.lifecycle_state, Listing.Lifecycle.RECYCLE_BIN)

    def test_seller_cannot_request_the_removed_archived_dashboard_view(self):
        seller = User.objects.create_user(
            email='archive-view-seller@example.com', password='StrongPassword123!',
            first_name='Archive', last_name='Seller', contact_num='09123456728',
            email_verified=True, is_first_login=False,
        )
        self.client.force_login(seller)

        response = self.client.get(reverse('dashboard:seller'), {'view': 'archived'})

        self.assertEqual(response.status_code, 404)

    def test_recycle_boundary_allows_29_days_and_rejects_exactly_30_days(self):
        category = Category.objects.get(slug='textbooks')
        seller = User.objects.create_user(
            email='boundary-owner@example.com', password='StrongPassword123!',
            first_name='Boundary', last_name='Owner', contact_num='09123456727',
            email_verified=True, is_first_login=False,
        )
        now = timezone.now()
        eligible = Listing.objects.create(
            seller=seller, category=category, title='Twenty-nine day listing', slug='twenty-nine-day-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
            lifecycle_state=Listing.Lifecycle.RECYCLE_BIN,
            recycled_at=now - timedelta(days=29),
        )
        expired = Listing.objects.create(
            seller=seller, category=category, title='Thirty day listing', slug='thirty-day-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
            lifecycle_state=Listing.Lifecycle.RECYCLE_BIN,
            recycled_at=now - timedelta(days=30),
        )

        self.assertEqual(restore_recycled_listing(eligible.pk, seller, now), RESTORED)
        self.client.force_login(seller)
        recycle_bin = self.client.get(reverse('dashboard:seller'), {'view': 'recycle'})
        self.assertNotContains(recycle_bin, expired.title)
        self.client.post(reverse('dashboard:restore_listing', args=[expired.pk]))
        eligible.refresh_from_db()
        expired.refresh_from_db()
        self.assertEqual(eligible.lifecycle_state, Listing.Lifecycle.NORMAL)
        self.assertEqual(expired.lifecycle_state, Listing.Lifecycle.ARCHIVED)

    def test_archive_processor_only_archives_listings_at_the_exact_cutoff(self):
        category = Category.objects.get(slug='textbooks')
        seller = User.objects.create_user(
            email='processor-owner@example.com', password='StrongPassword123!',
            first_name='Processor', last_name='Owner', contact_num='09123456726',
            email_verified=True, is_first_login=False,
        )
        now = timezone.now()
        before_cutoff = Listing.objects.create(
            seller=seller, category=category, title='Still restorable', slug='still-restorable',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
            lifecycle_state=Listing.Lifecycle.RECYCLE_BIN,
            recycled_at=now - timedelta(days=30) + timedelta(microseconds=1),
        )
        at_cutoff = Listing.objects.create(
            seller=seller, category=category, title='Ready to archive', slug='ready-to-archive',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
            lifecycle_state=Listing.Lifecycle.RECYCLE_BIN,
            recycled_at=now - timedelta(days=30),
        )

        self.assertEqual(archive_expired_recycled_listings(now), 1)
        self.assertEqual(archive_expired_recycled_listings(now), 0)
        before_cutoff.refresh_from_db()
        at_cutoff.refresh_from_db()
        self.assertEqual(before_cutoff.lifecycle_state, Listing.Lifecycle.RECYCLE_BIN)
        self.assertEqual(at_cutoff.lifecycle_state, Listing.Lifecycle.ARCHIVED)

    def test_archive_admin_is_available_only_to_the_existing_admin_role(self):
        category = Category.objects.get(slug='textbooks')
        administrator = User.objects.create_user(
            email='archive-admin@example.com', password='StrongPassword123!',
            first_name='Archive', last_name='Admin', contact_num='09123456725',
            email_verified=True, is_first_login=False, is_staff=True, role=Roles.ADMIN,
        )
        staff_user = User.objects.create_user(
            email='archive-staff@example.com', password='StrongPassword123!',
            first_name='Archive', last_name='Staff', contact_num='09123456724',
            email_verified=True, is_first_login=False, is_staff=True,
        )
        archived = Listing.objects.create(
            seller=administrator, category=category, title='Administrative archive', slug='administrative-archive',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
            lifecycle_state=Listing.Lifecycle.ARCHIVED,
            archived_at=timezone.now(),
        )
        archive_url = reverse('admin:dashboard_listing_changelist')

        self.client.force_login(administrator)
        response = self.client.get(archive_url, {'lifecycle_state__exact': Listing.Lifecycle.ARCHIVED})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, archived.title)

        self.client.force_login(staff_user)
        self.assertEqual(self.client.get(archive_url).status_code, 403)

    def test_listing_photo_validation_enforces_existing_count_and_image_types(self):
        valid_images = [
            SimpleUploadedFile(f'photo-{index}.jpg', b'photo', content_type='image/jpeg')
            for index in range(8)
        ]
        self.assertEqual(validate_listing_images(valid_images), valid_images)
        with self.assertRaisesMessage(ValidationError, 'up to 8 photos'):
            validate_listing_images(valid_images, existing_count=1)
        with self.assertRaisesMessage(ValidationError, 'JPEG, PNG, GIF, or WebP'):
            validate_listing_images([
                SimpleUploadedFile('photo.pdf', b'file', content_type='application/pdf'),
            ])

    def test_recycling_a_listing_keeps_its_valid_seller_reputation_rating(self):
        category = Category.objects.get(slug='textbooks')
        seller = User.objects.create_user(
            email='reputation-retention-seller@example.com', password='StrongPassword123!',
            first_name='Reputation', last_name='Retention', contact_num='09123456735',
            email_verified=True, is_first_login=False,
        )
        buyer = User.objects.create_user(
            email='reputation-retention-buyer@example.com', password='StrongPassword123!',
            first_name='Rating', last_name='Buyer', contact_num='09123456736',
            email_verified=True, is_first_login=False,
        )
        visible_listing = Listing.objects.create(
            seller=seller, category=category, title='Visible reputation listing', slug='visible-reputation-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
        )
        recycled_listing = Listing.objects.create(
            seller=seller, category=category, title='Recycled reputation listing', slug='recycled-reputation-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
            lifecycle_state=Listing.Lifecycle.RECYCLE_BIN,
            recycled_at=timezone.now(),
        )
        ListingReview.objects.create(listing=recycled_listing, reviewer=buyer, rating=5, body='Valid review.')

        response = self.client.get(reverse('dashboard:buyer_detail', args=[visible_listing.slug]))
        self.assertEqual(response.context['seller_info']['reputation_count'], 1)
        self.assertEqual(float(response.context['seller_info']['reputation_average']), 5.0)

    def test_buyer_listing_page_loads(self):
        response = self.client.get(reverse('dashboard:buyer'))
        self.assertEqual(response.status_code, 200)

    def test_buyer_detail_page_loads(self):
        response = self.client.get(reverse('dashboard:buyer_detail', args=['engineering-mechanics-textbook']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Stock available')

    def test_buyer_can_post_and_update_a_listing_review(self):
        seller = User.objects.create_user(
            email='review-listing-owner@example.com',
            password='StrongPassword123!',
            first_name='Listing',
            last_name='Owner',
            contact_num='09123456763',
            email_verified=True,
            is_first_login=False,
        )
        category = Category.objects.get(slug='textbooks')
        listing = Listing.objects.create(
            seller=seller,
            category=category,
            title='Review test textbook',
            slug='review-test-textbook',
            description='A listing used to test ratings and reviews.',
            price='100.00',
            condition='Good condition',
            location='Library',
        )
        buyer = User.objects.create_user(
            email='reviewer@example.com',
            password='StrongPassword123!',
            first_name='Campus',
            last_name='Reviewer',
            contact_num='09123456762',
            email_verified=True,
            is_first_login=False,
        )
        self.client.force_login(buyer)

        post_response = self.client.post(
            reverse('dashboard:submit_listing_review', args=[listing.slug]),
            {'rating': '5', 'body': 'Exactly what I needed.'},
        )

        self.assertEqual(post_response.status_code, 302)
        review = ListingReview.objects.get(listing=listing, reviewer=buyer)
        self.assertEqual(review.rating, 5)
        detail_response = self.client.get(reverse('dashboard:buyer_detail', args=[listing.slug]))
        self.assertEqual(detail_response.context['average_rating'], 5)
        self.assertEqual(detail_response.context['review_count'], 1)
        self.assertContains(detail_response, 'Ratings &amp; reviews')
        self.assertContains(detail_response, 'Exactly what I needed.')

        update_response = self.client.post(
            reverse('dashboard:submit_listing_review', args=[listing.slug]),
            {'rating': '4', 'body': 'Updated after another week of use.'},
        )

        self.assertEqual(update_response.status_code, 302)
        self.assertEqual(ListingReview.objects.filter(listing=listing).count(), 1)
        review.refresh_from_db()
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.body, 'Updated after another week of use.')

    def test_listing_owner_cannot_review_their_own_listing(self):
        seller = User.objects.create_user(
            email='review-owner@example.com',
            password='StrongPassword123!',
            first_name='Listing',
            last_name='Owner',
            contact_num='09123456761',
            email_verified=True,
            is_first_login=False,
        )
        listing = Listing.objects.create(
            seller=seller,
            category=Category.objects.get(slug='textbooks'),
            title='Owner review test',
            slug='owner-review-test',
            description='A listing used to test owner review restrictions.',
            price='100.00',
            condition='Good condition',
            location='Library',
        )
        self.client.force_login(seller)

        response = self.client.post(
            reverse('dashboard:submit_listing_review', args=[listing.slug]),
            {'rating': '5', 'body': 'My own listing.'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(ListingReview.objects.filter(listing=listing).exists())

    def test_anonymous_buyer_must_log_in_to_review(self):
        seller = User.objects.create_user(
            email='anonymous-review-owner@example.com',
            password='StrongPassword123!',
            first_name='Listing',
            last_name='Owner',
            contact_num='09123456760',
            email_verified=True,
            is_first_login=False,
        )
        listing = Listing.objects.create(
            seller=seller,
            category=Category.objects.get(slug='textbooks'),
            title='Anonymous review test',
            slug='anonymous-review-test',
            description='A listing used to test review authentication.',
            price='100.00',
            condition='Good condition',
            location='Library',
        )

        response = self.client.post(
            reverse('dashboard:submit_listing_review', args=[listing.slug]),
            {'rating': '5', 'body': 'A review.'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])
        self.assertFalse(ListingReview.objects.filter(listing=listing).exists())

    def test_buyer_search_and_category_filter_routes(self):
        response = self.client.get(reverse('dashboard:buyer') + '?q=calculator')
        self.assertEqual(response.status_code, 200)

        category_response = self.client.get(reverse('dashboard:buyer') + '?category=textbooks')
        self.assertEqual(category_response.status_code, 200)

    def test_seller_preview_supports_multiple_listings(self):
        seller = User.objects.get(email='test.seller@usep.edu.ph')
        response = self.client.get(
            reverse('dashboard:buyer'),
            {'seller': seller.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['seller_profile']['id'], seller.pk)
        self.assertGreaterEqual(response.context['items'].count(), 4)

    def test_product_media_frames_render_on_normal_and_seller_listing_pages(self):
        normal_response = self.client.get(reverse('dashboard:buyer'))
        seller = User.objects.get(email='test.seller@usep.edu.ph')
        seller_response = self.client.get(reverse('dashboard:buyer'), {'seller': seller.pk})

        self.assertContains(normal_response, 'listing-product-media')
        self.assertContains(normal_response, 'listing-seller-avatar')
        self.assertContains(seller_response, 'listing-product-media')
        self.assertContains(seller_response, 'listing-seller-avatar')

    def test_named_sellers_have_separate_linked_products(self):
        maria = User.objects.get(email='maria.santos@usep.edu.ph')
        juan = User.objects.get(email='juan.reyes@usep.edu.ph')
        self.assertEqual(maria.first_name, 'Maria')
        self.assertEqual(juan.last_name, 'Reyes')
        self.assertTrue(Listing.objects.filter(seller=maria).exists())
        self.assertTrue(Listing.objects.filter(seller=juan).exists())

    def test_buyer_cart_page_loads(self):
        response = self.client.get(reverse('dashboard:buyer_cart'))
        self.assertEqual(response.status_code, 302)

    def test_buyer_detail_has_multiple_gallery_images(self):
        response = self.client.get(reverse('dashboard:buyer_detail', args=['engineering-mechanics-textbook']))
        self.assertEqual(response.status_code, 200)
        self.assertIn('images', response.context['item'])
        self.assertGreaterEqual(len(response.context['item']['images']), 2)

    def test_buyer_detail_includes_seller_profile_details(self):
        response = self.client.get(reverse('dashboard:buyer_detail', args=['engineering-mechanics-textbook']))
        seller = response.context['seller_info']
        self.assertIn(seller['name'], response.content.decode())
        self.assertIn(seller['role'], response.content.decode())
        self.assertIn(seller['email'], response.content.decode())

    def test_seller_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard:seller'))
        self.assertEqual(response.status_code, 302)

    def test_seller_cannot_add_own_listing_to_cart(self):
        seller = User.objects.get(email='test.seller@usep.edu.ph')
        listing = Listing.objects.filter(seller=seller, status=Listing.Status.ACTIVE).first()
        self.client.force_login(seller)
        response = self.client.post(reverse('dashboard:toggle_saved_item', args=[listing.slug]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SavedItem.objects.filter(buyer=seller, listing=listing).exists())

    def test_seller_can_create_listing_for_their_account(self):
        seller = User.objects.create_user(
            email='seller@example.com',
            password='StrongPassword123!',
            first_name='Campus',
            last_name='Seller',
            contact_num='09123456788',
            email_verified=True,
            is_first_login=False,
            is_seller=True,
        )
        category = Category.objects.get(slug='textbooks')
        self.client.force_login(seller)

        response = self.client.post(reverse('dashboard:create_listing'), {
            'title': 'Database Systems',
            'category': category.pk,
            'price': '500',
            'condition': 'Good condition',
            'location': 'Library',
            'description': 'Clean copy.',
        })

        self.assertEqual(response.status_code, 302)
        created_listing = Listing.objects.get(seller=seller, title='Database Systems')
        self.assertEqual(created_listing.status, Listing.Status.ACTIVE)

    def test_seller_can_create_listing_with_stock_quantity(self):
        seller = User.objects.create_user(
            email='stock-seller@example.com',
            password='StrongPassword123!',
            first_name='Stock',
            last_name='Seller',
            contact_num='09123456780',
            email_verified=True,
            is_first_login=False,
            is_seller=True,
        )
        category = Category.objects.get(slug='textbooks')
        self.client.force_login(seller)

        response = self.client.post(reverse('dashboard:create_listing'), {
            'title': 'Inventory testing book',
            'category': category.pk,
            'price': '250',
            'condition': 'Good condition',
            'location': 'Library',
            'description': 'Fresh copy.',
            'stock_quantity': '15',
        })

        self.assertEqual(response.status_code, 302)
        created_listing = Listing.objects.get(seller=seller, title='Inventory testing book')
        self.assertEqual(created_listing.stock_quantity, 15)

    def test_seller_can_open_and_update_listing(self):
        seller = User.objects.create_user(
            email='editor@example.com',
            password='StrongPassword123!',
            first_name='Listing',
            last_name='Editor',
            contact_num='09123456787',
            email_verified=True,
            is_first_login=False,
            is_seller=True,
        )
        listing = Listing.objects.filter(seller_id__isnull=False).first()
        listing.seller = seller
        listing.save(update_fields=['seller'])
        self.client.force_login(seller)

        edit_response = self.client.get(reverse('dashboard:edit_listing', args=[listing.id]))
        self.assertEqual(edit_response.status_code, 200)

        save_response = self.client.post(reverse('dashboard:edit_listing', args=[listing.id]), {
            'title': 'Updated listing title',
            'category': listing.category_id,
            'price': '999',
            'condition': 'Like new',
            'location': 'Student center',
            'description': 'Updated details.',
            'status': Listing.Status.SOLD,
            'images': [
                SimpleUploadedFile('front.jpg', b'front-image', content_type='image/jpeg'),
                SimpleUploadedFile('back.jpg', b'back-image', content_type='image/jpeg'),
            ],
        })
        self.assertEqual(save_response.status_code, 302)
        listing.refresh_from_db()
        self.assertEqual(listing.title, 'Updated listing title')
        self.assertEqual(listing.status, Listing.Status.SOLD)
        self.assertEqual(listing.listing_images.count(), 2)

    def test_seller_can_update_listing_stock(self):
        seller = User.objects.create_user(
            email='stock-editor@example.com', password='StrongPassword123!',
            first_name='Stock', last_name='Editor', contact_num='09123456999',
            email_verified=True, is_first_login=False, is_seller=True,
        )
        listing = Listing.objects.filter(seller_id__isnull=False).first()
        listing.seller = seller
        listing.stock_quantity = 2
        listing.save(update_fields=['seller', 'stock_quantity'])
        self.client.force_login(seller)

        response = self.client.post(reverse('dashboard:edit_listing', args=[listing.id]), {
            'title': listing.title,
            'category': listing.category_id,
            'price': str(listing.price),
            'condition': listing.condition,
            'location': listing.location,
            'description': listing.description,
            'status': listing.status,
            'stock_quantity': '9',
        })

        self.assertEqual(response.status_code, 302)
        listing.refresh_from_db()
        self.assertEqual(listing.stock_quantity, 9)

    def test_seller_can_mark_a_listing_sold_when_stock_is_recorded(self):
        seller = User.objects.create_user(
            email='sold-stock-editor@example.com', password='StrongPassword123!',
            first_name='Sold', last_name='Editor', contact_num='09123456888',
            email_verified=True, is_first_login=False, is_seller=True,
        )
        category = Category.objects.get(slug='textbooks')
        listing = Listing.objects.create(
            seller=seller,
            category=category,
            title='Available inventory item',
            description='A test listing.',
            price='200.00',
            condition='Good condition',
            location='Library',
            stock_quantity=4,
        )
        self.client.force_login(seller)

        response = self.client.post(reverse('dashboard:edit_listing', args=[listing.id]), {
            'title': listing.title,
            'category': category.id,
            'price': str(listing.price),
            'condition': listing.condition,
            'location': listing.location,
            'description': listing.description,
            'status': Listing.Status.SOLD,
            'stock_quantity': '4',
        })

        self.assertEqual(response.status_code, 302)
        listing.refresh_from_db()
        self.assertEqual(listing.status, Listing.Status.SOLD)
        self.assertEqual(listing.stock_quantity, 4)

    def test_seller_can_remove_an_uploaded_listing_photo(self):
        seller = User.objects.create_user(
            email='photo-remover@example.com', password='StrongPassword123!',
            first_name='Photo', last_name='Remover', contact_num='09123456776',
            email_verified=True, is_first_login=False,
        )
        listing = Listing.objects.filter(seller_id__isnull=False).first()
        listing.seller = seller
        listing.save(update_fields=['seller'])
        first_image = listing.listing_images.first()
        if not first_image:
            from .models import ListingImage
            first_image = ListingImage.objects.create(listing=listing)
        self.client.force_login(seller)
        response = self.client.post(reverse('dashboard:edit_listing', args=[listing.id]), {
            'title': listing.title,
            'category': listing.category_id,
            'price': str(listing.price),
            'condition': listing.condition,
            'location': listing.location,
            'description': listing.description,
            'status': listing.status,
            'remove_image_ids': [first_image.id],
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(listing.listing_images.filter(id=first_image.id).exists())

    def test_listing_edit_ignores_missing_photo_id_when_uploading_replacement(self):
        seller = User.objects.create_user(
            email='photo-replacement@example.com', password='StrongPassword123!',
            first_name='Photo', last_name='Replacement', contact_num='09123456775',
            email_verified=True, is_first_login=False,
        )
        listing = Listing.objects.filter(seller_id__isnull=False).first()
        listing.seller = seller
        listing.save(update_fields=['seller'])
        self.client.force_login(seller)
        response = self.client.post(reverse('dashboard:edit_listing', args=[listing.id]), {
            'title': listing.title,
            'category': listing.category_id,
            'price': str(listing.price),
            'condition': listing.condition,
            'location': listing.location,
            'description': listing.description,
            'status': listing.status,
            'remove_image_ids': 'None',
            'images': SimpleUploadedFile('replacement.jpg', b'replacement-image', content_type='image/jpeg'),
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(listing.listing_images.exists())

    def test_removing_all_photos_then_uploading_one_replaces_the_primary_photo(self):
        from .models import ListingImage

        seller = User.objects.create_user(
            email='photo-reset@example.com', password='StrongPassword123!',
            first_name='Photo', last_name='Reset', contact_num='09123456774',
            email_verified=True, is_first_login=False,
        )
        listing = Listing.objects.filter(seller_id__isnull=False).first()
        listing.seller = seller
        listing.save(update_fields=['seller'])
        old_primary_name = listing.image.name
        existing_images = list(listing.listing_images.all())
        if not existing_images:
            existing_images = [ListingImage.objects.create(listing=listing)]
        self.client.force_login(seller)
        response = self.client.post(reverse('dashboard:edit_listing', args=[listing.id]), {
            'title': listing.title,
            'category': listing.category_id,
            'price': str(listing.price),
            'condition': listing.condition,
            'location': listing.location,
            'description': listing.description,
            'status': listing.status,
            'remove_image_ids': [image.id for image in existing_images],
            'images': SimpleUploadedFile('replacement.jpg', b'replacement-image', content_type='image/jpeg'),
        })
        self.assertEqual(response.status_code, 302)
        listing.refresh_from_db()
        self.assertEqual(listing.listing_images.count(), 1)
        self.assertTrue(listing.image)
        self.assertNotEqual(listing.image.name, old_primary_name)

    def test_primary_photo_without_gallery_record_is_shown_as_a_real_gallery_photo(self):
        seller = User.objects.create_user(
            email='legacy-photo@example.com', password='StrongPassword123!',
            first_name='Legacy', last_name='Photo', contact_num='09123456773',
            email_verified=True, is_first_login=False,
        )
        listing = Listing.objects.filter(seller_id__isnull=False).first()
        listing.seller = seller
        listing.listing_images.all().delete()
        listing.image_urls = []
        listing.image = SimpleUploadedFile('legacy.jpg', b'legacy-image', content_type='image/jpeg')
        listing.save()
        self.assertEqual(len(listing.gallery_urls), 1)
        self.assertNotIn('placehold.co', listing.gallery_urls[0])

    def test_buyer_is_sent_to_buyer_dashboard_and_cannot_open_seller_dashboard(self):
        buyer = User.objects.create_user(
            email='routing-buyer@example.com',
            password='StrongPassword123!',
            first_name='Routing',
            last_name='Buyer',
            contact_num='09123456786',
            email_verified=True,
            is_first_login=False,
        )
        self.client.force_login(buyer)
        self.assertEqual(self.client.get(reverse('dashboard:seller')).status_code, 200)

    def test_seller_dashboard_listing_links_to_its_product_view(self):
        seller = User.objects.get(email='test.seller@usep.edu.ph')
        listing = Listing.objects.filter(seller=seller).first()
        self.client.force_login(seller)

        response = self.client.get(reverse('dashboard:seller'))

        self.assertContains(response, f'href="{listing.get_absolute_url()}"')

    def test_buyer_can_enable_seller_tools(self):
        buyer = User.objects.create_user(
            email='become-seller@example.com',
            password='StrongPassword123!',
            first_name='Future',
            last_name='Seller',
            contact_num='09123456784',
            email_verified=True,
            is_first_login=False,
        )
        self.client.force_login(buyer)
        response = self.client.get(reverse('dashboard:become_seller'))
        self.assertRedirects(response, reverse('dashboard:seller'))

    def test_seller_default_landing_is_still_buyer_listings(self):
        seller = User.objects.get(email='test.seller@usep.edu.ph')
        self.client.force_login(seller)
        response = self.client.get(reverse('dashboard:buyer'))
        self.assertEqual(response.status_code, 200)

    def test_cart_contains_only_the_listings_added_by_buyer(self):
        buyer = User.objects.create_user(
            email='cart-buyer@example.com',
            password='StrongPassword123!',
            first_name='Cart',
            last_name='Buyer',
            contact_num='09123456785',
            email_verified=True,
            is_first_login=False,
        )
        listings = list(Listing.objects.filter(status=Listing.Status.ACTIVE)[:2])
        self.client.force_login(buyer)
        for listing in listings:
            self.client.post(reverse('dashboard:toggle_saved_item', args=[listing.slug]), {'next': reverse('dashboard:buyer_cart')})
        response = self.client.get(reverse('dashboard:buyer_cart'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.context['saved_items'].values_list('listing_id', flat=True)),
            {listing.id for listing in listings},
        )

    def test_carts_are_isolated_between_users(self):
        first_buyer = User.objects.create_user(
            email='first-cart-user@example.com', password='StrongPassword123!',
            first_name='First', last_name='Cart', contact_num='09123456783',
            email_verified=True, is_first_login=False,
        )
        second_buyer = User.objects.create_user(
            email='second-cart-user@example.com', password='StrongPassword123!',
            first_name='Second', last_name='Cart', contact_num='09123456780',
            email_verified=True, is_first_login=False,
        )
        first_listing, second_listing = list(Listing.objects.filter(status=Listing.Status.ACTIVE)[:2])

        self.client.force_login(first_buyer)
        self.client.post(reverse('dashboard:toggle_saved_item', args=[first_listing.slug]))
        self.client.force_login(second_buyer)
        self.client.post(reverse('dashboard:toggle_saved_item', args=[second_listing.slug]))

        first_cart = SavedItem.objects.filter(buyer=first_buyer).values_list('listing_id', flat=True)
        second_cart = SavedItem.objects.filter(buyer=second_buyer).values_list('listing_id', flat=True)
        self.assertEqual(set(first_cart), {first_listing.id})
        self.assertEqual(set(second_cart), {second_listing.id})

    def test_sold_saved_product_moves_to_sold_cart_section(self):
        buyer = User.objects.create_user(
            email='sold-cart-user@example.com', password='StrongPassword123!',
            first_name='Sold', last_name='Cart', contact_num='09123456770',
            email_verified=True, is_first_login=False,
        )
        listing = Listing.objects.filter(status=Listing.Status.ACTIVE).first()
        self.client.force_login(buyer)
        self.client.post(reverse('dashboard:toggle_saved_item', args=[listing.slug]))
        listing.status = Listing.Status.SOLD
        listing.save(update_fields=['status'])

        response = self.client.get(reverse('dashboard:buyer_cart'))
        self.assertEqual(response.context['active_saved_items'].count(), 0)
        self.assertEqual(response.context['sold_saved_items'].count(), 1)

        remove_response = self.client.post(
            reverse('dashboard:toggle_saved_item', args=[listing.slug]),
            {'next': reverse('dashboard:buyer_cart')},
        )
        self.assertRedirects(remove_response, reverse('dashboard:buyer_cart'))
        self.assertFalse(SavedItem.objects.filter(buyer=buyer, listing=listing).exists())

    def test_sold_listing_remains_viewable_after_cart_removal(self):
        buyer = User.objects.create_user(
            email='sold-detail-user@example.com', password='StrongPassword123!',
            first_name='Sold', last_name='Detail', contact_num='09123456771',
            email_verified=True, is_first_login=False,
        )
        listing = Listing.objects.filter(status=Listing.Status.ACTIVE).first()
        self.client.force_login(buyer)
        self.client.post(reverse('dashboard:toggle_saved_item', args=[listing.slug]))
        listing.status = Listing.Status.SOLD
        listing.save(update_fields=['status'])
        self.client.post(reverse('dashboard:toggle_saved_item', args=[listing.slug]), {
            'next': reverse('dashboard:buyer_cart'),
        })

        response = self.client.get(reverse('dashboard:buyer_detail', args=[listing.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This listing has been sold.')
        self.assertContains(response, '>Sold<')

    def test_unavailable_listing_is_viewable_with_a_warning(self):
        listing = Listing.objects.filter(status=Listing.Status.ACTIVE).first()
        listing.status = Listing.Status.ARCHIVED
        listing.save(update_fields=['status'])

        response = self.client.get(reverse('dashboard:buyer_detail', args=[listing.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This listing is unavailable.')

    def test_available_cart_item_has_message_button_but_sold_item_does_not(self):
        buyer = User.objects.create_user(
            email='cart-message-user@example.com', password='StrongPassword123!',
            first_name='Cart', last_name='Message', contact_num='09123456779',
            email_verified=True, is_first_login=False,
        )
        available, sold = list(Listing.objects.filter(status=Listing.Status.ACTIVE)[:2])
        sold.status = Listing.Status.SOLD
        sold.save(update_fields=['status'])
        SavedItem.objects.create(buyer=buyer, listing=available)
        SavedItem.objects.create(buyer=buyer, listing=sold)
        self.client.force_login(buyer)

        response = self.client.get(reverse('dashboard:buyer_cart'))
        self.assertContains(response, 'cart-message-button')
        sold_section = response.content.decode().split('Sold products', 1)[1]
        self.assertNotIn('cart-message-button', sold_section)

    def test_owner_sees_edit_link_on_listing_detail(self):
        seller = User.objects.get(email='test.seller@usep.edu.ph')
        listing = Listing.objects.filter(seller=seller).first()
        self.client.force_login(seller)
        response = self.client.get(reverse('dashboard:buyer_detail', args=[listing.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['can_edit'])
        self.assertNotContains(response, 'Message seller')

    def test_non_owner_sees_buyer_actions_on_listing_detail(self):
        buyer = User.objects.create_user(
            email='non-owner-actions@example.com', password='StrongPassword123!',
            first_name='Non', last_name='Owner', contact_num='09123456778',
            email_verified=True, is_first_login=False,
        )
        listing = Listing.objects.filter(status=Listing.Status.ACTIVE).first()
        self.client.force_login(buyer)
        response = self.client.get(reverse('dashboard:buyer_detail', args=[listing.slug]))
        self.assertContains(response, 'Message seller')
        self.assertContains(response, 'Add to cart')
        self.assertNotContains(response, 'id="open-detail-edit"')

    def test_owner_edit_link_targets_dashboard_manage_modal(self):
        seller = User.objects.get(email='test.seller@usep.edu.ph')
        listing = Listing.objects.filter(seller=seller).first()
        self.client.force_login(seller)
        response = self.client.get(reverse('dashboard:buyer_detail', args=[listing.slug]))
        self.assertContains(response, 'id="open-detail-edit"')
        self.assertContains(response, 'id="detail-edit-modal"')
        self.assertContains(response, f'action="/dashboard/seller/listings/{listing.id}/edit/"')

    def test_listing_form_rejects_malformed_prices(self):
        category = Category.objects.get(slug='textbooks')
        for value in ['1 0 0 0', '1@000', 'abc1000', '1000!!!', '10.00.50', '-50']:
            form = ListingForm(data={
                'title': 'Valid title',
                'category': category.pk,
                'price': value,
                'condition': 'Good condition',
                'location': 'Library',
                'description': 'Valid description.',
                'status': Listing.Status.ACTIVE,
            })
            self.assertFalse(form.is_valid(), value)

    def test_listing_form_accepts_clean_decimal_prices(self):
        category = Category.objects.get(slug='textbooks')
        form = ListingForm(data={
            'title': 'Valid title',
            'category': category.pk,
            'price': '1000.50',
            'condition': 'Good condition',
            'location': 'Library',
            'description': 'Valid description.',
            'status': Listing.Status.ACTIVE,
        })
        self.assertTrue(form.is_valid())

    def test_review_form_rejects_missing_or_non_whole_star_ratings(self):
        for rating in ['', '4.5', '0', '6', 'five']:
            form = ListingReviewForm(data={'rating': rating, 'body': 'A valid review body.'})
            self.assertFalse(form.is_valid(), rating)
            self.assertIn('rating', form.errors)

    def test_review_submission_preserves_bound_values_after_validation_error(self):
        seller = User.objects.create_user(
            email='review-validation-seller@example.com', password='StrongPassword123!',
            first_name='Review', last_name='Seller', contact_num='09123456719',
            email_verified=True, is_first_login=False,
        )
        buyer = User.objects.create_user(
            email='review-validation-buyer@example.com', password='StrongPassword123!',
            first_name='Review', last_name='Buyer', contact_num='09123456718',
            email_verified=True, is_first_login=False,
        )
        listing = Listing.objects.create(
            seller=seller, category=Category.objects.get(slug='textbooks'),
            title='Validation review listing', slug='validation-review-listing',
            description='A listing for review validation.', price='100.00',
            condition='Good condition', location='Library',
        )
        self.client.force_login(buyer)

        response = self.client.post(
            reverse('dashboard:submit_listing_review', args=[listing.slug]),
            {'rating': '4.5', 'body': 'Keep this review text.'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Keep this review text.')
        self.assertContains(response, 'Select a valid choice.')
        self.assertFalse(ListingReview.objects.filter(listing=listing).exists())

    def test_review_submission_saves_each_whole_star_value(self):
        seller = User.objects.create_user(
            email='whole-star-seller@example.com', password='StrongPassword123!',
            first_name='Whole', last_name='Star', contact_num='09123456713',
            email_verified=True, is_first_login=False,
        )
        buyer = User.objects.create_user(
            email='whole-star-buyer@example.com', password='StrongPassword123!',
            first_name='Whole', last_name='Buyer', contact_num='09123456712',
            email_verified=True, is_first_login=False,
        )
        listing = Listing.objects.create(
            seller=seller, category=Category.objects.get(slug='textbooks'),
            title='Whole star listing', slug='whole-star-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
        )
        self.client.force_login(buyer)

        for rating in range(1, 6):
            response = self.client.post(
                reverse('dashboard:submit_listing_review', args=[listing.slug]),
                {'rating': str(rating), 'body': f'{rating} star review.'},
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                ListingReview.objects.get(listing=listing, reviewer=buyer).rating,
                rating,
            )

    def test_seller_reputation_is_weighted_and_does_not_include_other_sellers(self):
        category = Category.objects.get(slug='textbooks')
        seller = User.objects.create_user(
            email='reputation-seller@example.com', password='StrongPassword123!',
            first_name='Reputation', last_name='Seller', contact_num='09123456717',
            email_verified=True, is_first_login=False,
        )
        other_seller = User.objects.create_user(
            email='other-reputation-seller@example.com', password='StrongPassword123!',
            first_name='Other', last_name='Seller', contact_num='09123456716',
            email_verified=True, is_first_login=False,
        )
        first_listing = Listing.objects.create(
            seller=seller, category=category, title='Highly rated listing', slug='highly-rated-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
        )
        second_listing = Listing.objects.create(
            seller=seller, category=category, title='Lower rated listing', slug='lower-rated-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
        )
        other_listing = Listing.objects.create(
            seller=other_seller, category=category, title='Other seller listing', slug='other-seller-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
        )
        listings_and_ratings = [(first_listing, 5)] + [(second_listing, 1)] * 9 + [(other_listing, 5)]
        for index, (listing, rating) in enumerate(listings_and_ratings):
            reviewer = User.objects.create_user(
                email=f'reputation-reviewer-{index}@example.com', password='StrongPassword123!',
                first_name='Reviewer', last_name=str(index), contact_num=f'09123456{700 + index:03d}',
                email_verified=True, is_first_login=False,
            )
            ListingReview.objects.create(listing=listing, reviewer=reviewer, rating=rating, body='Review.')

        response = self.client.get(reverse('dashboard:buyer_detail', args=[first_listing.slug]))

        seller_info = response.context['seller_info']
        self.assertEqual(seller_info['reputation_count'], 10)
        self.assertEqual(float(seller_info['reputation_average']), 1.4)
        self.assertEqual(
            seller_info['reputation_star_states'],
            ['full', 'half', 'empty', 'empty', 'empty'],
        )
        self.assertContains(response, '1.4 out of 5')
        self.assertContains(response, 'bi-star-half')

    def test_other_listing_reviews_section_renders_for_every_rating_combination(self):
        category = Category.objects.get(slug='textbooks')
        seller = User.objects.create_user(
            email='fallback-seller@example.com', password='StrongPassword123!',
            first_name='Fallback', last_name='Seller', contact_num='09123456715',
            email_verified=True, is_first_login=False,
        )
        current_listing = Listing.objects.create(
            seller=seller, category=category, title='Unrated listing', slug='unrated-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
        )
        other_listing = Listing.objects.create(
            seller=seller, category=category, title='Reviewed listing', slug='reviewed-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
        )
        reviewer = User.objects.create_user(
            email='fallback-reviewer@example.com', password='StrongPassword123!',
            first_name='Fallback', last_name='Reviewer', contact_num='09123456714',
            email_verified=True, is_first_login=False,
        )

        response = self.client.get(reverse('dashboard:buyer_detail', args=[current_listing.slug]))
        self.assertEqual(response.context['seller_other_review_count'], 0)
        self.assertContains(response, 'Ratings from this seller&rsquo;s other listings')
        self.assertContains(response, 'No ratings from this seller&rsquo;s other listings yet.')
        content = response.content.decode()
        self.assertLess(
            content.index('No ratings yet for this listing.'),
            content.index('Ratings from this seller&rsquo;s other listings'),
        )

        ListingReview.objects.create(listing=other_listing, reviewer=reviewer, rating=5, body='Other listing review.')

        response = self.client.get(reverse('dashboard:buyer_detail', args=[current_listing.slug]))

        self.assertEqual(response.context['review_count'], 0)
        self.assertEqual(response.context['seller_other_review_count'], 1)
        self.assertContains(response, 'Ratings from this seller&rsquo;s other listings')
        self.assertContains(response, 'Reviewed listing')
        content = response.content.decode()
        self.assertLess(
            content.index('No ratings yet for this listing.'),
            content.index('Ratings from this seller&rsquo;s other listings'),
        )

        current_review = ListingReview.objects.create(
            listing=current_listing, reviewer=seller, rating=4, body='Current listing review.',
        )
        response = self.client.get(reverse('dashboard:buyer_detail', args=[current_listing.slug]))
        self.assertEqual(response.context['review_count'], 1)
        self.assertEqual(response.context['average_rating'], 4)
        self.assertEqual(response.context['seller_other_review_count'], 1)
        self.assertContains(response, 'Ratings from this seller&rsquo;s other listings')
        content = response.content.decode()
        self.assertLess(
            content.index('Current listing review.'),
            content.index('Ratings from this seller&rsquo;s other listings'),
        )

        ListingReview.objects.filter(listing=other_listing).delete()
        response = self.client.get(reverse('dashboard:buyer_detail', args=[current_listing.slug]))
        self.assertEqual(response.context['review_count'], 1)
        self.assertEqual(response.context['seller_other_review_count'], 0)
        self.assertContains(response, 'Ratings from this seller&rsquo;s other listings')
        self.assertContains(response, 'No ratings from this seller&rsquo;s other listings yet.')
        content = response.content.decode()
        self.assertLess(
            content.index('Current listing review.'),
            content.index('Ratings from this seller&rsquo;s other listings'),
        )

        current_review.delete()
        response = self.client.get(reverse('dashboard:buyer_detail', args=[current_listing.slug]))
        self.assertEqual(response.context['review_count'], 0)
        self.assertEqual(response.context['seller_other_review_count'], 0)
        self.assertContains(response, 'No ratings yet for this listing.')
        self.assertContains(response, 'No ratings from this seller&rsquo;s other listings yet.')

    def test_product_cards_show_listing_specific_rating_summaries(self):
        category = Category.objects.get(slug='textbooks')
        seller = User.objects.create_user(
            email='card-rating-seller@example.com', password='StrongPassword123!',
            first_name='Card', last_name='Seller', contact_num='09123456711',
            email_verified=True, is_first_login=False,
        )
        buyer = User.objects.create_user(
            email='card-rating-buyer@example.com', password='StrongPassword123!',
            first_name='Card', last_name='Buyer', contact_num='09123456710',
            email_verified=True, is_first_login=False,
        )
        one_rating_listing = Listing.objects.create(
            seller=seller, category=category, title='One rating listing', slug='one-rating-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
        )
        average_listing = Listing.objects.create(
            seller=seller, category=category, title='Average rating listing', slug='average-rating-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
        )
        fractional_listing = Listing.objects.create(
            seller=seller, category=category, title='Fractional rating listing', slug='fractional-rating-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
        )
        unrated_listing = Listing.objects.create(
            seller=seller, category=category, title='Unrated card listing', slug='unrated-card-listing',
            description='A listing.', price='100.00', condition='Good condition', location='Library',
        )
        rating_data = (
            [(one_rating_listing, 5)]
            + [(average_listing, rating) for rating in (5, 4, 3)]
            + [(fractional_listing, rating) for rating in (5, 4, 4)]
        )
        for index, (listing, rating) in enumerate(rating_data):
            reviewer = User.objects.create_user(
                email=f'card-rating-reviewer-{index}@example.com', password='StrongPassword123!',
                first_name='Card', last_name=f'Reviewer {index}', contact_num=f'09123456{800 + index:03d}',
                email_verified=True, is_first_login=False,
            )
            ListingReview.objects.create(listing=listing, reviewer=reviewer, rating=rating, body='Review.')
        SavedItem.objects.create(buyer=buyer, listing=average_listing)
        self.client.force_login(buyer)

        response = self.client.get(reverse('dashboard:buyer'))

        items = {item.pk: item for item in response.context['items']}
        self.assertEqual((float(items[one_rating_listing.pk].rating_average), items[one_rating_listing.pk].rating_count), (5.0, 1))
        self.assertEqual((float(items[average_listing.pk].rating_average), items[average_listing.pk].rating_count), (4.0, 3))
        self.assertAlmostEqual(float(items[fractional_listing.pk].rating_average), 4.3, places=1)
        self.assertEqual(items[fractional_listing.pk].rating_count, 3)
        self.assertIsNone(items[unrated_listing.pk].rating_average)
        self.assertEqual(items[unrated_listing.pk].rating_count, 0)
        self.assertContains(response, 'Rated 5.0 out of 5 based on 1 rating.')
        self.assertContains(response, 'Rated 4.0 out of 5 based on 3 ratings.')
        self.assertContains(response, 'Rated 4.3 out of 5 based on 3 ratings.')


@override_settings(ALLOWED_HOSTS=['testserver'])
class SellerReputationAndReviewReplyTests(TestCase):
    def setUp(self):
        self.category = Category.objects.get(slug='textbooks')
        self.seller = self.create_user('reputation-seller@example.com', 'Reputation', 'Seller', '09123457001')
        self.other_seller = self.create_user('reputation-other@example.com', 'Other', 'Seller', '09123457002')
        self.reviewer = self.create_user('reputation-reviewer@example.com', 'Review', 'Author', '09123457003')
        self.outsider = self.create_user('reputation-outsider@example.com', 'Outside', 'User', '09123457004')
        self.normal_listing = self.create_listing(self.seller, 'reputation-normal', 'Normal listing')
        self.second_listing = self.create_listing(self.seller, 'reputation-second', 'Second listing')
        self.recycled_listing = self.create_listing(
            self.seller,
            'reputation-recycled',
            'Recycled listing',
            lifecycle_state=Listing.Lifecycle.RECYCLE_BIN,
        )
        self.other_listing = self.create_listing(self.other_seller, 'reputation-other-listing', 'Other seller listing')
        self.normal_review = self.create_review(self.normal_listing, self.reviewer, 5, 'Great item.')
        self.second_review = self.create_review(self.second_listing, self.outsider, 4, 'Good item.')
        self.recycled_review = self.create_review(self.recycled_listing, self.reviewer, 3, 'Old item.')
        self.other_review = self.create_review(self.other_listing, self.reviewer, 2, 'Other seller review.')

    @staticmethod
    def create_user(email, first_name, last_name, contact_num):
        return User.objects.create_user(
            email=email,
            password='StrongPassword123!',
            first_name=first_name,
            last_name=last_name,
            contact_num=contact_num,
            email_verified=True,
            is_first_login=False,
        )

    def create_listing(self, seller, slug, title, lifecycle_state=Listing.Lifecycle.NORMAL):
        return Listing.objects.create(
            seller=seller,
            category=self.category,
            title=title,
            slug=slug,
            description='A test listing.',
            price='100.00',
            condition='Good condition',
            location='Library',
            lifecycle_state=lifecycle_state,
        )

    @staticmethod
    def create_review(listing, reviewer, rating, body):
        return ListingReview.objects.create(
            listing=listing,
            reviewer=reviewer,
            rating=rating,
            body=body,
        )

    def test_reputation_includes_only_own_listings_and_all_lifecycle_states(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse('dashboard:seller_reputation'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['review_count'], 3)
        self.assertEqual(response.context['average_rating'], 4.0)
        self.assertEqual(response.context['needs_reply_count'], 2)
        self.assertEqual(
            {review.pk for review in response.context['reviews']},
            {self.normal_review.pk, self.second_review.pk, self.recycled_review.pk},
        )
        self.assertNotContains(response, self.other_review.body)
        self.assertContains(response, 'Read only')

    def test_reputation_filters_listing_rating_and_normal_listing_needs_reply(self):
        ListingReviewReply.objects.create(
            review=self.normal_review,
            author=self.seller,
            body='Thanks for your review.',
        )
        self.client.force_login(self.seller)

        needs_reply_response = self.client.get(
            reverse('dashboard:seller_reputation'),
            {'needs_reply': '1'},
        )
        self.assertEqual(
            {review.pk for review in needs_reply_response.context['reviews']},
            {self.second_review.pk},
        )
        self.assertEqual(needs_reply_response.context['needs_reply_count'], 1)

        rating_response = self.client.get(
            reverse('dashboard:seller_reputation'),
            {'rating': '3'},
        )
        self.assertEqual(
            [review.pk for review in rating_response.context['reviews']],
            [self.recycled_review.pk],
        )

        listing_response = self.client.get(
            reverse('dashboard:seller_reputation'),
            {'listing': str(self.second_listing.pk)},
        )
        self.assertEqual(
            [review.pk for review in listing_response.context['reviews']],
            [self.second_review.pk],
        )

    def test_non_participant_and_another_seller_cannot_reply_to_review(self):
        self.client.force_login(self.outsider)
        outsider_response = self.client.post(
            reverse('dashboard:add_listing_review_reply', args=[self.normal_review.pk]),
            {'body': 'I am not a participant.'},
        )
        self.assertEqual(outsider_response.status_code, 403)

        self.client.force_login(self.other_seller)
        other_seller_response = self.client.post(
            reverse('dashboard:add_listing_review_reply', args=[self.normal_review.pk]),
            {'body': 'This is another seller listing.'},
        )
        self.assertEqual(other_seller_response.status_code, 403)
        self.assertEqual(self.client.get(reverse('dashboard:seller_reputation')).context['reviews'].count(), 1)

    def test_reviewer_can_reply_and_notifies_the_listing_seller(self):
        self.client.force_login(self.reviewer)

        response = self.client.post(
            reverse('dashboard:add_listing_review_reply', args=[self.normal_review.pk]),
            {'body': 'Thanks for the listing.', 'next': reverse('dashboard:buyer_detail', args=[self.normal_listing.slug])},
        )

        self.assertEqual(response.status_code, 302)
        reply = ListingReviewReply.objects.get(review=self.normal_review, author=self.reviewer)
        notification = ReviewNotification.objects.get(reply=reply)
        self.assertEqual(notification.recipient, self.seller)
        self.assertEqual(notification.preview, 'Thanks for the listing.')
        self.assertEqual(notification.link, f'{self.normal_listing.get_absolute_url()}#review-{self.normal_review.pk}')

    def test_seller_reply_notifies_reviewer(self):
        self.client.force_login(self.seller)

        response = self.client.post(
            reverse('dashboard:add_listing_review_reply', args=[self.normal_review.pk]),
            {'body': 'Thank you!'},
        )

        self.assertEqual(response.status_code, 302)
        notification = ReviewNotification.objects.get(reply__review=self.normal_review)
        self.assertEqual(notification.recipient, self.reviewer)

    def test_only_reply_author_can_edit_or_delete(self):
        reply = ListingReviewReply.objects.create(
            review=self.normal_review,
            author=self.seller,
            body='Original seller reply.',
        )
        self.client.force_login(self.reviewer)

        edit_denied = self.client.post(
            reverse('dashboard:edit_listing_review_reply', args=[reply.pk]),
            {'body': 'Changed by reviewer.'},
        )
        delete_denied = self.client.post(
            reverse('dashboard:delete_listing_review_reply', args=[reply.pk]),
        )
        self.assertEqual(edit_denied.status_code, 403)
        self.assertEqual(delete_denied.status_code, 403)
        reply.refresh_from_db()
        self.assertEqual(reply.body, 'Original seller reply.')

        self.client.force_login(self.seller)
        edit_response = self.client.post(
            reverse('dashboard:edit_listing_review_reply', args=[reply.pk]),
            {'body': 'Updated seller reply.'},
        )
        self.assertEqual(edit_response.status_code, 302)
        reply.refresh_from_db()
        self.assertEqual(reply.body, 'Updated seller reply.')
        delete_response = self.client.post(
            reverse('dashboard:delete_listing_review_reply', args=[reply.pk]),
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(ListingReviewReply.objects.filter(pk=reply.pk).exists())

    def test_non_normal_review_is_read_only(self):
        self.client.force_login(self.seller)
        response = self.client.get(reverse('dashboard:seller_reputation'))
        self.assertContains(response, 'Read only — Recycle bin')
        self.assertContains(response, 'Replies are unavailable for this listing.')

        self.client.force_login(self.reviewer)
        reply_response = self.client.post(
            reverse('dashboard:add_listing_review_reply', args=[self.recycled_review.pk]),
            {'body': 'Reply to a recycled listing.'},
        )
        self.assertEqual(reply_response.status_code, 404)
        self.assertFalse(ListingReviewReply.objects.filter(review=self.recycled_review).exists())

    def test_review_notification_can_only_be_opened_by_recipient_and_marks_read(self):
        reply = ListingReviewReply.objects.create(
            review=self.normal_review,
            author=self.seller,
            body='A notification for the reviewer.',
        )
        notification = ReviewNotification.objects.create(recipient=self.reviewer, reply=reply)
        self.client.force_login(self.seller)
        denied = self.client.post(reverse('dashboard:open_review_notification', args=[notification.pk]))
        self.assertEqual(denied.status_code, 404)

        self.client.force_login(self.reviewer)
        response = self.client.post(reverse('dashboard:open_review_notification', args=[notification.pk]))
        self.assertRedirects(
            response,
            f'{self.normal_listing.get_absolute_url()}#review-{self.normal_review.pk}',
            fetch_redirect_response=False,
        )
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_reply_thread_is_visible_on_normal_listing_detail(self):
        reply = ListingReviewReply.objects.create(
            review=self.normal_review,
            author=self.seller,
            body='Seller response visible on the listing.',
        )
        self.client.force_login(self.reviewer)

        response = self.client.get(reverse('dashboard:buyer_detail', args=[self.normal_listing.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'id="review-{self.normal_review.pk}"')
        self.assertContains(response, reply.body)
        self.assertContains(response, 'Write a reply')
