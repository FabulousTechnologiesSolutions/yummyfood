import pytest
from rest_framework import status

from apps.accounts.models import AppMode, CustomerNotificationSetting


@pytest.mark.django_db
class TestPreferences:
    def test_customer_preferences_defaults_and_patch(self, auth_client, customer_user):
        client = auth_client(customer_user)
        res = client.get('/api/me/preferences/')
        assert res.status_code == 200
        assert res.data['side'] == 'customer'
        assert res.data['max_distance_km'] == 5

        patch = client.patch(
            '/api/me/preferences/',
            {'max_distance_km': 10, 'cuisines': ['BBQ'], 'theme': 'dark'},
            format='json',
        )
        assert patch.status_code == 200
        assert patch.data['max_distance_km'] == 10
        assert patch.data['cuisines'] == ['BBQ']

    def test_invalid_distance(self, auth_client, customer_user):
        res = auth_client(customer_user).patch(
            '/api/me/preferences/',
            {'max_distance_km': 99},
            format='json',
        )
        assert res.status_code == 400

    def test_restaurant_preferences(self, auth_client, restaurant_user):
        client = auth_client(restaurant_user, active_mode=AppMode.RESTAURANT)
        res = client.get('/api/me/preferences/')
        assert res.status_code == 200
        assert res.data['side'] == 'restaurant'
        assert res.data['language'] == 'en'

        patch = client.patch('/api/me/preferences/', {'language': 'ur'}, format='json')
        assert patch.status_code == 200
        assert patch.data['language'] == 'ur'

    def test_customer_notifications_defaults(self, auth_client, customer_user):
        res = auth_client(customer_user).get('/api/me/notifications/')
        assert res.status_code == 200
        assert res.data['side'] == 'customer'
        assert res.data['enable_push_notification'] is True
        assert res.data['expiry_reminders'] is True
        assert res.data['nearby_flash_deals'] is False
        assert res.data['security_alerts'] is True

    def test_security_alerts_always_on(self, auth_client, customer_user):
        client = auth_client(customer_user)
        res = client.patch(
            '/api/me/notifications/',
            {
                'security_alerts': False,
                'weekly_digest': True,
                'enable_push_notification': False,
            },
            format='json',
        )
        assert res.status_code == 200
        assert res.data['security_alerts'] is True
        assert res.data['weekly_digest'] is True
        assert res.data['enable_push_notification'] is False
        setting = CustomerNotificationSetting.objects.get(
            customer_profile=customer_user.customer_profile
        )
        assert setting.security_alerts is True
        assert setting.enable_push_notification is False

    def test_restaurant_notifications(self, auth_client, restaurant_user):
        client = auth_client(restaurant_user, active_mode=AppMode.RESTAURANT)
        res = client.get('/api/me/notifications/')
        assert res.status_code == 200
        assert res.data['side'] == 'restaurant'
        assert res.data['enable_push_notification'] is True
        assert res.data['promo_status_alerts'] is True
        patch = client.patch(
            '/api/me/notifications/',
            {
                'weekly_performance_digest': True,
                'enable_push_notification': False,
            },
            format='json',
        )
        assert patch.status_code == 200
        assert patch.data['weekly_performance_digest'] is True
        assert patch.data['enable_push_notification'] is False

    def test_restaurant_only_cannot_get_customer_prefs(self, auth_client, restaurant_user):
        # restaurant active_mode uses restaurant prefs — OK
        # switch idea: customer prefs require customer profile
        restaurant_user.active_mode = AppMode.CUSTOMER
        restaurant_user.save(update_fields=['active_mode'])
        res = auth_client(restaurant_user).get('/api/me/preferences/')
        assert res.status_code == 403
