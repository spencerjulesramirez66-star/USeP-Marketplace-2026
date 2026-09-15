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
    path('messages/<int:conversation_id>/', views.conversation_detail, name='conversation'),
]