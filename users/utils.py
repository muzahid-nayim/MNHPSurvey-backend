# Backend/users/utils.py
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_verification_email(user, token):
	"""Send email verification link"""
	verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
	
	subject = 'Verify Your Email - Survey Platform'
	html_message = f"""
	<html>
		<body>
			<h2>Welcome to Survey Platform!</h2>
			<p>Hi {user.username},</p>
			<p>Thank you for registering. Please verify your email by clicking the link below:</p>
			<p><a href="{verification_url}">Verify Email</a></p>
			<p>Or copy this link: {verification_url}</p>
			<p>This link will expire in 24 hours.</p>
			<p>If you didn't create this account, please ignore this email.</p>
		</body>
	</html>
	"""
	plain_message = strip_tags(html_message)
	
	send_mail(
		subject,
		plain_message,
		settings.DEFAULT_FROM_EMAIL,
		[user.email],
		html_message=html_message,
		fail_silently=False,
	)


def send_password_reset_email(user, token):
	"""Send password reset link"""
	reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
	
	subject = 'Reset Your Password - Survey Platform'
	html_message = f"""
	<html>
		<body>
			<h2>Password Reset Request</h2>
			<p>Hi {user.username},</p>
			<p>You requested to reset your password. Click the link below to proceed:</p>
			<p><a href="{reset_url}">Reset Password</a></p>
			<p>Or copy this link: {reset_url}</p>
			<p>This link will expire in 1 hour.</p>
			<p>If you didn't request this, please ignore this email.</p>
		</body>
	</html>
	"""
	plain_message = strip_tags(html_message)
	
	send_mail(
		subject,
		plain_message,
		settings.DEFAULT_FROM_EMAIL,
		[user.email],
		html_message=html_message,
		fail_silently=False,
	)