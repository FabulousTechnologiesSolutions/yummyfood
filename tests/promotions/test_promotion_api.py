from datetime import timedelta

import pytest
from django.utils import timezone

from apps.promotions.models import FeaturedCampaign, PromotionRequestStatus
from apps.promotions.services import expire_promotion_resources
from apps.promotions.tasks import expire_promotions
from tests.accounts.factories import UserFactory
from tests.discovery.factories import DealFactory, MenuItemFactory, PromoteRequestFactory


@pytest.mark.django_db
def test_owner_create_and_list(auth_client, restaurant_user):
    restaurant = restaurant_user.restaurant
    item = MenuItemFactory(restaurant=restaurant)
    client = auth_client(restaurant_user)
    start = timezone.now()
    end = start + timedelta(days=3)
    res = client.post(
        '/api/restaurant/promotion-requests/',
        {
            'event_model': 'item',
            'resource_id': item.id,
            'requested_start': start.isoformat(),
            'requested_end': end.isoformat(),
        },
        format='json',
    )
    assert res.status_code == 201, res.data
    assert res.data['status'] == 'pending'
    listed = client.get('/api/restaurant/promotion-requests/')
    assert listed.status_code == 200
    assert len(listed.data) >= 1


@pytest.mark.django_db
def test_create_rejects_bad_window(auth_client, restaurant_user):
    restaurant = restaurant_user.restaurant
    item = MenuItemFactory(restaurant=restaurant)
    client = auth_client(restaurant_user)
    now = timezone.now()
    res = client.post(
        '/api/restaurant/promotion-requests/',
        {
            'event_model': 'item',
            'resource_id': item.id,
            'requested_start': now.isoformat(),
            'requested_end': (now - timedelta(hours=1)).isoformat(),
        },
        format='json',
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_admin_approve_sets_promoted(auth_client, restaurant_user):
    restaurant = restaurant_user.restaurant
    item = MenuItemFactory(restaurant=restaurant)
    req = PromoteRequestFactory(restaurant=restaurant, menu_item=item)
    admin = UserFactory(is_staff=True, is_superuser=True)
    client = auth_client(admin)
    res = client.post(f'/api/admin-api/promotion-requests/{req.id}/approve/', {}, format='json')
    assert res.status_code == 200, res.data
    assert res.data['status'] == 'live'
    item.refresh_from_db()
    assert item.is_promoted is True
    assert FeaturedCampaign.objects.filter(menu_item=item).exists()


@pytest.mark.django_db
def test_admin_reject(auth_client, restaurant_user):
    restaurant = restaurant_user.restaurant
    item = MenuItemFactory(restaurant=restaurant)
    req = PromoteRequestFactory(restaurant=restaurant, menu_item=item)
    admin = UserFactory(is_staff=True, is_superuser=True)
    client = auth_client(admin)
    res = client.post(
        f'/api/admin-api/promotion-requests/{req.id}/reject/',
        {'admin_note': 'needs clearer video'},
        format='json',
    )
    assert res.status_code == 200
    assert res.data['status'] == 'changes'
    item.refresh_from_db()
    assert item.is_promoted is False


@pytest.mark.django_db
def test_double_approve_fails(auth_client, restaurant_user):
    restaurant = restaurant_user.restaurant
    item = MenuItemFactory(restaurant=restaurant)
    req = PromoteRequestFactory(restaurant=restaurant, menu_item=item)
    admin = UserFactory(is_staff=True, is_superuser=True)
    client = auth_client(admin)
    assert client.post(f'/api/admin-api/promotion-requests/{req.id}/approve/', {}).status_code == 200
    res = client.post(f'/api/admin-api/promotion-requests/{req.id}/approve/', {})
    assert res.status_code == 400


@pytest.mark.django_db
def test_expire_promotions_clears_flag(restaurant_user):
    restaurant = restaurant_user.restaurant
    item = MenuItemFactory(
        restaurant=restaurant,
        is_promoted=True,
        promoted_starts_at=timezone.now() - timedelta(days=5),
        promoted_ends_at=timezone.now() - timedelta(hours=1),
    )
    req = PromoteRequestFactory(
        restaurant=restaurant,
        menu_item=item,
        status=PromotionRequestStatus.LIVE,
        goes_live_at=item.promoted_starts_at,
        ends_at=item.promoted_ends_at,
    )
    expire_promotions()
    item.refresh_from_db()
    req.refresh_from_db()
    assert item.is_promoted is False
    assert req.status == PromotionRequestStatus.ENDED


@pytest.mark.django_db
def test_admin_approve_deal_sets_promoted(auth_client, restaurant_user):
    restaurant = restaurant_user.restaurant
    deal = DealFactory(restaurant=restaurant)
    req = PromoteRequestFactory(
        restaurant=restaurant,
        menu_item=None,
        deal=deal,
    )
    admin = UserFactory(is_staff=True, is_superuser=True)
    client = auth_client(admin)
    res = client.post(f'/api/admin-api/promotion-requests/{req.id}/approve/', {}, format='json')
    assert res.status_code == 200, res.data
    assert res.data['status'] == 'live'
    deal.refresh_from_db()
    assert deal.is_promoted is True
    assert deal.promoted_starts_at is not None
    assert deal.promoted_ends_at is not None
    assert FeaturedCampaign.objects.filter(deal=deal, menu_item__isnull=True).exists()


@pytest.mark.django_db
def test_admin_promotion_requests_list_paginated(auth_client, restaurant_user):
    restaurant = restaurant_user.restaurant
    for _ in range(12):
        PromoteRequestFactory(
            restaurant=restaurant,
            menu_item=MenuItemFactory(restaurant=restaurant),
        )
    admin = UserFactory(is_staff=True, is_superuser=True)
    client = auth_client(admin)

    page1 = client.get('/api/admin/promotion-requests/?page=1&page_size=10')
    assert page1.status_code == 200, page1.data
    assert page1.data['count'] >= 12
    assert len(page1.data['results']) == 10
    assert page1.data['next']
    assert page1.data['previous'] is None
    assert 'title' in page1.data['results'][0]
    assert 'restaurant_name' in page1.data['results'][0]

    page2 = client.get('/api/admin/promotion-requests/?page=2&page_size=10')
    assert page2.status_code == 200
    assert len(page2.data['results']) >= 2
    assert page2.data['previous']
    ids1 = {row['id'] for row in page1.data['results']}
    ids2 = {row['id'] for row in page2.data['results']}
    assert not ids1.intersection(ids2)


@pytest.mark.django_db
def test_new_admin_approve_requires_window(auth_client, restaurant_user, api_client):
    restaurant = restaurant_user.restaurant
    item = MenuItemFactory(restaurant=restaurant)
    req = PromoteRequestFactory(restaurant=restaurant, menu_item=item)
    admin = UserFactory(is_staff=True, is_superuser=True)
    client = auth_client(admin)

    missing = client.post(f'/api/admin/promotion-requests/{req.id}/approve/', {}, format='json')
    assert missing.status_code == 400

    start = timezone.now()
    end = start + timedelta(days=2)
    res = client.post(
        f'/api/admin/promotion-requests/{req.id}/approve/',
        {'starts_at': start.isoformat(), 'ends_at': end.isoformat()},
        format='json',
    )
    assert res.status_code == 200, res.data
    assert res.data['status'] == 'live'
    item.refresh_from_db()
    assert item.is_promoted is True
    assert item.promoted_starts_at is not None
    assert item.promoted_ends_at is not None

    public = api_client.get(f'/api/public/menu-items/{item.id}/')
    assert public.status_code == 200
    assert public.data['is_promoted'] is True
    assert public.data['promoted_starts_at']
    assert public.data['promoted_ends_at']


@pytest.mark.django_db
def test_new_admin_reject_requires_note(auth_client, restaurant_user):
    restaurant = restaurant_user.restaurant
    item = MenuItemFactory(restaurant=restaurant)
    req = PromoteRequestFactory(restaurant=restaurant, menu_item=item)
    admin = UserFactory(is_staff=True, is_superuser=True)
    client = auth_client(admin)

    missing = client.post(f'/api/admin/promotion-requests/{req.id}/reject/', {}, format='json')
    assert missing.status_code == 400

    res = client.post(
        f'/api/admin/promotion-requests/{req.id}/reject/',
        {'admin_note': 'Needs a clearer video and better price'},
        format='json',
    )
    assert res.status_code == 200, res.data
    assert res.data['status'] == 'changes'
    assert res.data['admin_note'] == 'Needs a clearer video and better price'
    item.refresh_from_db()
    assert item.is_promoted is False


@pytest.mark.django_db
def test_expire_at_ends_at_equals_now_clears_flag(restaurant_user):
    restaurant = restaurant_user.restaurant
    now = timezone.now()
    item = MenuItemFactory(
        restaurant=restaurant,
        is_promoted=True,
        promoted_starts_at=now - timedelta(days=2),
        promoted_ends_at=now,
    )
    req = PromoteRequestFactory(
        restaurant=restaurant,
        menu_item=item,
        status=PromotionRequestStatus.LIVE,
        goes_live_at=item.promoted_starts_at,
        ends_at=now,
    )
    cleared = expire_promotion_resources(now=now)
    assert cleared >= 1
    item.refresh_from_db()
    req.refresh_from_db()
    assert item.is_promoted is False
    assert req.status == PromotionRequestStatus.ENDED
