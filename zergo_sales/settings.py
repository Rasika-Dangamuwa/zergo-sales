"""
Django settings for zergo_sales project.
"""

from pathlib import Path
from decouple import config
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',') + [
    '192.168.1.4',
    '.localhost',  # Allow all *.localhost subdomains for tenants
]

# =============================================================================
# MULTI-TENANCY CONFIGURATION (django-tenants)
# =============================================================================
# Schema layout:
#   public schema  → SHARED_APPS (tenants, accounts/auth, django core)
#   tenant schemas → TENANT_APPS (shops, products, sales, payments, business)
# =============================================================================

# Apps whose tables live in the PUBLIC schema (shared across all tenants)
SHARED_APPS = [
    'django_tenants',  # Must be first
    'tenants',         # Distributor + Domain models
    
    # Django core (shared)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Third party (shared)
    'django_extensions',
    'crispy_forms',
    'crispy_bootstrap5',
    
    # User model must be shared (Django auth requires it in public schema)
    'accounts',
    
    # Global product catalog (shared across all distributors)
    'catalog',
]

# Apps whose tables live in EACH TENANT's schema (per-distributor data)
TENANT_APPS = [
    # Django core (needed per-tenant for permissions/content types)
    'django.contrib.contenttypes',
    'django.contrib.auth',
    
    # Business data apps (fully isolated per distributor)
    'shops',
    'products',
    'sales',
    'payments',
    'dashboard',
    'business',
    'expenses',
]

# Combined list (django-tenants requires this)
INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

# Tenant model references
TENANT_MODEL = 'tenants.Distributor'
TENANT_DOMAIN_MODEL = 'tenants.Domain'

# Database router for tenant-aware queries
DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)

MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',  # Must be first - sets tenant schema
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'accounts.middleware.TenantAccessMiddleware',  # Must be after Auth AND Messages
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'zergo_sales.urls'

# Public schema URL conf (central admin dashboard, tenant management)
PUBLIC_SCHEMA_URLCONF = 'zergo_sales.urls_public'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'business.context_processors.business_settings',  # Global business settings
            ],
        },
    },
]

WSGI_APPLICATION = 'zergo_sales.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',  # Tenant-aware PostgreSQL backend
        'NAME': config('DB_NAME', default='zergo_sales_db'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Colombo'  # Sri Lanka timezone

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Login URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard:home'
LOGOUT_REDIRECT_URL = 'login'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Leaflet Configuration for Maps
LEAFLET_CONFIG = {
    'DEFAULT_CENTER': (7.8731, 80.7718),  # Sri Lanka center
    'DEFAULT_ZOOM': 8,
    'MIN_ZOOM': 3,
    'MAX_ZOOM': 18,
    'TILES': 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    'ATTRIBUTION_PREFIX': 'Zergo Distributors',
}

# Email Configuration (for production)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Session settings
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = True

# HTTPS/SSL Settings
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_HTTPONLY = True

# Production HSTS settings (only when not DEBUG)
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Production CSRF trusted origins — set PRODUCTION_DOMAIN in .env (e.g., zergosales.com)
    _prod_domain = config('PRODUCTION_DOMAIN', default='')
    if _prod_domain:
        CSRF_TRUSTED_ORIGINS = [
            f'https://{_prod_domain}',
            f'https://*.{_prod_domain}',
        ]

# For development with self-signed certificates
if DEBUG:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    CSRF_TRUSTED_ORIGINS = [
        'https://192.168.1.4:8000',
        'https://localhost:8000',
        'https://127.0.0.1:8000',
        'http://192.168.1.4:8000',
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        'https://*.localhost:8000',  # Tenant subdomains
        'http://*.localhost:8000',   # Tenant subdomains
    ]
