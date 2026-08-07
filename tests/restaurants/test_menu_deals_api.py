import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from apps.restaurants.models import MenuCategory


def put_tmp_file(restaurant_id, name='img.jpg', content=b'fake-image'):
    key = f'uploads/tmp/{restaurant_id}/{uuid.uuid4().hex}_{name}'
    default_storage.save(key, ContentFile(content))
    return key


def media_payload(restaurant_id):
    img = put_tmp_file(restaurant_id, 'cover.jpg')
    img2 = put_tmp_file(restaurant_id, 'side.jpg')
    vid = put_tmp_file(restaurant_id, 'clip.mp4', b'fake-video')
    return [
        {'type': 'image', 'url': img, 'is_cover': True},
        {'type': 'image', 'url': img2},
        {'type': 'video', 'url': vid},
    ]


@pytest.fixture
def restaurant(restaurant_user):
    return restaurant_user.restaurant


@pytest.fixture
def category(restaurant):
    # Global seed runs with restaurant creation
    return MenuCategory.objects.filter(slug='burgers').first() or MenuCategory.objects.first()


@pytest.mark.django_db
def test_categories_seeded_globally(restaurant):
    assert MenuCategory.objects.count() >= 17
    assert MenuCategory.objects.filter(slug='burgers').exists()


@pytest.mark.django_db
def test_list_categories(auth_client, restaurant_user, restaurant):
    client = auth_client(restaurant_user)
    res = client.get('/api/restaurant/categories/')
    assert res.status_code == 200
    assert len(res.data) >= 17


@pytest.mark.django_db
def test_create_menu_item(auth_client, restaurant_user, restaurant, category, monkeypatch):
    monkeypatch.setattr(
        'apps.mediahub.tasks.process_content_video.delay',
        lambda *a, **k: None,
    )
    client = auth_client(restaurant_user)
    payload = {
        'category_ids': [category.id],
        'name': 'Chicken Burger',
        'description': 'Juicy',
        'item_type': 'Chicken',
        'sizes': [{'label': 'Regular', 'price': '450.00'}],
        'media': media_payload(restaurant.id),
    }
    res = client.post('/api/restaurant/menu-items/', payload, format='json')
    assert res.status_code == 201, res.data
    assert res.data['name'] == 'Chicken Burger'
    assert res.data['status'] == 'published'
    assert len(res.data['sizes']) == 1
    assert len(res.data['media']) == 3
    assert restaurant.__class__.objects.get(pk=restaurant.pk).products_created_this_month == 1


@pytest.mark.django_db
def test_product_quota(auth_client, restaurant_user, restaurant, category, monkeypatch, settings):
    monkeypatch.setattr(
        'apps.mediahub.tasks.process_content_video.delay',
        lambda *a, **k: None,
    )
    settings.FREE_TIER_PRODUCTS_PER_MONTH = 1
    client = auth_client(restaurant_user)
    payload = {
        'category_ids': [category.id],
        'name': 'Item 1',
        'sizes': [{'label': 'R', 'price': '100.00'}],
        'media': media_payload(restaurant.id),
    }
    assert client.post('/api/restaurant/menu-items/', payload, format='json').status_code == 201
    payload['name'] = 'Item 2'
    payload['media'] = media_payload(restaurant.id)
    res = client.post('/api/restaurant/menu-items/', payload, format='json')
    assert res.status_code == 403
    assert res.data['error']['code'] == 'PRODUCT_QUOTA_EXCEEDED'


@pytest.mark.django_db
def test_offer_price_validation(auth_client, restaurant_user, restaurant, category):
    client = auth_client(restaurant_user)
    payload = {
        'category_ids': [category.id],
        'name': 'Bad Offer',
        'sizes': [{'label': 'R', 'price': '100.00', 'offer_price': '150.00'}],
        'media': media_payload(restaurant.id),
    }
    res = client.post('/api/restaurant/menu-items/', payload, format='json')
    assert res.status_code == 400
    assert res.data['error']['code'] == 'INVALID_OFFER_PRICE'


@pytest.mark.django_db
def test_public_restaurant_profile(
    auth_client, restaurant_user, restaurant, category, monkeypatch, api_client
):
    monkeypatch.setattr(
        'apps.mediahub.tasks.process_content_video.delay',
        lambda *a, **k: None,
    )
    client = auth_client(restaurant_user)
    item_res = client.post(
        '/api/restaurant/menu-items/',
        {
            'category_ids': [category.id],
            'name': 'Public Burger',
            'sizes': [{'label': 'R', 'price': '200.00'}],
            'media': media_payload(restaurant.id),
        },
        format='json',
    )
    assert item_res.status_code == 201
    now = timezone.now()
    deal_res = client.post(
        '/api/restaurant/deals/',
        {
            'label': 'Public Deal',
            'deal_price': '150.00',
            'starts_at': now.isoformat(),
            'ends_at': (now + timedelta(days=3)).isoformat(),
            'lines': [
                {
                    'menu_item_id': item_res.data['id'],
                    'size_label': 'R',
                    'unit_price': '200.00',
                    'quantity': 1,
                }
            ],
            'media': media_payload(restaurant.id),
        },
        format='json',
    )
    assert deal_res.status_code == 201

    res = api_client.get(f'/api/public/restaurants/{restaurant.id}/')
    assert res.status_code == 200
    assert res.data['restaurant']['id'] == restaurant.id
    assert res.data['restaurant']['name'] == restaurant.name
    assert 'logo' in res.data['restaurant']
    assert 'cover' in res.data['restaurant']
    assert 'lat' in res.data['restaurant']
    assert 'lng' in res.data['restaurant']
    assert 'street_address' in res.data['restaurant']
    assert any(i['name'] == 'Public Burger' for i in res.data['menu_items'])
    assert any(d['label'] == 'Public Deal' for d in res.data['deals'])
    assert len(res.data['categories']) >= 1

    detail = api_client.get(f'/api/public/deals/{deal_res.data["id"]}/')
    assert detail.status_code == 200
    item_detail = api_client.get(f'/api/public/menu-items/{item_res.data["id"]}/')
    assert item_detail.status_code == 200


@pytest.mark.django_db
def test_create_deal(auth_client, restaurant_user, restaurant, category, monkeypatch):
    monkeypatch.setattr(
        'apps.mediahub.tasks.process_content_video.delay',
        lambda *a, **k: None,
    )
    client = auth_client(restaurant_user)
    item_res = client.post(
        '/api/restaurant/menu-items/',
        {
            'category_ids': [category.id],
            'name': 'Deal Burger',
            'sizes': [{'label': 'Regular', 'price': '500.00'}],
            'media': media_payload(restaurant.id),
        },
        format='json',
    )
    assert item_res.status_code == 201
    item_id = item_res.data['id']
    now = timezone.now()
    deal_payload = {
        'label': 'Lunch Deal',
        'deal_price': '400.00',
        'starts_at': now.isoformat(),
        'ends_at': (now + timedelta(days=7)).isoformat(),
        'days_of_week': [0, 1, 2, 3, 4],
        'lines': [
            {
                'menu_item_id': item_id,
                'size_label': 'Regular',
                'unit_price': '500.00',
                'quantity': 1,
            }
        ],
        'media': media_payload(restaurant.id),
    }
    res = client.post('/api/restaurant/deals/', deal_payload, format='json')
    assert res.status_code == 201, res.data
    assert Decimal(res.data['items_total']) == Decimal('500.00')
    assert Decimal(res.data['savings_amount']) == Decimal('100.00')
    assert res.data['status'] == 'active'


@pytest.mark.django_db
def test_deal_price_must_be_less_than_total(
    auth_client, restaurant_user, restaurant, category, monkeypatch
):
    monkeypatch.setattr(
        'apps.mediahub.tasks.process_content_video.delay',
        lambda *a, **k: None,
    )
    client = auth_client(restaurant_user)
    item_res = client.post(
        '/api/restaurant/menu-items/',
        {
            'category_ids': [category.id],
            'name': 'X',
            'sizes': [{'label': 'R', 'price': '100.00'}],
            'media': media_payload(restaurant.id),
        },
        format='json',
    )
    now = timezone.now()
    res = client.post(
        '/api/restaurant/deals/',
        {
            'label': 'Bad',
            'deal_price': '100.00',
            'starts_at': now.isoformat(),
            'ends_at': (now + timedelta(days=1)).isoformat(),
            'lines': [
                {
                    'menu_item_id': item_res.data['id'],
                    'size_label': 'R',
                    'unit_price': '100.00',
                    'quantity': 1,
                }
            ],
            'media': media_payload(restaurant.id),
        },
        format='json',
    )
    assert res.status_code == 400
    assert res.data['error']['code'] == 'INVALID_DEAL_PRICE'


@pytest.mark.django_db
def test_customer_mode_blocked_from_restaurant_apis(
    auth_client, both_profiles_user, monkeypatch
):
    monkeypatch.setattr(
        'apps.mediahub.tasks.process_content_video.delay',
        lambda *a, **k: None,
    )
    restaurant = both_profiles_user.restaurant
    category = MenuCategory.objects.filter(slug='burgers').first() or MenuCategory.objects.first()
    client = auth_client(both_profiles_user, active_mode='customer')
    res = client.get('/api/restaurant/categories/')
    assert res.status_code == 403
    assert res.data['error']['code'] == 'RESTAURANT_MODE_REQUIRED'

    payload = {
        'category_ids': [category.id],
        'name': 'Should Fail',
        'sizes': [{'label': 'R', 'price': '100.00'}],
        'media': media_payload(restaurant.id),
    }
    res = client.post('/api/restaurant/menu-items/', payload, format='json')
    assert res.status_code == 403
    assert res.data['error']['code'] == 'RESTAURANT_MODE_REQUIRED'


@pytest.mark.django_db
def test_restaurant_mode_allows_dual_profile_user(
    auth_client, both_profiles_user, monkeypatch
):
    monkeypatch.setattr(
        'apps.mediahub.tasks.process_content_video.delay',
        lambda *a, **k: None,
    )
    restaurant = both_profiles_user.restaurant
    category = MenuCategory.objects.filter(slug='burgers').first() or MenuCategory.objects.first()
    client = auth_client(both_profiles_user, active_mode='restaurant')
    res = client.get('/api/restaurant/categories/')
    assert res.status_code == 200
    payload = {
        'category_ids': [category.id],
        'name': 'Allowed Burger',
        'sizes': [{'label': 'R', 'price': '100.00'}],
        'media': media_payload(restaurant.id),
    }
    res = client.post('/api/restaurant/menu-items/', payload, format='json')
    assert res.status_code == 201, res.data
    assert res.data['name'] == 'Allowed Burger'
