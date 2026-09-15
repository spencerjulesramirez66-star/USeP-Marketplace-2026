from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from .forms import ListingForm
from .models import Category, Conversation, Listing, SavedItem


@override_settings(ALLOWED_HOSTS=['testserver'])
class BuyerDashboardViewsTests(TestCase):
    def test_buyer_listing_page_loads(self):
        response = self.client.get(reverse('dashboard:buyer'))
        self.assertEqual(response.status_code, 200)

    def test_buyer_detail_page_loads(self):
        response = self.client.get(reverse('dashboard:buyer_detail', args=['engineering-mechanics-textbook']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Stock available')

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

    def test_logged_in_buyer_can_save_listing_and_start_chat(self):
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

        chat_response = self.client.post(
            reverse('dashboard:start_conversation', args=[listing.slug]),
            {'body': 'Is this still available?'},
        )
        self.assertEqual(chat_response.status_code, 302)
        self.assertTrue(Conversation.objects.filter(buyer=buyer, listing=listing).exists())

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
