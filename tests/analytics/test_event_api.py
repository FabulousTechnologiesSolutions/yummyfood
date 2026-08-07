from datetime import timedelta

import pytest
from django.utils import timezone

from apps.analytics.models import ResourceAnalytics
from apps.promotions.models import FeaturedCampaign, PromotionRequestStatus
from tests.accounts.factories import UserFactory
from tests.discovery.factories import (
    DealFactory,
    FeaturedCampaignFactory,
    MenuItemFactory,
    PromoteRequestFactory,
)


@pytest.mark.django_db
def test_detail_view_increments_anon(api_client):
    item = MenuItemFactory()
    item.restaurant.lat = 31.52
    item.restaurant.lng = 74.35
    item.restaurant.save()
    res = api_client.post(
        '/api/analytics/event/',
        {'event_model': 'item', 'resource_id': item.id, 'event_type': 'detail_view'},
        format='json',
    )
    assert res.status_code == 200, res.data
    assert res.data['ok'] is True
    row = ResourceAnalytics.objects.get(menu_item=item, user=None)
    assert row.detail_views == 1
    assert row.engagement_score == pytest.approx(1.0)


@pytest.mark.django_db
def test_impression_rejected_from_client(api_client):
    item = MenuItemFactory()
    res = api_client.post(
        '/api/analytics/event/',
        {'event_model': 'item', 'resource_id': item.id, 'event_type': 'impression'},
        format='json',
    )
    assert res.status_code == 400
    assert res.data['error']['code'] == 'IMPRESSION_SERVER_ONLY'


@pytest.mark.django_db
def test_authed_creates_user_and_anon_rows(auth_client, customer_user):
    item = MenuItemFactory()
    client = auth_client(customer_user)
    res = client.post(
        '/api/analytics/event/',
        {'event_model': 'item', 'resource_id': item.id, 'event_type': 'call'},
        format='json',
    )
    assert res.status_code == 200
    assert ResourceAnalytics.objects.filter(menu_item=item, user=None).exists()
    assert ResourceAnalytics.objects.filter(menu_item=item, user=customer_user).exists()


@pytest.mark.django_db
def test_hidden_item_not_found(api_client):
    item = MenuItemFactory(status='hidden')
    res = api_client.post(
        '/api/analytics/event/',
        {'event_model': 'item', 'resource_id': item.id, 'event_type': 'detail_view'},
        format='json',
    )
    assert res.status_code == 404


@pytest.mark.django_db
def test_active_campaign_bumped(api_client):
    item = MenuItemFactory()
    req = PromoteRequestFactory(
        restaurant=item.restaurant,
        menu_item=item,
        status=PromotionRequestStatus.LIVE,
        goes_live_at=timezone.now() - timedelta(hours=1),
        ends_at=timezone.now() + timedelta(days=1),
    )
    camp = FeaturedCampaignFactory(
        menu_item=item,
        deal=None,
        promotion_request=req,
        started_at=req.goes_live_at,
        ends_at=req.ends_at,
    )
    api_client.post(
        '/api/analytics/event/',
        {'event_model': 'item', 'resource_id': item.id, 'event_type': 'whatsapp'},
        format='json',
    )
    camp.refresh_from_db()
    assert camp.whatsapp_clicks == 1


@pytest.mark.django_db
def test_deal_event(api_client):
    deal = DealFactory()
    res = api_client.post(
        '/api/analytics/event/',
        {'event_model': 'deal', 'resource_id': deal.id, 'event_type': 'share'},
        format='json',
    )
    assert res.status_code == 200
    assert ResourceAnalytics.objects.get(deal=deal, user=None).share_count == 1


@pytest.mark.django_db
def test_explore_serve_bumps_featured_campaign_impression(api_client):
    now = timezone.now()
    item = MenuItemFactory(
        is_promoted=True,
        promoted_starts_at=now - timedelta(hours=1),
        promoted_ends_at=now + timedelta(days=1),
    )
    item.restaurant.lat = 31.52
    item.restaurant.lng = 74.35
    item.restaurant.is_paused = False
    item.restaurant.is_permanently_closed = False
    item.restaurant.save()
    req = PromoteRequestFactory(
        restaurant=item.restaurant,
        menu_item=item,
        status=PromotionRequestStatus.LIVE,
        goes_live_at=item.promoted_starts_at,
        ends_at=item.promoted_ends_at,
    )
    camp = FeaturedCampaignFactory(
        menu_item=item,
        deal=None,
        promotion_request=req,
        started_at=item.promoted_starts_at,
        ends_at=item.promoted_ends_at,
        impression_count=0,
    )
    DealFactory(restaurant=item.restaurant)
    MenuItemFactory(restaurant=item.restaurant)

    res = api_client.get('/api/explore/products/?page_size=4')
    assert res.status_code == 200
    assert any(
        r['slot'] == 'promoted' and r['data']['id'] == item.id
        for r in res.data['results']
    )
    camp.refresh_from_db()
    assert camp.impression_count == 1


@pytest.mark.django_db
def test_expired_campaign_not_bumped_on_detail_view(api_client):
    item = MenuItemFactory()
    req = PromoteRequestFactory(
        restaurant=item.restaurant,
        menu_item=item,
        status=PromotionRequestStatus.ENDED,
        goes_live_at=timezone.now() - timedelta(days=5),
        ends_at=timezone.now() - timedelta(days=1),
    )
    camp = FeaturedCampaignFactory(
        menu_item=item,
        deal=None,
        promotion_request=req,
        started_at=req.goes_live_at,
        ends_at=req.ends_at,
        detail_views=0,
        impression_count=0,
    )
    res = api_client.post(
        '/api/analytics/event/',
        {'event_model': 'item', 'resource_id': item.id, 'event_type': 'detail_view'},
        format='json',
    )
    assert res.status_code == 200
    camp.refresh_from_db()
    assert camp.detail_views == 0
    assert camp.impression_count == 0


@pytest.mark.django_db
def test_detail_view_does_not_create_explore_impression(api_client):
    from apps.discovery.models import ExploreImpression

    item = MenuItemFactory()
    assert ExploreImpression.objects.count() == 0
    res = api_client.post(
        '/api/analytics/event/',
        {'event_model': 'item', 'resource_id': item.id, 'event_type': 'detail_view'},
        format='json',
    )
    assert res.status_code == 200
    assert ExploreImpression.objects.count() == 0
    assert not ExploreImpression.objects.filter(menu_item=item).exists()
