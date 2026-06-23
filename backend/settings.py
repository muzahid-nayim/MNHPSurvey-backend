# Backend/backend/settings.py
from pathlib import Path
from datetime import timedelta
from decouple import config
import dj_database_url
import os
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', default=False, cast=bool)

if os.environ.get('DEBUG', 'True') == 'False':
    ALLOWED_HOSTS = ['mnhp.pythonanywhere.com', 'localhost', '127.0.0.1']
else:
    ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

INSTALLED_APPS = [
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'rest_framework',
	'rest_framework_simplejwt.token_blacklist',
	'corsheaders',
	'backend',
	'users',
	'surveys',
]

REST_FRAMEWORK = {
	'DEFAULT_AUTHENTICATION_CLASSES': (
		'rest_framework_simplejwt.authentication.JWTAuthentication',
	),
	'DEFAULT_PERMISSION_CLASSES': (
		'rest_framework.permissions.IsAuthenticated',
	),
}

SIMPLE_JWT = {
	'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
	'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
	'ROTATE_REFRESH_TOKENS': True,
	'BLACKLIST_AFTER_ROTATION': True,
	'UPDATE_LAST_LOGIN': True,
	'ALGORITHM': 'HS256',
	'SIGNING_KEY': SECRET_KEY,
	'AUTH_HEADER_TYPES': ('Bearer',),
	'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
	'USER_ID_FIELD': 'id',
	'USER_ID_CLAIM': 'user_id',
	'TOKEN_OBTAIN_SERIALIZER': 'users.serializers.CustomTokenObtainPairSerializer',
}

# Email — console for now (no domain verified)
# Switch to smtp backend once you have a domain
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')



# Frontend URL
FRONTEND_URL = config('FRONTEND_URL', default='https://mnhp-survey.netlify.app')

# Token expiry times
EMAIL_VERIFICATION_TOKEN_LIFETIME = timedelta(hours=24)
PASSWORD_RESET_TOKEN_LIFETIME = timedelta(hours=72)

MIDDLEWARE = [
	'corsheaders.middleware.CorsMiddleware',
	'django.middleware.security.SecurityMiddleware',
	'whitenoise.middleware.WhiteNoiseMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOWED_ORIGINS = [
	"http://localhost:3000",
	"https://mnhp-survey.netlify.app",
	config('FRONTEND_URL', default='http://localhost:3000'),
]
CORS_ALLOW_CREDENTIALS = True

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
	{
		'BACKEND': 'django.template.backends.django.DjangoTemplates',
		'DIRS': [],
		'APP_DIRS': True,
		'OPTIONS': {
			'context_processors': [
				'django.template.context_processors.request',
				'django.contrib.auth.context_processors.auth',
				'django.contrib.messages.context_processors.messages',
			],
		},
	},
]

WSGI_APPLICATION = 'backend.wsgi.application'

AUTH_USER_MODEL = 'users.User'

DATABASES = {
	'default': dj_database_url.config(
		default=config('DATABASE_URL'),
		conn_max_age=600,
	)
}

AUTH_PASSWORD_VALIDATORS = [
	{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
	{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
	{'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
	{'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Security settings — only active in production (DEBUG=False)
if not DEBUG:
	SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
	SECURE_SSL_REDIRECT = True
	SESSION_COOKIE_SECURE = True
	CSRF_COOKIE_SECURE = True
	SECURE_HSTS_SECONDS = 31536000
	SECURE_HSTS_INCLUDE_SUBDOMAINS = True