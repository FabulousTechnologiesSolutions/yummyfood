import os
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-secret-key-change-me')
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '164.68.125.17',
    '192.168.1.41',
    '192.168.1.65',
    'propertymanage-be.thefabulousshow.com',
    '.thefabulousshow.com',
    'saskatchewan-diameter-recorders-cycle.trycloudflare.com',
    '.trycloudflare.com',
]

_extra_allowed_hosts = os.getenv('EXTRA_ALLOWED_HOSTS', '')
if _extra_allowed_hosts:
    ALLOWED_HOSTS.extend(
        host.strip() for host in _extra_allowed_hosts.split(',') if host.strip()
    )

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    'django_filters',
    'channels',
    'storages',
    'django_celery_beat',
]

LOCAL_APPS = [
    'core',
    'apps.accounts',
    'apps.geo',
    'apps.restaurants',
    'apps.menu',
    'apps.deals',
    'apps.promotions',
    'apps.mediahub',
    'apps.feed',
    'apps.discovery',
    'apps.engagement',
    'apps.analytics',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.RequestLoggingMiddleware',
]

ROOT_URLCONF = 'conf.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'conf.wsgi.application'
ASGI_APPLICATION = 'conf.asgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'core.auth.CustomJWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
}

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://192.168.1.65:5173',
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https://[\w-]+\.trycloudflare\.com$',
]

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://192.168.1.65:5173',
]

APPEND_SLASH = True

API_BASE_URL = os.getenv(
    'API_BASE_URL',
    'https://propertymanage-be.thefabulousshow.com',
)

SPECTACULAR_SETTINGS = {
    'TITLE': 'FoodApp API',
    'DESCRIPTION': 'API for FoodApp food discovery and restaurant promotion platform',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {'persistAuthorization': True},
    'SERVERS': [
        {'url': API_BASE_URL, 'description': 'Production'},
        {'url': 'http://localhost:6060', 'description': 'Local Docker'},
    ],
    'COMPONENTS': {
        'securitySchemes': {
            'BearerAuth': {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'}
        }
    },
    'SECURITY': [{'BearerAuth': []}],
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'level': 'INFO', 'class': 'logging.StreamHandler'},
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'app.log',
        },
    },
    'loggers': {
        'django': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': True},
        'apps': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
    },
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Karachi'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.User'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_ACCESS_DAYS', '7'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_DAYS', '30'))),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'TOKEN_OBTAIN_SERIALIZER': 'core.auth.CustomTokenObtainPairSerializer',
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(os.getenv('REDIS_HOST', '127.0.0.1'), int(os.getenv('REDIS_PORT', '6379')))],
        },
    },
}

# Celery
CELERY_BROKER_URL = os.getenv(
    'CELERY_BROKER_URL',
    f"redis://{os.getenv('REDIS_HOST', '127.0.0.1')}:{os.getenv('REDIS_PORT', '6379')}/0",
)
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BEAT_SCHEDULE = {
    'expire-promotions-midnight': {
        'task': 'apps.promotions.tasks.expire_promotions',
        'schedule': crontab(hour=0, minute=0),
    },
}
CELERY_TASK_ACKS_LATE = True

# Explore / analytics
EXPLORE_ENGAGEMENT_WEIGHTS = {
    'impression': 0.2,
    'detail_view': 1,
    'call': 8,
    'whatsapp': 10,
    'share': 6,
    'save': 5,
    'follow': 4,
    'direction': 3,
}
EXPLORE_BLOCK_PROMOTED = 1
EXPLORE_BLOCK_ORGANIC = 3
EXPLORE_DEFAULT_PAGE_SIZE = 20
VIEWER_IP_HASH_SALT = os.getenv('VIEWER_IP_HASH_SALT', SECRET_KEY)
EXPLORE_DEFAULT_MAX_RADIUS_KM = 50
EXPLORE_DISTANCE_FILTER_CHOICES = [1, 3, 5, 10, 25, 50]
NOTIFICATION_LEAD_THROTTLE_MINUTES = int(os.getenv('NOTIFICATION_LEAD_THROTTLE_MINUTES', '15'))

# LifetimeSMS / OTP signup
LIFETIMESMS_API_TOKEN = os.getenv('LIFETIMESMS_API_TOKEN', '')
LIFETIMESMS_API_SECRET = os.getenv('LIFETIMESMS_API_SECRET', '')
LIFETIMESMS_FROM = os.getenv('LIFETIMESMS_FROM', 'Lifetimesms')
OTP_TTL_MINUTES = int(os.getenv('OTP_TTL_MINUTES', '10'))
OTP_SMS_MAX_ATTEMPTS = int(os.getenv('OTP_SMS_MAX_ATTEMPTS', '3'))
OTP_MAX_VERIFY_ATTEMPTS = int(os.getenv('OTP_MAX_VERIFY_ATTEMPTS', '5'))
OTP_SMS_RETRY_BACKOFF_SECONDS = float(os.getenv('OTP_SMS_RETRY_BACKOFF_SECONDS', '0.5'))

# FCM push notifications
FCM_ENABLED = os.getenv('FCM_ENABLED', 'false').lower() in ('true', '1', 'yes')
FIREBASE_CREDENTIALS_PATH = os.getenv('FIREBASE_CREDENTIALS_PATH', '')
FIREBASE_CREDENTIALS_JSON = os.getenv('FIREBASE_CREDENTIALS_JSON', '')

FFMPEG_PATH = os.getenv('FFMPEG_PATH', 'ffmpeg')
FFPROBE_PATH = os.getenv('FFPROBE_PATH', 'ffprobe')

# Restaurant product quota (free tier)
FREE_TIER_PRODUCTS_PER_MONTH = int(os.getenv('FREE_TIER_PRODUCTS_PER_MONTH', '5'))
PRESIGNED_UPLOAD_EXPIRES = int(os.getenv('PRESIGNED_UPLOAD_EXPIRES', '3600'))
MAX_UPLOAD_BYTES = int(os.getenv('MAX_UPLOAD_BYTES', str(100 * 1024 * 1024)))
MAX_VIDEO_DURATION_SECONDS = int(os.getenv('MAX_VIDEO_DURATION_SECONDS', '60'))

# Cloudflare R2 storage (overridden in testing.py / development.py when USE_LOCAL_MEDIA=true)
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID', '')
CLOUDFLARE_R2_ACCESS_KEY_ID = os.getenv('CLOUDFLARE_R2_ACCESS_KEY_ID', '')
CLOUDFLARE_R2_SECRET_ACCESS_KEY = os.getenv('CLOUDFLARE_R2_SECRET_ACCESS_KEY', '')
CLOUDFLARE_R2_BUCKET_NAME = os.getenv('CLOUDFLARE_R2_BUCKET_NAME', '')
CLOUDFLARE_R2_PUBLIC_URL = os.getenv('CLOUDFLARE_R2_PUBLIC_URL', '') or None
CLOUDFLARE_R2_CUSTOM_DOMAIN = None
if CLOUDFLARE_R2_PUBLIC_URL:
    from core.storage import normalize_r2_public_domain

    CLOUDFLARE_R2_CUSTOM_DOMAIN = normalize_r2_public_domain(CLOUDFLARE_R2_PUBLIC_URL)
CLOUDFLARE_R2_ENDPOINT_URL = (
    f'https://{CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com'
    if CLOUDFLARE_ACCOUNT_ID else None
)
AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False

STORAGES = {
    'default': {
        'BACKEND': 'core.storage.CloudflareR2Storage',
        'OPTIONS': {
            'access_key': CLOUDFLARE_R2_ACCESS_KEY_ID,
            'secret_key': CLOUDFLARE_R2_SECRET_ACCESS_KEY,
            'bucket_name': CLOUDFLARE_R2_BUCKET_NAME,
            'endpoint_url': CLOUDFLARE_R2_ENDPOINT_URL,
            'custom_domain': CLOUDFLARE_R2_CUSTOM_DOMAIN,
            'default_acl': None,
            'file_overwrite': False,
            'querystring_auth': False,
        },
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}
