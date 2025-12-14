# Backend/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	email = models.EmailField(unique=True)
	is_email_verified = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	USERNAME_FIELD = 'email'
	REQUIRED_FIELDS = ['username']
	
	class Meta:
		db_table = 'users'
		ordering = ['-created_at']
	
	def __str__(self):
		return self.email


class EmailVerificationToken(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)
	
	class Meta:
		db_table = 'email_verification_tokens'
	
	def __str__(self):
		return f"{self.user.email} - {self.token}"


class PasswordResetToken(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)
	
	class Meta:
		db_table = 'password_reset_tokens'
	
	def __str__(self):
		return f"{self.user.email} - {self.token}"