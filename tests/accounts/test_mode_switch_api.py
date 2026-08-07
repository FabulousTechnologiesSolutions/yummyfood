import jwt
import pytest
from django.conf import settings

from apps.accounts.models import AppMode
from apps.restaurants.models import Restaurant


@pytest.mark.django_db
class TestModeSwitch:
    def test_switch_to_restaurant_creates_when_missing(self, auth_client, customer_user):
        client = auth_client(customer_user)
        res = client.post(
            '/api/me/switch-to-restaurant/',
            {'restaurant_name': 'New Spot'},
            format='json',
        )
        assert res.status_code == 200
        assert res.data['active_mode'] == 'restaurant'
        assert res.data['profiles']['restaurant'] is True
        assert res.data['needs_profile_update'] is True
        assert res.data['restaurant']['name'] == 'New Spot'
        assert Restaurant.objects.filter(owner=customer_user).count() == 1
        payload = jwt.decode(
            res.data['tokens']['access'],
            settings.SECRET_KEY,
            algorithms=['HS256'],
        )
        assert payload['active_mode'] == 'restaurant'

    def test_switch_to_restaurant_auto_creates_without_name(self, auth_client, customer_user):
        customer_user.display_name = 'Ahmad'
        customer_user.save(update_fields=['display_name'])
        res = auth_client(customer_user).post('/api/me/switch-to-restaurant/', {}, format='json')
        assert res.status_code == 200
        assert res.data['needs_profile_update'] is True
        assert res.data['profiles']['restaurant'] is True
        assert res.data['restaurant']['name'] == 'Ahmad'
        assert Restaurant.objects.filter(owner=customer_user).count() == 1

        # Second switch must not recreate and must not flag again.
        again = auth_client(customer_user).post('/api/me/switch-to-restaurant/', {}, format='json')
        assert again.status_code == 200
        assert again.data['needs_profile_update'] is False
        assert Restaurant.objects.filter(owner=customer_user).count() == 1

    def test_switch_to_customer_creates_profile(self, auth_client, restaurant_user):
        assert restaurant_user.has_customer_profile is False
        res = auth_client(restaurant_user).post('/api/me/switch-to-customer/', format='json')
        assert res.status_code == 200
        assert res.data['profiles']['customer'] is True
        assert res.data['active_mode'] == 'customer'

    def test_never_creates_second_restaurant(self, auth_client, both_profiles_user):
        client = auth_client(both_profiles_user, active_mode=AppMode.CUSTOMER)
        res = client.post('/api/me/switch-to-restaurant/', format='json')
        assert res.status_code == 200
        assert res.data['needs_profile_update'] is False
        assert Restaurant.objects.filter(owner=both_profiles_user).count() == 1

    def test_add_restaurant_twice_conflict(self, auth_client, customer_user):
        client = auth_client(customer_user)
        first = client.post('/api/me/restaurants/', {'name': 'One'}, format='json')
        assert first.status_code == 201
        second = client.post('/api/me/restaurants/', {'name': 'Two'}, format='json')
        assert second.status_code == 409

    def test_add_customer_twice_conflict(self, auth_client, restaurant_user):
        client = auth_client(restaurant_user)
        first = client.post('/api/me/customer-profile/', format='json')
        assert first.status_code == 201
        second = client.post('/api/me/customer-profile/', format='json')
        assert second.status_code == 409

    def test_console_access(self, auth_client, restaurant_user, customer_user):
        ok = auth_client(restaurant_user).get('/api/me/console-access/')
        assert ok.status_code == 200
        assert ok.data['can_switch'] is True
        no = auth_client(customer_user).get('/api/me/console-access/')
        assert no.data['can_switch'] is False
