# Backend/users/views.py
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    RegisterSerializer, UserSerializer,
    EmailVerificationSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, ChangePasswordSerializer,
    CustomTokenObtainPairSerializer
)
from .models import EmailVerificationToken, PasswordResetToken
from .utils import send_verification_email, send_password_reset_email

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Create verification token
        verification_token = EmailVerificationToken.objects.create(user=user)
        
        # Send verification email
        try:
            send_verification_email(user, verification_token.token)
        except Exception as e:
            # Log error but don't fail registration
            print(f"Failed to send verification email: {e}")
        
        return Response({
            "message": "Registration successful. Please check your email to verify your account.",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
            }
        }, status=status.HTTP_201_CREATED)


class EmailVerificationView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        
        try:
            verification_token = EmailVerificationToken.objects.get(token=token)
            
            # Check if token is expired (24 hours)
            token_age = timezone.now() - verification_token.created_at
            if token_age > settings.EMAIL_VERIFICATION_TOKEN_LIFETIME:
                verification_token.delete()
                return Response(
                    {"error": "Verification token has expired. Please request a new one."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify user
            user = verification_token.user
            user.is_email_verified = True
            user.save()
            
            # Delete token
            verification_token.delete()
            
            return Response({
                "message": "Email verified successfully. You can now log in."
            }, status=status.HTTP_200_OK)
            
        except EmailVerificationToken.DoesNotExist:
            return Response(
                {"error": "Invalid verification token."},
                status=status.HTTP_400_BAD_REQUEST
            )


class ResendVerificationEmailView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response(
                {"error": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
            
            if user.is_email_verified:
                return Response(
                    {"error": "Email is already verified."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Delete old tokens
            EmailVerificationToken.objects.filter(user=user).delete()
            
            # Create new token
            verification_token = EmailVerificationToken.objects.create(user=user)
            
            # Send email
            send_verification_email(user, verification_token.token)
            
            return Response({
                "message": "Verification email sent successfully."
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            # Don't reveal if email exists
            return Response({
                "error": "User with this email does not exist."
            }, status=status.HTTP_404_NOT_FOUND)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            
            # Delete old tokens
            PasswordResetToken.objects.filter(user=user).delete()
            
            # Create new token
            reset_token = PasswordResetToken.objects.create(user=user)
            
            # Send email
            send_password_reset_email(user, reset_token.token)
            
        except User.DoesNotExist:
            pass  # Don't reveal if email exists
        
        return Response({
            "message": "If the email exists, a password reset link has been sent."
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['password']
        
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
            
            # Check if token is expired (1 hour)
            token_age = timezone.now() - reset_token.created_at
            if token_age > settings.PASSWORD_RESET_TOKEN_LIFETIME:
                reset_token.delete()
                return Response(
                    {"error": "Reset token has expired. Please request a new one."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Reset password
            user = reset_token.user
            user.set_password(new_password)
            user.save()
            
            # Delete token
            reset_token.delete()
            
            # Delete all user tokens (force re-login)
            PasswordResetToken.objects.filter(user=user).delete()
            
            return Response({
                "message": "Password reset successfully. You can now log in with your new password."
            }, status=status.HTTP_200_OK)
            
        except PasswordResetToken.DoesNotExist:
            return Response(
                {"error": "Invalid reset token."},
                status=status.HTTP_400_BAD_REQUEST
            )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']
        
        # Check old password
        if not user.check_password(old_password):
            return Response(
                {"error": "Old password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        return Response({
            "message": "Password changed successfully."
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({
                "message": "Logout successful."
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": "Invalid token or token already blacklisted."},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def patch(self, request):
        serializer = UserSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)



class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        password = request.data.get('password')
        
        if not password:
            return Response(
                {"error": "Password is required to delete account."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        
        if not user.check_password(password):
            return Response(
                {"error": "Incorrect password."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.delete()
        
        return Response({
            "message": "Account deleted successfully."
        }, status=status.HTTP_200_OK)