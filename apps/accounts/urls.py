from django.urls import path
from . import views

urlpatterns=[
    path("profile/update-field/", views.update_profile_field, name="update_profile_field"),
    path('profile/', views.setup_profile_view, name='profile'),
    path('upload-profile-picture/', views.upload_profile_picture, name='upload_profile_picture'),
    path('logout/', views.logout_view, name='logout'),
    path("reset-password/", views.setup_reset_password_view, name="reset_password"),
    path('forgot-password/', views.setup_forgot_password_view, name='forgot_password'),
    path('change-password/', views.setup_change_password_view, name='change_password'),
    path('login/', views.setup_login_view, name='login'),
    path('verify/', views.setup_verify_view, name='verify')
]