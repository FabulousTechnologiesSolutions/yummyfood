import pytest


@pytest.mark.django_db
class TestProfileApi:
    def test_profiles_endpoint(self, auth_client, both_profiles_user):
        res = auth_client(both_profiles_user).get('/api/me/profiles/')
        assert res.status_code == 200
        assert res.data['customer'] is True
        assert res.data['restaurant'] is True
        assert 'restaurant_id' in res.data

    def test_guest_migrate(self, auth_client, customer_user):
        from tests.accounts.factories import GuestSessionFactory

        guest = GuestSessionFactory(session_key='mig-1')
        client = auth_client(customer_user)
        res = client.post('/api/auth/guest/migrate/', {'session_key': 'mig-1'}, format='json')
        assert res.status_code == 200
        assert res.data['merged'] is True
        guest.refresh_from_db()
        assert guest.merged_into_user_id == customer_user.id
        # idempotent
        again = client.post('/api/auth/guest/migrate/', {'session_key': 'mig-1'}, format='json')
        assert again.data['idempotent'] is True
