from django.urls import path
from . import views

urlpatterns=[
<<<<<<< HEAD
    path('', views.dashboard_view, name='dashboard'),
    path('seller/', views.seller_view, name='seller'),
    path('seller/add/', views.add_listing_view, name='add_listing'),
    path('seller/items/<int:item_id>/', views.manage_item_view, name='manage_item'),
    path('logout/', views.logout_view, name='logout'),
=======
    path("profile/update-field/", views.update_profile_field, name="update_profile_field"),
    path('profile/', views.setup_profile_view, name='profile'),
    path('upload-profile-picture/', views.upload_profile_picture, name='upload_profile_picture'),
    path('logout/', views.logout_view, name='logout'),
    path("reset-password/", views.setup_reset_password_view, name="reset_password"),
    path('forgot-password/', views.setup_forgot_password_view, name='forgot_password'),
>>>>>>> 6fe02047874f2a41b2024f6c526d69b183b30d75
    path('change-password/', views.setup_change_password_view, name='change_password'),
    path('login/', views.setup_login_view, name='login'),
    path('verify/', views.setup_verify_view, name='verify')
]