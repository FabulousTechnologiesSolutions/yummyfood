import os

from .base import *  # noqa: F401,F403

DEBUG = False

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',  # noqa: F405
    }
}

# Allow overriding with Postgres via env if desired.
if os.getenv('TEST_USE_POSTGRES', '').lower() in ('true', '1', 'yes'):
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

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

LOGGING['handlers'] = {  # noqa: F405
    'console': {'level': 'WARNING', 'class': 'logging.StreamHandler'},
}
LOGGING['loggers'] = {  # noqa: F405
    'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': True},
    'apps': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
}
