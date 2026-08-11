import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image


def _png_file(name='image.png'):
    buf = BytesIO()
    Image.new('RGB', (8, 8), color=(20, 120, 200)).save(buf, format='PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


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

    def test_restaurant_branding_cover_and_logo(self, auth_client, restaurant_user):
        client = auth_client(restaurant_user)
        res = client.post(
            '/api/me/restaurant/branding/',
            {'type': 'cover', 'image': _png_file('cover.png')},
            format='multipart',
        )
        assert res.status_code == 200
        assert res.data['type'] == 'cover'
        cover_url = res.data['restaurant']['cover']
        assert cover_url.startswith(('http://', 'https://'))
        assert res.data['restaurant']['id'] == restaurant_user.restaurant.id

        res2 = client.post(
            '/api/me/restaurant/branding/',
            {'type': 'logo', 'image': _png_file('logo.png')},
            format='multipart',
        )
        assert res2.status_code == 200
        assert res2.data['type'] == 'logo'
        logo_url = res2.data['restaurant']['logo']
        assert logo_url.startswith(('http://', 'https://'))
        restaurant_user.restaurant.refresh_from_db()
        assert restaurant_user.restaurant.cover
        assert restaurant_user.restaurant.logo

    def test_restaurant_branding_requires_restaurant(self, auth_client, customer_user):
        res = auth_client(customer_user).post(
            '/api/me/restaurant/branding/',
            {'type': 'cover', 'image': _png_file('cover.png')},
            format='multipart',
        )
        assert res.status_code == 403
        assert res.data['error']['code'] == 'RESTAURANT_REQUIRED'

    def test_get_and_patch_restaurant_profile(self, auth_client, restaurant_user):
        from tests.geo.factories import CityFactory

        city = CityFactory(name='Lahore')
        client = auth_client(restaurant_user)
        get_res = client.get('/api/me/restaurant/')
        assert get_res.status_code == 200
        assert get_res.data['id'] == restaurant_user.restaurant.id
        assert get_res.data['name'] == restaurant_user.restaurant.name

        patch_res = client.patch(
            '/api/me/restaurant/',
            {
                'name': 'Updated House',
                'short_description': 'Tasty',
                'cuisines': ['Burgers', 'Fries'],
                'price_range': '200-7000',
                'primary_phone': '03001234567',
                'street_address': '12 Mall Road',
                'area': 'Gulberg',
                'city_id': city.id,
                'lat': '31.520400',
                'lng': '74.358700',
                'is_paused': True,
                'promo_default_radius_km': 8,
            },
            format='json',
        )
        assert patch_res.status_code == 200
        assert patch_res.data['name'] == 'Updated House'
        assert patch_res.data['cuisines'] == ['Burgers', 'Fries']
        assert patch_res.data['price_range'] == '200-7000'
        assert patch_res.data['primary_phone'] == '+923001234567'
        assert patch_res.data['city_id'] == city.id
        assert patch_res.data['city'] == 'Lahore'
        assert patch_res.data['lat'] == '31.520400'
        assert patch_res.data['lng'] == '74.358700'
        assert patch_res.data['is_paused'] is True
        assert patch_res.data['promo_default_radius_km'] == 8
        restaurant_user.restaurant.refresh_from_db()
        assert restaurant_user.restaurant.name == 'Updated House'
        assert restaurant_user.restaurant.is_paused is True

    def test_patch_restaurant_rejects_too_many_cuisines(self, auth_client, restaurant_user):
        res = auth_client(restaurant_user).patch(
            '/api/me/restaurant/',
            {'cuisines': ['A', 'B', 'C', 'D']},
            format='json',
        )
        assert res.status_code == 400

    def test_patch_restaurant_requires_restaurant(self, auth_client, customer_user):
        res = auth_client(customer_user).patch(
            '/api/me/restaurant/',
            {'name': 'Nope'},
            format='json',
        )
        assert res.status_code == 403
        assert res.data['error']['code'] == 'RESTAURANT_REQUIRED'
