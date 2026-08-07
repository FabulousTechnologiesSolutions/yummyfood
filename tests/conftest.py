import os

# Must be set before Django settings import.
os.environ.setdefault('DJANGO_ENV', 'testing')
os.environ.setdefault('ENVIRONMENT', 'testing')
os.environ.setdefault('USE_LOCAL_MEDIA', 'true')

import pytest
from rest_framework.test import APIClient

from tests.accounts.factories import (
    BothProfilesUserFactory,
    CustomerOnlyUserFactory,
    RestaurantOnlyUserFactory,
    access_token_for,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client():
    def _make(user, active_mode=None):
        client = APIClient()
        if active_mode:
            user.active_mode = active_mode
            user.save(update_fields=['active_mode'])
        token = access_token_for(user, active_mode=user.active_mode)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return client

    return _make


@pytest.fixture
def customer_user():
    return CustomerOnlyUserFactory()


@pytest.fixture
def restaurant_user():
    return RestaurantOnlyUserFactory()


@pytest.fixture
def both_profiles_user():
    return BothProfilesUserFactory()
