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
