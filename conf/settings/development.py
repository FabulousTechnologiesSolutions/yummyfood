import os

from .base import *  # noqa: F401,F403

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'foodapp'),
        'USER': os.getenv('POSTGRES_USER', 'foodapp'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'foodapp'),
        'HOST': os.getenv('POSTGRES_HOST', '127.0.0.1'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

# Local filesystem media when USE_LOCAL_MEDIA=true (default in development).
if os.getenv('USE_LOCAL_MEDIA', 'true').lower() in ('true', '1', 'yes'):
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
        },
    }
