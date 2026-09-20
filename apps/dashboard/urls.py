from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('seller/', views.setup_seller_dashboard, name='seller'),
    path('seller/enable/', views.become_seller, name='become_seller'),
    path('seller/listings/create/', views.create_listing, name='create_listing'),
    path('seller/listings/<int:listing_id>/edit/', views.edit_listing, name='edit_listing'),
    path('seller/listings/<int:listing_id>/images/<int:image_id>/delete/', views.delete_listing_image, name='delete_listing_image'),
    path('seller/listings/<int:listing_id>/delete/', views.delete_listing, name='delete_listing'),
    path('buyer/', views.setup_buyer_dashboard, name='buyer'),
    path('buyer/cart/', views.setup_buyer_cart, name='buyer_cart'),
    path('buyer/<slug:item_slug>/save/', views.toggle_saved_item, name='toggle_saved_item'),
    path('buyer/<slug:item_slug>/message/', views.start_conversation, name='start_conversation'),
    path('buyer/<slug:item_slug>/', views.setup_buyer_item_detail, name='buyer_detail'),
    path('messages/', views.conversation_list, name='conversation_list'),
    path('messages/link-preview/', views.link_preview, name='link_preview'),
    path('messages/unread-count/', views.unread_message_count, name='unread_message_count'),
    path('messages/sidebar-state/', views.conversation_sidebar_state, name='conversation_sidebar_state'),
    path('messages/search/', views.conversation_search, name='conversation_search'),
    path('messages/<int:conversation_id>/search/', views.conversation_message_search, name='conversation_message_search'),
    path('messages/<int:conversation_id>/links/', views.conversation_links, name='conversation_links'),
    path('messages/<int:conversation_id>/clear/', views.clear_conversation, name='clear_conversation'),
    path('messages/<int:conversation_id>/new/', views.conversation_new_messages, name='conversation_new_messages'),
    path('messages/<int:conversation_id>/typing/', views.conversation_typing, name='conversation_typing'),
    path('messages/<int:conversation_id>/read/', views.conversation_read, name='conversation_read'),
    path('messages/<int:conversation_id>/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('messages/<int:conversation_id>/<int:message_id>/edit/', views.edit_message, name='edit_message'),
    path('messages/<int:conversation_id>/<int:message_id>/history/', views.message_history, name='message_history'),
    path('messages/<int:conversation_id>/', views.conversation_detail, name='conversation'),
]
