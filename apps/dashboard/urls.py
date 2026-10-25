from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('seller/', views.setup_seller_dashboard, name='seller'),
    path('seller/reputation/', views.seller_reputation_page, name='seller_reputation'),
    path('seller/enable/', views.become_seller, name='become_seller'),
    path('seller/listings/create/', views.create_listing, name='create_listing'),
    path('seller/listings/<int:listing_id>/edit/', views.edit_listing, name='edit_listing'),
    path('seller/listings/<int:listing_id>/images/<int:image_id>/delete/', views.delete_listing_image, name='delete_listing_image'),
    path('seller/listings/<int:listing_id>/delete/', views.delete_listing, name='delete_listing'),
    path('seller/listings/<int:listing_id>/restore/', views.restore_listing, name='restore_listing'),
    path('buyer/', views.setup_buyer_dashboard, name='buyer'),
    path('buyer/cart/', views.setup_buyer_cart, name='buyer_cart'),
    path('buyer/<slug:item_slug>/save/', views.toggle_saved_item, name='toggle_saved_item'),
    path('buyer/<slug:item_slug>/reviews/', views.submit_listing_review, name='submit_listing_review'),
    path('reviews/<int:review_id>/replies/', views.add_listing_review_reply, name='add_listing_review_reply'),
    path('review-replies/<int:reply_id>/edit/', views.edit_listing_review_reply, name='edit_listing_review_reply'),
    path('review-replies/<int:reply_id>/delete/', views.delete_listing_review_reply, name='delete_listing_review_reply'),
    path('review-notifications/<int:notification_id>/open/', views.open_review_notification, name='open_review_notification'),
    path('review-notifications/read-all/', views.mark_review_notifications_read, name='mark_review_notifications_read'),
    path('buyer/<slug:item_slug>/', views.setup_buyer_item_detail, name='buyer_detail'),
]

# Everything under messages/ -- conversation_list, link_preview,
# unread_message_count, conversation_sidebar_state, conversation_search,
# conversation_message_search, conversation_links, clear_conversation,
# conversation_new_messages, conversation_typing, conversation_read,
# delete_message, edit_message, message_history, conversation_detail --
# has moved to apps.messaging.urls, mounted at /messages/ in the project's
# root urlconf. 'buyer/<slug:item_slug>/message/' (start_conversation) moved
# there too, as 'listings/<slug:item_slug>/start/'.
