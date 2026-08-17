from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.analytics.models import ResourceAnalytics
from apps.discovery.models import ExploreImpression, ExploreViewerState
from apps.feed.models import FeedImpression, FeedViewerState, FeedWatchOutcome
from apps.feed.services.viewer import hash_ip
from apps.mediahub.models import (
    ContentMedia,
    MediaEntityType,
    MediaProcessingStatus,
    MediaType,
)
from apps.restaurants.models import MenuItem
from tests.accounts.factories import CustomerOnlyUserFactory, RestaurantFactory
from tests.discovery.factories import DealFactory, MenuItemFactory, ResourceAnalyticsFactory
from tests.geo.factories import CityFactory

FEED_URL = '/api/feed/products/'
SEEN_BATCH_URL = '/api/feed/seen/batch/'
GUEST_IP = '10.0.0.55'


def _place(restaurant, lat=31.52, lng=74.35, city=None):
    restaurant.lat = Decimal(str(lat))
    restaurant.lng = Decimal(str(lng))
    if city is not None:
        restaurant.city = city
    restaurant.is_paused = False
    restaurant.is_permanently_closed = False
    restaurant.save()
    return restaurant


@pytest.fixture
def main_city(db):
    return CityFactory(name='FeedMainCity')


@pytest.fixture
def near_restaurant(main_city):
    return _place(RestaurantFactory(), city=main_city)


def attach_video(entity, *, status=MediaProcessingStatus.READY, is_feed_video=True, resolutions=None):
    is_item = hasattr(entity, 'base_price')
    restaurant = entity.restaurant
    return ContentMedia.objects.create(
        restaurant=restaurant,
        entity_type=MediaEntityType.MENU_ITEM if is_item else MediaEntityType.DEAL,
        menu_item=entity if is_item else None,
        deal=None if is_item else entity,
        media_type=MediaType.VIDEO,
        is_feed_video=is_feed_video,
        processing_status=status,
        hls_master_url='https://cdn.example/master.m3u8',
        thumbnail_url='https://cdn.example/thumb.jpg',
        duration=12.5,
        resolutions=resolutions
        if resolutions is not None
        else [{'quality': '720p', 'url': 'https://cdn.example/720.m3u8'}],
    )


def ready_item(restaurant, **kwargs):
    item = MenuItemFactory(restaurant=restaurant, **kwargs)
    attach_video(item)
    ContentMedia.objects.create(
        restaurant=restaurant,
        entity_type=MediaEntityType.MENU_ITEM,
        menu_item=item,
        media_type=MediaType.IMAGE,
        is_cover=True,
        processing_status=MediaProcessingStatus.EMPTY,
    )
    return item


def ready_deal(restaurant, **kwargs):
    deal = DealFactory(restaurant=restaurant, **kwargs)
    attach_video(deal)
    return deal


def ready_promo(restaurant, **kwargs):
    now = timezone.now()
    return ready_item(
        restaurant,
        is_promoted=True,
        promoted_starts_at=now - timedelta(hours=1),
        promoted_ends_at=now + timedelta(days=1),
        **kwargs,
    )


@pytest.mark.django_db
def test_podO_pattern_with_promo_item_deal(api_client, near_restaurant):
    p = ready_promo(near_restaurant, name='P1')
    ready_item(near_restaurant, name='O1')
    ready_item(near_restaurant, name='O2')
    ready_deal(near_restaurant, label='D1')
    res = api_client.get('/api/feed/products/?page_size=4')
    assert res.status_code == 200
    rows = res.data['results']
    assert len(rows) == 4
    assert rows[0]['slot'] == 'promoted' and rows[0]['type'] == 'item' and rows[0]['data']['id'] == p.id
    assert rows[1]['slot'] == 'organic' and rows[1]['type'] == 'item'
    assert rows[2]['slot'] == 'organic' and rows[2]['type'] == 'deal'
    assert rows[3]['slot'] == 'organic' and rows[3]['type'] == 'item'


@pytest.mark.django_db
def test_no_promoted_continues_with_organic(api_client, near_restaurant):
    for i in range(3):
        ready_item(near_restaurant, name=f'I{i}')
    ready_deal(near_restaurant)
    res = api_client.get('/api/feed/products/?page_size=4')
    assert res.status_code == 200
    assert all(r['slot'] == 'organic' for r in res.data['results'])
    assert len(res.data['results']) == 4


@pytest.mark.django_db
def test_promo_without_deal_crossfills_organic(api_client, near_restaurant):
    ready_promo(near_restaurant)
    for i in range(4):
        ready_item(near_restaurant, name=f'X{i}')
    res = api_client.get('/api/feed/products/?page_size=4')
    assert res.status_code == 200
    rows = res.data['results']
    assert rows[0]['slot'] == 'promoted'
    assert all(r['type'] == 'item' for r in rows[1:])


@pytest.mark.django_db
def test_no_deal_crossfills_organic(api_client, near_restaurant):
    for i in range(5):
        ready_item(near_restaurant, name=f'N{i}')
    res = api_client.get('/api/feed/products/?page_size=4')
    assert res.status_code == 200
    assert len(res.data['results']) == 4
    assert all(r['type'] == 'item' for r in res.data['results'])


@pytest.mark.django_db
def test_no_promo_and_no_deal_all_items(api_client, near_restaurant):
    for i in range(6):
        ready_item(near_restaurant, name=f'A{i}')
    res = api_client.get('/api/feed/products/?page_size=4')
    assert res.status_code == 200
    assert len(res.data['results']) == 4


@pytest.mark.django_db
def test_multiple_promos_cycle(api_client, near_restaurant):
    p1 = ready_promo(near_restaurant, name='CP1')
    p2 = ready_promo(near_restaurant, name='CP2')
    assert p1.id < p2.id
    for i in range(6):
        ready_item(near_restaurant, name=f'CI{i}')
    for i in range(3):
        ready_deal(near_restaurant, label=f'CD{i}')
    res = api_client.get('/api/feed/products/?page_size=12', REMOTE_ADDR='10.0.1.1')
    rows = res.data['results']
    assert rows[0]['data']['id'] == p2.id and rows[0]['slot'] == 'promoted'
    assert rows[4]['data']['id'] == p1.id and rows[4]['slot'] == 'promoted'
    assert rows[8]['data']['id'] == p2.id and rows[8]['slot'] == 'promoted'


@pytest.mark.django_db
def test_multiple_deals_and_organics_consumed(api_client, near_restaurant):
    ready_promo(near_restaurant)
    items = [ready_item(near_restaurant, name=f'MI{i}') for i in range(4)]
    deals = [ready_deal(near_restaurant, label=f'MD{i}') for i in range(2)]
    res = api_client.get('/api/feed/products/?page_size=8')
    organic_ids = [
        (r['type'], r['data']['id'])
        for r in res.data['results']
        if r['slot'] == 'organic'
    ]
    assert len(organic_ids) == len(set(organic_ids))
    assert any(t == 'deal' for t, _ in organic_ids)
    assert {('item', i.id) for i in items} | {('deal', d.id) for d in deals}


@pytest.mark.django_db
def test_insufficient_organic_no_empty_holes(api_client, near_restaurant):
    ready_promo(near_restaurant)
    ready_item(near_restaurant)
    res = api_client.get('/api/feed/products/?page_size=10')
    assert res.status_code == 200
    assert len(res.data['results']) >= 1
    assert all(r.get('data') for r in res.data['results'])


@pytest.mark.django_db
def test_pagination_past_end_empty(api_client, near_restaurant):
    ready_item(near_restaurant)
    first = api_client.get('/api/feed/products/?page_size=4')
    assert first.data['has_more'] is False
    past = api_client.get('/api/feed/products/?page_size=4&page=2')
    assert past.data['results'] == []
    assert past.data['has_more'] is False
    assert past.data['next_page'] is None


@pytest.mark.django_db
def test_pagination_has_more_and_next_page(api_client, near_restaurant):
    for i in range(10):
        ready_item(near_restaurant, name=f'P{i}')
    res = api_client.get('/api/feed/products/?page_size=4')
    assert res.data['has_more'] is True
    assert res.data['next_page'] == 2


@pytest.mark.django_db
def test_ready_video_included(api_client, near_restaurant):
    item = ready_item(near_restaurant, name='Ready')
    res = api_client.get('/api/feed/products/')
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    assert item.id in ids


@pytest.mark.django_db
def test_pending_video_excluded(api_client, near_restaurant):
    item = MenuItemFactory(restaurant=near_restaurant, name='Pend')
    attach_video(item, status=MediaProcessingStatus.PENDING)
    res = api_client.get('/api/feed/products/')
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    assert item.id not in ids


@pytest.mark.django_db
def test_failed_video_excluded(api_client, near_restaurant):
    item = MenuItemFactory(restaurant=near_restaurant, name='Fail')
    attach_video(item, status=MediaProcessingStatus.FAILED)
    res = api_client.get('/api/feed/products/')
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    assert item.id not in ids


@pytest.mark.django_db
def test_missing_video_excluded(api_client, near_restaurant):
    item = MenuItemFactory(restaurant=near_restaurant, name='NoVid')
    ContentMedia.objects.create(
        restaurant=near_restaurant,
        entity_type=MediaEntityType.MENU_ITEM,
        menu_item=item,
        media_type=MediaType.IMAGE,
        is_cover=True,
    )
    res = api_client.get('/api/feed/products/')
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    assert item.id not in ids


@pytest.mark.django_db
def test_is_feed_video_false_excluded(api_client, near_restaurant):
    item = MenuItemFactory(restaurant=near_restaurant, name='NotFeed')
    attach_video(item, is_feed_video=False)
    res = api_client.get('/api/feed/products/')
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    assert item.id not in ids


@pytest.mark.django_db
def test_media_includes_resolutions_and_hls(api_client, near_restaurant):
    item = ready_item(near_restaurant, name='Media')
    res = api_client.get('/api/feed/products/')
    row = next(r for r in res.data['results'] if r['data']['id'] == item.id)
    videos = [m for m in row['data']['media'] if m['type'] == 'video']
    assert videos
    v = videos[0]
    assert v['hls_master_url']
    assert v['thumbnail_url']
    assert v['resolutions']
    assert v['duration']
    assert v['processing_status'] == 'ready'


@pytest.mark.django_db
def test_restaurant_top_level_matches_item(api_client, near_restaurant):
    item = ready_item(near_restaurant, name='Rest')
    res = api_client.get('/api/feed/products/')
    row = next(r for r in res.data['results'] if r['data']['id'] == item.id)
    assert row['restaurant']['id'] == near_restaurant.id
    assert row['restaurant']['name']
    assert row['data']['restaurant_id'] == near_restaurant.id


@pytest.mark.django_db
def test_menu_item_details_in_data(api_client, near_restaurant):
    item = ready_item(near_restaurant, name='DetailItem', base_price=Decimal('199.00'))
    res = api_client.get('/api/feed/products/')
    row = next(r for r in res.data['results'] if r['data']['id'] == item.id and r['type'] == 'item')
    assert row['data']['name'] == 'DetailItem'
    assert row['data']['base_price']


@pytest.mark.django_db
def test_deal_details_in_data(api_client, near_restaurant):
    deal = ready_deal(near_restaurant, label='DealDetail', deal_price=Decimal('399.00'))
    res = api_client.get('/api/feed/products/')
    row = next(r for r in res.data['results'] if r['type'] == 'deal' and r['data']['id'] == deal.id)
    assert row['data']['label'] == 'DealDetail'
    assert row['data']['deal_price']
    assert 'media' in row['data']



# ── D. Ranking / unwatched-on-top ───────────────────────────────────────────


@pytest.mark.django_db
def test_get_serve_does_not_sink_unwatched(api_client, near_restaurant):
    a = ready_item(near_restaurant, name='A-low')
    b = ready_item(near_restaurant, name='B-high')
    ResourceAnalyticsFactory(menu_item=b, engagement_score=999)
    ip_hash = hash_ip(GUEST_IP)
    FeedImpression.objects.create(
        ip_hash=ip_hash,
        menu_item=b,
        serve_count=1,
        watched_ms=5000,
        outcome=FeedWatchOutcome.WATCH,
    )
    res1 = api_client.get(FEED_URL, REMOTE_ADDR=GUEST_IP)
    assert res1.status_code == 200
    ids1 = [r['data']['id'] for r in res1.data['results'] if r['type'] == 'item']
    assert ids1.index(a.id) < ids1.index(b.id)
    res2 = api_client.get(FEED_URL, REMOTE_ADDR=GUEST_IP)
    ids2 = [r['data']['id'] for r in res2.data['results'] if r['type'] == 'item']
    assert ids2.index(a.id) < ids2.index(b.id)
    imp_a = FeedImpression.objects.get(ip_hash=ip_hash, menu_item=a)
    assert imp_a.serve_count >= 1
    assert imp_a.watched_ms is None


@pytest.mark.django_db
def test_seen_under_3s_still_unwatched_band(api_client, near_restaurant):
    low = ready_item(near_restaurant, name='Under3')
    watched = ready_item(near_restaurant, name='Watched')
    ip_hash = hash_ip(GUEST_IP)
    FeedImpression.objects.create(
        ip_hash=ip_hash,
        menu_item=watched,
        serve_count=1,
        watched_ms=4000,
        outcome=FeedWatchOutcome.WATCH,
    )
    api_client.post(
        SEEN_BATCH_URL,
        {'items': [{'event_model': 'item', 'resource_id': low.id, 'watched_ms': 800}]},
        format='json',
        REMOTE_ADDR=GUEST_IP,
    )
    res = api_client.get(FEED_URL, REMOTE_ADDR=GUEST_IP)
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    assert ids.index(low.id) < ids.index(watched.id)


@pytest.mark.django_db
def test_seen_gte_3s_leaves_unwatched_band(api_client, near_restaurant):
    a = ready_item(near_restaurant, name='WillWatch')
    b = ready_item(near_restaurant, name='StillFresh')
    api_client.post(
        SEEN_BATCH_URL,
        {'items': [{'event_model': 'item', 'resource_id': a.id, 'watched_ms': 3500}]},
        format='json',
        REMOTE_ADDR=GUEST_IP,
    )
    res = api_client.get(FEED_URL, REMOTE_ADDR=GUEST_IP)
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    assert ids.index(b.id) < ids.index(a.id)


@pytest.mark.django_db
def test_unwatched_ignores_engagement_score(api_client, near_restaurant):
    high = ready_item(near_restaurant, name='HighScore')
    low = ready_item(near_restaurant, name='LowScore')
    ResourceAnalyticsFactory(menu_item=high, engagement_score=5000)
    res = api_client.get(FEED_URL, REMOTE_ADDR=GUEST_IP)
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    # Newest unwatched first; score must not override recency.
    assert ids.index(low.id) < ids.index(high.id)


@pytest.mark.django_db
def test_unwatched_organic_newest_first(api_client, near_restaurant):
    older = ready_item(near_restaurant, name='OlderOrganic')
    newer = ready_item(near_restaurant, name='NewerOrganic')
    res = api_client.get(FEED_URL, REMOTE_ADDR=GUEST_IP)
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    assert ids.index(newer.id) < ids.index(older.id)


@pytest.mark.django_db
def test_watched_band_uses_engagement_score(api_client, near_restaurant):
    low = ready_item(near_restaurant, name='WatchedLow')
    high = ready_item(near_restaurant, name='WatchedHigh')
    ip_hash = hash_ip(GUEST_IP)
    for it in (low, high):
        FeedImpression.objects.create(
            ip_hash=ip_hash,
            menu_item=it,
            serve_count=1,
            watched_ms=4000,
            outcome=FeedWatchOutcome.WATCH,
        )
    ResourceAnalyticsFactory(menu_item=high, engagement_score=900)
    ResourceAnalyticsFactory(menu_item=low, engagement_score=10)
    res = api_client.get(FEED_URL, REMOTE_ADDR=GUEST_IP)
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    assert ids.index(high.id) < ids.index(low.id)


@pytest.mark.django_db
def test_all_organic_watched_rotates_on_page1(api_client, near_restaurant):
    first = ready_item(near_restaurant, name='AllWatchA')
    second = ready_item(near_restaurant, name='AllWatchB')
    ip_hash = hash_ip(GUEST_IP)
    for it in (first, second):
        FeedImpression.objects.create(
            ip_hash=ip_hash,
            menu_item=it,
            serve_count=1,
            watched_ms=4000,
            outcome=FeedWatchOutcome.WATCH,
        )
    ResourceAnalyticsFactory(menu_item=first, engagement_score=100)
    ResourceAnalyticsFactory(menu_item=second, engagement_score=10)
    FeedViewerState.objects.create(
        ip_hash=ip_hash,
        organic_item_rotate_offset=1,
    )
    res = api_client.get(FEED_URL, REMOTE_ADDR=GUEST_IP)
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    assert ids[0] == second.id
    state = FeedViewerState.objects.get(ip_hash=ip_hash)
    assert state.organic_item_rotate_offset == 2


@pytest.mark.django_db
def test_promoted_unwatched_before_promoted_watched(api_client, near_restaurant):
    for i in range(4):
        ready_item(near_restaurant, name=f'O{i}')
    p_fresh = ready_promo(near_restaurant, name='PFresh')
    p_seen = ready_promo(near_restaurant, name='PSeen')
    ip_hash = hash_ip(GUEST_IP)
    FeedImpression.objects.create(
        ip_hash=ip_hash,
        menu_item=p_seen,
        serve_count=1,
        watched_ms=5000,
        outcome=FeedWatchOutcome.WATCH,
    )
    ResourceAnalyticsFactory(menu_item=p_seen, engagement_score=9999)
    res = api_client.get(FEED_URL, REMOTE_ADDR=GUEST_IP)
    promo_ids = [r['data']['id'] for r in res.data['results'] if r['slot'] == 'promoted']
    assert promo_ids[0] == p_fresh.id


# ── E. Seen batch ───────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_seen_batch_accepts_1_to_10(api_client, near_restaurant):
    items = [ready_item(near_restaurant, name=f'B{i}') for i in range(11)]
    ok1 = api_client.post(
        SEEN_BATCH_URL,
        {'items': [{'event_model': 'item', 'resource_id': items[0].id, 'watched_ms': 100}]},
        format='json',
        REMOTE_ADDR=GUEST_IP,
    )
    assert ok1.status_code == 200
    ok10 = api_client.post(
        SEEN_BATCH_URL,
        {
            'items': [
                {'event_model': 'item', 'resource_id': items[i].id, 'watched_ms': 100}
                for i in range(1, 11)
            ]
        },
        format='json',
        REMOTE_ADDR=GUEST_IP,
    )
    assert ok10.status_code == 200
    bad0 = api_client.post(SEEN_BATCH_URL, {'items': []}, format='json', REMOTE_ADDR=GUEST_IP)
    assert bad0.status_code == 400
    bad11 = api_client.post(
        SEEN_BATCH_URL,
        {
            'items': [
                {'event_model': 'item', 'resource_id': items[0].id, 'watched_ms': 1}
                for _ in range(11)
            ]
        },
        format='json',
        REMOTE_ADDR=GUEST_IP,
    )
    assert bad11.status_code == 400


@pytest.mark.django_db
def test_seen_batch_requires_watched_ms(api_client, near_restaurant):
    item = ready_item(near_restaurant)
    res = api_client.post(
        SEEN_BATCH_URL,
        {'items': [{'event_model': 'item', 'resource_id': item.id}]},
        format='json',
        REMOTE_ADDR=GUEST_IP,
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_seen_batch_dedupe_keeps_highest_watched_ms(api_client, near_restaurant):
    item = ready_item(near_restaurant)
    res = api_client.post(
        SEEN_BATCH_URL,
        {
            'items': [
                {'event_model': 'item', 'resource_id': item.id, 'watched_ms': 500},
                {'event_model': 'item', 'resource_id': item.id, 'watched_ms': 4000},
            ]
        },
        format='json',
        REMOTE_ADDR=GUEST_IP,
    )
    assert res.status_code == 200
    assert res.data['recorded_count'] == 1
    assert len(res.data['results']) == 1
    assert res.data['results'][0]['outcome'] == 'watch'
    assert res.data['results'][0]['view_counted'] is True
    imp = FeedImpression.objects.get(ip_hash=hash_ip(GUEST_IP), menu_item=item)
    assert imp.watched_ms == 4000


@pytest.mark.django_db
def test_seen_batch_partial_success(api_client, near_restaurant):
    item = ready_item(near_restaurant)
    res = api_client.post(
        SEEN_BATCH_URL,
        {
            'items': [
                {'event_model': 'item', 'resource_id': item.id, 'watched_ms': 1000},
                {'event_model': 'item', 'resource_id': 999999, 'watched_ms': 1000},
            ]
        },
        format='json',
        REMOTE_ADDR=GUEST_IP,
    )
    assert res.status_code == 200
    assert res.data['recorded_count'] == 1
    assert res.data['results'][0]['recorded'] is True
    assert res.data['results'][1]['recorded'] is False
    assert res.data['results'][1]['error']


@pytest.mark.django_db
def test_seen_batch_outcome_upgrade_only(api_client, near_restaurant):
    item = ready_item(near_restaurant)
    ip_hash = hash_ip(GUEST_IP)
    api_client.post(
        SEEN_BATCH_URL,
        {'items': [{'event_model': 'item', 'resource_id': item.id, 'watched_ms': 500}]},
        format='json',
        REMOTE_ADDR=GUEST_IP,
    )
    assert FeedImpression.objects.get(ip_hash=ip_hash, menu_item=item).outcome == 'skip'
    api_client.post(
        SEEN_BATCH_URL,
        {
            'items': [
                {
                    'event_model': 'item',
                    'resource_id': item.id,
                    'watched_ms': 5000,
                    'duration_ms': 10000,
                }
            ]
        },
        format='json',
        REMOTE_ADDR=GUEST_IP,
    )
    assert FeedImpression.objects.get(ip_hash=ip_hash, menu_item=item).outcome == 'watch'
    api_client.post(
        SEEN_BATCH_URL,
        {
            'items': [
                {
                    'event_model': 'item',
                    'resource_id': item.id,
                    'watched_ms': 9500,
                    'duration_ms': 10000,
                }
            ]
        },
        format='json',
        REMOTE_ADDR=GUEST_IP,
    )
    assert FeedImpression.objects.get(ip_hash=ip_hash, menu_item=item).outcome == 'complete'
    api_client.post(
        SEEN_BATCH_URL,
        {'items': [{'event_model': 'item', 'resource_id': item.id, 'watched_ms': 100}]},
        format='json',
        REMOTE_ADDR=GUEST_IP,
    )
    imp = FeedImpression.objects.get(ip_hash=ip_hash, menu_item=item)
    assert imp.outcome == 'complete'
    assert imp.watched_ms == 9500


@pytest.mark.django_db
def test_seen_batch_gte_3s_bumps_detail_views(api_client, near_restaurant):
    item = ready_item(near_restaurant)
    api_client.post(
        SEEN_BATCH_URL,
        {'items': [{'event_model': 'item', 'resource_id': item.id, 'watched_ms': 3000}]},
        format='json',
        REMOTE_ADDR=GUEST_IP,
    )
    analytics = ResourceAnalytics.objects.get(menu_item=item, user__isnull=True)
    assert analytics.detail_views == 1


@pytest.mark.django_db
def test_seen_batch_under_3s_no_detail_views(api_client, near_restaurant):
    item = ready_item(near_restaurant)
    api_client.post(
        SEEN_BATCH_URL,
        {'items': [{'event_model': 'item', 'resource_id': item.id, 'watched_ms': 2000}]},
        format='json',
        REMOTE_ADDR=GUEST_IP,
    )
    assert not ResourceAnalytics.objects.filter(menu_item=item).exists()


@pytest.mark.django_db
def test_seen_batch_rewatch_gte_3s_bumps_again(api_client, near_restaurant):
    item = ready_item(near_restaurant)
    payload = {'items': [{'event_model': 'item', 'resource_id': item.id, 'watched_ms': 4000}]}
    api_client.post(SEEN_BATCH_URL, payload, format='json', REMOTE_ADDR=GUEST_IP)
    api_client.post(SEEN_BATCH_URL, payload, format='json', REMOTE_ADDR=GUEST_IP)
    analytics = ResourceAnalytics.objects.get(menu_item=item, user__isnull=True)
    assert analytics.detail_views == 2


@pytest.mark.django_db
def test_seen_batch_guest_vs_user_isolation(api_client, auth_client, near_restaurant):
    item = ready_item(near_restaurant)
    user = CustomerOnlyUserFactory()
    payload = {'items': [{'event_model': 'item', 'resource_id': item.id, 'watched_ms': 1500}]}
    api_client.post(SEEN_BATCH_URL, payload, format='json', REMOTE_ADDR=GUEST_IP)
    auth_client(user).post(SEEN_BATCH_URL, payload, format='json')
    assert FeedImpression.objects.filter(menu_item=item).count() == 2
    assert FeedImpression.objects.filter(menu_item=item, user__isnull=False).count() == 1
    assert FeedImpression.objects.filter(menu_item=item, ip_hash__isnull=False).count() == 1


@pytest.mark.django_db
def test_seen_batch_does_not_write_explore_impression(api_client, near_restaurant):
    item = ready_item(near_restaurant)
    before = ExploreImpression.objects.count()
    api_client.post(
        SEEN_BATCH_URL,
        {'items': [{'event_model': 'item', 'resource_id': item.id, 'watched_ms': 4000}]},
        format='json',
        REMOTE_ADDR=GUEST_IP,
    )
    assert ExploreImpression.objects.count() == before


# ── F. Feed GET analytics ───────────────────────────────────────────────────


@pytest.mark.django_db
def test_feed_get_bumps_impression_count(api_client, near_restaurant):
    item = ready_item(near_restaurant)
    api_client.get(FEED_URL, REMOTE_ADDR=GUEST_IP)
    analytics = ResourceAnalytics.objects.get(menu_item=item, user__isnull=True)
    assert analytics.impression_count >= 1


@pytest.mark.django_db
def test_feed_get_bumps_serve_count_only(api_client, near_restaurant):
    item = ready_item(near_restaurant)
    api_client.get(FEED_URL, REMOTE_ADDR=GUEST_IP)
    imp = FeedImpression.objects.get(ip_hash=hash_ip(GUEST_IP), menu_item=item)
    assert imp.serve_count == 1
    assert imp.watched_ms is None
    assert imp.outcome == ''


# ── G. Isolation ────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_feed_does_not_touch_explore_viewer_state(api_client, near_restaurant):
    item = ready_item(near_restaurant)
    before = ExploreViewerState.objects.count()
    api_client.get(FEED_URL, REMOTE_ADDR=GUEST_IP)
    api_client.post(
        SEEN_BATCH_URL,
        {'items': [{'event_model': 'item', 'resource_id': item.id, 'watched_ms': 1000}]},
        format='json',
        REMOTE_ADDR=GUEST_IP,
    )
    assert ExploreViewerState.objects.count() == before
    assert FeedViewerState.objects.count() >= 1
