import os

from .base import *  # noqa: F401,F403

DEBUG = False

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

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
