import pytest
from django.core.management import call_command

from apps.geo.models import City
from tests.accounts.factories import RestaurantFactory, UserFactory, access_token_for
from tests.geo.factories import CityFactory
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_seed_cities_idempotent():
    call_command('seed_cities')
    call_command('seed_cities')
    names = list(City.objects.order_by('id').values_list('name', flat=True))
    assert names == ['Karachi', 'Lahore', 'Islamabad', 'Faisalabad', 'Multan']
    assert City.objects.count() == 5


@pytest.mark.django_db
def test_cities_list_public(api_client):
    CityFactory(name='Visible')
    CityFactory(name='Hidden', is_active=False)
    res = api_client.get('/api/cities/')
    assert res.status_code == 200
    names = [c['name'] for c in res.data['results']]
    assert 'Visible' in names
    assert 'Hidden' not in names


@pytest.mark.django_db
def test_cities_picker_live_count(api_client):
    city = CityFactory(name='Lahore')
    r = RestaurantFactory()
    r.city = city
    r.is_paused = False
    r.is_permanently_closed = False
    r.save()
    RestaurantFactory()  # different city / no city — not counted for Lahore

    paused = RestaurantFactory()
    paused.city = city
    paused.is_paused = True
    paused.save()

    res = api_client.get('/api/cities/picker/')
    assert res.status_code == 200
    popular = res.data['popular']
    row = next(c for c in popular if c['name'] == 'Lahore')
    assert row['restaurant_count'] == 1


@pytest.mark.django_db
def test_cities_search(api_client):
    CityFactory(name='Lahore')
    CityFactory(name='Karachi')
    res = api_client.get('/api/cities/search/', {'q': 'lah'})
    assert res.status_code == 200
    assert len(res.data) == 1
    assert res.data[0]['name'] == 'Lahore'


@pytest.mark.django_db
def test_cities_staff_crud(api_client):
    staff = UserFactory(is_staff=True, is_superuser=True)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token_for(staff)}')

    create = client.post('/api/cities/', {'name': 'Sialkot', 'is_active': True}, format='json')
    assert create.status_code == 201
    city_id = create.data['id']

    patch = client.patch(f'/api/cities/{city_id}/', {'name': 'Sialkot City'}, format='json')
    assert patch.status_code == 200
    assert patch.data['name'] == 'Sialkot City'

    guest = api_client.post('/api/cities/', {'name': 'Nope'}, format='json')
    assert guest.status_code in (401, 403)

    delete = client.delete(f'/api/cities/{city_id}/')
    assert delete.status_code == 204
    assert not City.objects.filter(id=city_id).exists()
