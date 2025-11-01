# Backend/users/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomTokenObtainPairView, RegisterView, ProfileView,
    EmailVerificationView, ResendVerificationEmailView,
    PasswordResetRequestView, PasswordResetConfirmView,
    ChangePasswordView, LogoutView, DeleteAccountView
)

urlpatterns = [
    # Authentication
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Email Verification
    path('verify-email/', EmailVerificationView.as_view(), name='verify_email'),
    path('resend-verification/', ResendVerificationEmailView.as_view(), name='resend_verification'),
    
    # Password Management
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # Profile
    path('profile/', ProfileView.as_view(), name='profile'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete_account'),
]