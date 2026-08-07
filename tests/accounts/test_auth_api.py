import jwt
import pytest
from django.conf import settings
from rest_framework import status

from apps.accounts.models import AppMode, GuestSession, User
from apps.accounts.services.seeding import seed_customer_side
from apps.restaurants.models import Restaurant
from tests.accounts.factories import GuestSessionFactory, access_token_for


@pytest.mark.django_db
class TestRegister:
    def test_register_customer(self, api_client):
        res = api_client.post(
            '/api/auth/register/',
            {
                'phone_number': '+923001112233',
                'password': 'secret123',
                'signup_intent': 'customer',
            },
            format='json',
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data['profiles']['customer'] is True
        assert res.data['profiles']['restaurant'] is False
        assert res.data['restaurant'] is None
        assert res.data['active_mode'] == 'customer'
        assert 'access' in res.data['tokens']
        payload = jwt.decode(
            res.data['tokens']['access'],
            settings.SECRET_KEY,
            algorithms=['HS256'],
        )
        assert payload['active_mode'] == 'customer'

    def test_register_restaurant(self, api_client):
        res = api_client.post(
            '/api/auth/register/',
            {
                'phone_number': '+923001112244',
                'password': 'secret123',
                'signup_intent': 'restaurant',
                'restaurant_name': 'Burger House',
            },
            format='json',
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data['profiles']['customer'] is False
        assert res.data['profiles']['restaurant'] is True
        assert res.data['restaurant']['name'] == 'Burger House'
        assert res.data['active_mode'] == 'restaurant'

    def test_register_restaurant_missing_name(self, api_client):
        res = api_client.post(
            '/api/auth/register/',
            {
                'phone_number': '+923001112255',
                'password': 'secret123',
                'signup_intent': 'restaurant',
            },
            format='json',
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_phone(self, api_client):
        payload = {
            'phone_number': '+923001112266',
            'password': 'secret123',
            'signup_intent': 'customer',
        }
        assert api_client.post('/api/auth/register/', payload, format='json').status_code == 201
        res = api_client.post('/api/auth/register/', payload, format='json')
        assert res.status_code == status.HTTP_409_CONFLICT

    def test_register_short_password(self, api_client):
        res = api_client.post(
            '/api/auth/register/',
            {
                'phone_number': '+923001112277',
                'password': 'short',
                'signup_intent': 'customer',
            },
            format='json',
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_with_guest_session(self, api_client):
        GuestSessionFactory(session_key='guest-abc', pending_save={'type': 'deal'})
        res = api_client.post(
            '/api/auth/register/',
            {
                'phone_number': '+923001112288',
                'password': 'secret123',
                'signup_intent': 'customer',
                'session_key': 'guest-abc',
            },
            format='json',
        )
        assert res.status_code == 201
        guest = GuestSession.objects.get(session_key='guest-abc')
        assert guest.merged_into_user_id is not None


@pytest.mark.django_db
class TestLoginLogoutRefresh:
    def test_login_success(self, api_client, customer_user):
        res = api_client.post(
            '/api/auth/login/',
            {'phone_number': customer_user.phone_number, 'password': 'secret123'},
            format='json',
        )
        assert res.status_code == 200
        assert 'tokens' in res.data
        assert res.data['active_mode'] == 'customer'

    def test_login_wrong_password(self, api_client, customer_user):
        res = api_client.post(
            '/api/auth/login/',
            {'phone_number': customer_user.phone_number, 'password': 'wrongpass'},
            format='json',
        )
        assert res.status_code == 401

    def test_login_restores_last_active_mode(self, api_client, both_profiles_user):
        both_profiles_user.last_active_mode = AppMode.RESTAURANT
        both_profiles_user.active_mode = AppMode.CUSTOMER
        both_profiles_user.save()
        res = api_client.post(
            '/api/auth/login/',
            {'phone_number': both_profiles_user.phone_number, 'password': 'secret123'},
            format='json',
        )
        assert res.status_code == 200
        assert res.data['active_mode'] == 'restaurant'

    def test_logout_persists_mode_and_blacklists(self, api_client, auth_client, both_profiles_user):
        both_profiles_user.active_mode = AppMode.RESTAURANT
        both_profiles_user.save(update_fields=['active_mode'])
        from core.auth import issue_tokens_for_user

        tokens = issue_tokens_for_user(both_profiles_user)
        client = api_client
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        res = client.post('/api/auth/logout/', {'refresh': tokens['refresh']}, format='json')
        assert res.status_code == 204
        both_profiles_user.refresh_from_db()
        assert both_profiles_user.last_active_mode == 'restaurant'

        # refresh should fail after blacklist
        refresh_res = api_client.post(
            '/api/auth/refresh/',
            {'refresh': tokens['refresh']},
            format='json',
        )
        assert refresh_res.status_code == 401

    def test_refresh_uses_db_active_mode(self, api_client, customer_user):
        from core.auth import issue_tokens_for_user

        tokens = issue_tokens_for_user(customer_user)
        customer_user.active_mode = AppMode.CUSTOMER
        customer_user.save()
        res = api_client.post('/api/auth/refresh/', {'refresh': tokens['refresh']}, format='json')
        assert res.status_code == 200
        payload = jwt.decode(res.data['access'], settings.SECRET_KEY, algorithms=['HS256'])
        assert payload['active_mode'] == 'customer'

    def test_soft_delete_blocks_login(self, api_client, auth_client, customer_user):
        client = auth_client(customer_user)
        assert client.delete('/api/auth/me/').status_code == 204
        res = api_client.post(
            '/api/auth/login/',
            {'phone_number': customer_user.phone_number, 'password': 'secret123'},
            format='json',
        )
        assert res.status_code == 401


@pytest.mark.django_db
class TestMe:
    def test_me_requires_auth(self, api_client):
        assert api_client.get('/api/auth/me/').status_code == 401

    def test_me_shape(self, auth_client, customer_user):
        res = auth_client(customer_user).get('/api/auth/me/')
        assert res.status_code == 200
        assert res.data['profiles']['customer'] is True
        assert res.data['restaurant'] is None
        assert 'active_mode' in res.data

    def test_patch_display_name(self, auth_client, customer_user):
        res = auth_client(customer_user).patch(
            '/api/auth/me/',
            {'display_name': 'Ahmad'},
            format='json',
        )
        assert res.status_code == 200
        assert res.data['display_name'] == 'Ahmad'
