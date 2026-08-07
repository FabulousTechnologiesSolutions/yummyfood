import os

# Select settings module from DJANGO_ENV / ENVIRONMENT (BACKEND-SPEC §3.1).
_env = (
    os.getenv('DJANGO_ENV')
    or os.getenv('ENVIRONMENT')
    or 'development'
).lower().strip()

if _env in ('production', 'prod'):
    from .production import *  # noqa: F401,F403
elif _env in ('testing', 'test'):
    from .testing import *  # noqa: F401,F403
else:
    from .development import *  # noqa: F401,F403
