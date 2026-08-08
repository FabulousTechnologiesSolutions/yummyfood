from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.discovery.models import ExploreImpression, ExploreViewerState
from apps.restaurants.models import MenuItemStatus
from tests.accounts.factories import RestaurantFactory
from tests.discovery.factories import DealFactory, MenuItemFactory, ResourceAnalyticsFactory


def _place(restaurant, lat, lng, city_id=1):
    restaurant.lat = Decimal(str(lat))
    restaurant.lng = Decimal(str(lng))
    restaurant.city_id = city_id
    restaurant.is_paused = False
    restaurant.is_permanently_closed = False
    restaurant.save()
    return restaurant


@pytest.fixture
def near_restaurant():
    r = RestaurantFactory()
    return _place(r, 31.5200, 74.3500, city_id=10)


@pytest.fixture
def far_restaurant():
    r = RestaurantFactory()
    # ~60km away roughly
    return _place(r, 32.1000, 74.3500, city_id=10)


@pytest.mark.django_db
def test_explore_global_returns_results(api_client, near_restaurant):
    MenuItemFactory(restaurant=near_restaurant)
    DealFactory(restaurant=near_restaurant)
    res = api_client.get('/api/explore/products/')
    assert res.status_code == 200
    assert 'results' in res.data
    assert res.data['page'] == 1
    assert 'next_page' in res.data
    assert res.data['applied_radius_km'] is None


@pytest.mark.django_db
def test_explore_block_promoted_plus_organic(api_client, near_restaurant):
    now = timezone.now()
    promo = MenuItemFactory(
        restaurant=near_restaurant,
        is_promoted=True,
        promoted_starts_at=now - timedelta(hours=1),
        promoted_ends_at=now + timedelta(days=1),
    )
    MenuItemFactory(restaurant=near_restaurant)
    MenuItemFactory(restaurant=near_restaurant)
    DealFactory(restaurant=near_restaurant)
    res = api_client.get('/api/explore/products/?page_size=4')
    assert res.status_code == 200
    results = res.data['results']
    assert len(results) >= 1
    assert results[0]['slot'] == 'promoted'
    assert results[0]['data']['id'] == promo.id


@pytest.mark.django_db
def test_no_promoted_all_organic(api_client, near_restaurant):
    for _ in range(4):
        MenuItemFactory(restaurant=near_restaurant)
    DealFactory(restaurant=near_restaurant)
    res = api_client.get('/api/explore/products/?page_size=4')
    assert all(r['slot'] == 'organic' for r in res.data['results'])


@pytest.mark.django_db
def test_geo_hard_radius_excludes_far(api_client, near_restaurant, far_restaurant):
    near_item = MenuItemFactory(restaurant=near_restaurant, name='Near')
    far_item = MenuItemFactory(restaurant=far_restaurant, name='Far')
    res = api_client.get(
        '/api/explore/products/',
        {'lat': '31.52', 'lng': '74.35', 'distance_km': '5'},
    )
    assert res.status_code == 200
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    assert near_item.id in ids
    assert far_item.id not in ids
    assert res.data['applied_radius_km'] == 5.0


@pytest.mark.django_db
def test_geo_default_50km(api_client, near_restaurant, far_restaurant):
    MenuItemFactory(restaurant=near_restaurant)
    MenuItemFactory(restaurant=far_restaurant)
    res = api_client.get('/api/explore/products/', {'lat': '31.52', 'lng': '74.35'})
    assert res.status_code == 200
    assert res.data['applied_radius_km'] == 50.0


@pytest.mark.django_db
def test_lat_only_invalid(api_client):
    res = api_client.get('/api/explore/products/', {'lat': '31.52'})
    assert res.status_code == 400
    assert res.data['error']['code'] == 'INVALID_COORDINATES'


@pytest.mark.django_db
def test_distance_without_lat_invalid(api_client):
    res = api_client.get('/api/explore/products/', {'distance_km': '5'})
    assert res.status_code == 400
    assert res.data['error']['code'] == 'DISTANCE_REQUIRES_LOCATION'


@pytest.mark.django_db
def test_invalid_distance_km(api_client):
    res = api_client.get(
        '/api/explore/products/',
        {'lat': '31.52', 'lng': '74.35', 'distance_km': '2'},
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_city_filter(api_client, near_restaurant):
    other = RestaurantFactory()
    _place(other, 31.52, 74.35, city_id=99)
    a = MenuItemFactory(restaurant=near_restaurant)
    b = MenuItemFactory(restaurant=other)
    res = api_client.get('/api/explore/products/', {'city_id': '10'})
    assert res.status_code == 200
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    assert a.id in ids
    assert b.id not in ids
    assert res.data['city_id'] == 10
    assert all(r.get('distance_km') is None for r in res.data['results'])


@pytest.mark.django_db
def test_paused_excluded(api_client, near_restaurant):
    near_restaurant.is_paused = True
    near_restaurant.save()
    MenuItemFactory(restaurant=near_restaurant)
    res = api_client.get('/api/explore/products/')
    assert res.data['results'] == []


@pytest.mark.django_db
def test_draft_excluded(api_client, near_restaurant):
    MenuItemFactory(restaurant=near_restaurant, status=MenuItemStatus.DRAFT)
    res = api_client.get('/api/explore/products/')
    assert res.data['results'] == []


@pytest.mark.django_db
def test_pagination_next_page(api_client, near_restaurant):
    for _ in range(6):
        MenuItemFactory(restaurant=near_restaurant)
    res = api_client.get('/api/explore/products/?page_size=4')
    assert res.data['has_more'] is True
    assert res.data['next_page'] == 2
    page2 = api_client.get('/api/explore/products/?page_size=4&page=2')
    assert page2.status_code == 200


@pytest.mark.django_db
def test_unread_promoted_leads_before_seen(api_client, near_restaurant):
    """Unseen promoted stay on top; next page=1 leads with remaining unread promo."""
    now = timezone.now()
    p1 = MenuItemFactory(
        restaurant=near_restaurant,
        is_promoted=True,
        promoted_starts_at=now - timedelta(hours=1),
        promoted_ends_at=now + timedelta(days=1),
        name='P1',
    )
    p2 = MenuItemFactory(
        restaurant=near_restaurant,
        is_promoted=True,
        promoted_starts_at=now - timedelta(hours=1),
        promoted_ends_at=now + timedelta(days=1),
        name='P2',
    )
    assert p1.id < p2.id
    DealFactory(restaurant=near_restaurant)
    MenuItemFactory(restaurant=near_restaurant)
    MenuItemFactory(restaurant=near_restaurant)

    first = api_client.get('/api/explore/products/?page_size=4', REMOTE_ADDR='1.2.3.4')
    assert first.data['results'][0]['slot'] == 'promoted'
    assert first.data['results'][0]['data']['id'] == p1.id
    second = api_client.get('/api/explore/products/?page_size=4', REMOTE_ADDR='1.2.3.4')
    assert second.data['results'][0]['slot'] == 'promoted'
    assert second.data['results'][0]['data']['id'] == p2.id
    assert ExploreViewerState.objects.filter(ip_hash__isnull=False).exists()
    assert ExploreImpression.objects.exists()


@pytest.mark.django_db
def test_promoted_rotate_only_after_all_seen(api_client, near_restaurant):
    now = timezone.now()
    p1 = MenuItemFactory(
        restaurant=near_restaurant,
        is_promoted=True,
        promoted_starts_at=now - timedelta(hours=1),
        promoted_ends_at=now + timedelta(days=1),
        name='P1',
    )
    p2 = MenuItemFactory(
        restaurant=near_restaurant,
        is_promoted=True,
        promoted_starts_at=now - timedelta(hours=1),
        promoted_ends_at=now + timedelta(days=1),
        name='P2',
    )
    assert p1.id < p2.id
    # Enough organic so page_size=4 is 1 promoted + 3 organic (p2 not served same page).
    DealFactory(restaurant=near_restaurant)
    MenuItemFactory(restaurant=near_restaurant)
    MenuItemFactory(restaurant=near_restaurant)

    # Exhaust unread: p1 then p2
    r1 = api_client.get('/api/explore/products/?page_size=4', REMOTE_ADDR='1.2.3.5')
    assert r1.data['results'][0]['data']['id'] == p1.id
    assert p2.id not in [r['data']['id'] for r in r1.data['results'] if r['type'] == 'item']
    r2 = api_client.get('/api/explore/products/?page_size=4', REMOTE_ADDR='1.2.3.5')
    assert r2.data['results'][0]['data']['id'] == p2.id
    # All seen → rotate starts; first all-seen open still leads with p1 (offset 0)
    third = api_client.get('/api/explore/products/?page_size=4', REMOTE_ADDR='1.2.3.5')
    assert third.data['results'][0]['data']['id'] == p1.id
    # Next page=1 advances rotate → p2
    fourth = api_client.get('/api/explore/products/?page_size=4', REMOTE_ADDR='1.2.3.5')
    assert fourth.data['results'][0]['data']['id'] == p2.id


@pytest.mark.django_db
def test_only_deals_fills_organic(api_client, near_restaurant):
    for _ in range(4):
        DealFactory(restaurant=near_restaurant)
    res = api_client.get('/api/explore/products/?page_size=4')
    assert len(res.data['results']) == 4
    assert all(r['type'] == 'deal' for r in res.data['results'])


@pytest.mark.django_db
def test_missing_coords_excluded_in_distance_mode(api_client, near_restaurant):
    near_restaurant.lat = None
    near_restaurant.lng = None
    near_restaurant.save()
    MenuItemFactory(restaurant=near_restaurant)
    res = api_client.get('/api/explore/products/', {'lat': '31.52', 'lng': '74.35'})
    assert res.data['results'] == []


@pytest.mark.django_db
def test_unread_float_to_top_after_viewing_batches(api_client, near_restaurant):
    """
    50 organic items, page_size=20 (page=1 each batch):
    - batch1: 20 unread served → remain unread = 30 on next open
    - batch2: next 20 unread; viewed 40 sit below
    - batch3: last 10 unread stay on top (plus fillers from seen)
    """
    items = [
        MenuItemFactory(restaurant=near_restaurant, name=f'Item {i:02d}')
        for i in range(50)
    ]
    assert len(items) == 50
    # stable id order for first batch expectations
    items_by_id = sorted(items, key=lambda x: x.id)

    # Batch 1
    r1 = api_client.get(
        '/api/explore/products/',
        {'page': '1', 'page_size': '20'},
        REMOTE_ADDR='10.0.0.50',
    )
    assert r1.status_code == 200
    assert len(r1.data['results']) == 20
    batch1_ids = [row['data']['id'] for row in r1.data['results']]
    assert len(set(batch1_ids)) == 20
    assert all(row['type'] == 'item' for row in r1.data['results'])

    # Batch 2 — unread (30) must occupy the top of the composed feed
    r2 = api_client.get(
        '/api/explore/products/',
        {'page': '1', 'page_size': '20'},
        REMOTE_ADDR='10.0.0.50',
    )
    batch2_ids = [row['data']['id'] for row in r2.data['results']]
    assert len(batch2_ids) == 20
    assert set(batch2_ids).isdisjoint(set(batch1_ids)), (
        'Already-viewed items must not appear until unread are exhausted'
    )

    # Batch 3 — only 10 unread left; those 10 must lead the response
    r3 = api_client.get(
        '/api/explore/products/',
        {'page': '1', 'page_size': '20'},
        REMOTE_ADDR='10.0.0.50',
    )
    batch3_ids = [row['data']['id'] for row in r3.data['results']]
    asserted_all = set(batch1_ids) | set(batch2_ids) | set(batch3_ids)
    assert asserted_all == {i.id for i in items_by_id}

    remaining_before_batch3 = {i.id for i in items_by_id} - set(batch1_ids) - set(batch2_ids)
    assert len(remaining_before_batch3) == 10
    assert set(batch3_ids[:10]) == remaining_before_batch3, (
        'The last 10 unread must lead the page before any already-viewed fillers'
    )


@pytest.mark.django_db
def test_all_seen_sorted_by_highest_engagement_score(api_client, near_restaurant):
    """Once every item has been served, highest global engagement_score leads."""
    from apps.discovery.services.viewer import hash_ip

    items = [
        MenuItemFactory(restaurant=near_restaurant, name=f'Seen {i}')
        for i in range(5)
    ]
    ip = '10.0.0.77'
    ip_hash = hash_ip(ip)
    # Higher serve_count on low-score item must not beat higher engagement_score
    counts = {items[0].id: 50, items[1].id: 5, items[2].id: 3, items[3].id: 1, items[4].id: 2}
    scores = {items[0].id: 1.0, items[1].id: 8.0, items[2].id: 5.0, items[3].id: 20.0, items[4].id: 3.0}
    for item in items:
        ExploreImpression.objects.create(
            user=None,
            ip_hash=ip_hash,
            menu_item=item,
            deal=None,
            serve_count=counts[item.id],
        )
        ResourceAnalyticsFactory(
            menu_item=item,
            deal=None,
            user=None,
            engagement_score=scores[item.id],
        )

    res = api_client.get(
        '/api/explore/products/',
        {'page': '1', 'page_size': '5'},
        REMOTE_ADDR=ip,
    )
    assert res.status_code == 200
    ids = [row['data']['id'] for row in res.data['results'] if row['type'] == 'item']
    assert ids[0] == items[3].id  # score 20
    assert ids[1] == items[1].id  # score 8
    assert ids[2] == items[2].id  # score 5


@pytest.mark.django_db
def test_price_min_max_filter(api_client, near_restaurant):
    cheap = MenuItemFactory(restaurant=near_restaurant, base_price=Decimal('100.00'), name='Cheap')
    mid = MenuItemFactory(restaurant=near_restaurant, base_price=Decimal('750.00'), name='Mid')
    pricey = MenuItemFactory(restaurant=near_restaurant, base_price=Decimal('1500.00'), name='Pricey')
    DealFactory(restaurant=near_restaurant, deal_price=Decimal('800.00'), label='MidDeal')

    res = api_client.get(
        '/api/explore/products/',
        {'min_price': '500', 'max_price': '1000'},
    )
    assert res.status_code == 200
    ids = {(r['type'], r['data']['id']) for r in res.data['results']}
    assert ('item', mid.id) in ids
    assert ('item', cheap.id) not in ids
    assert ('item', pricey.id) not in ids
    assert res.data['min_price'] == 500.0
    assert res.data['max_price'] == 1000.0


@pytest.mark.django_db
def test_price_min_only(api_client, near_restaurant):
    MenuItemFactory(restaurant=near_restaurant, base_price=Decimal('100.00'))
    keep = MenuItemFactory(restaurant=near_restaurant, base_price=Decimal('600.00'))
    res = api_client.get('/api/explore/products/', {'min_price': '500'})
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    assert keep.id in ids
    assert all(
        Decimal(r['data']['base_price']) >= Decimal('500')
        for r in res.data['results']
        if r['type'] == 'item'
    )


@pytest.mark.django_db
def test_invalid_price_range(api_client):
    res = api_client.get('/api/explore/products/', {'min_price': '1000', 'max_price': '100'})
    assert res.status_code == 400
    assert res.data['error']['code'] == 'INVALID_PRICE_RANGE'


@pytest.mark.django_db
def test_category_filter_items(api_client, near_restaurant):
    from apps.restaurants.models import MenuCategory

    burgers = MenuCategory.objects.filter(slug='burgers').first() or MenuCategory.objects.create(
        slug='burgers-test',
        name='Burgers',
    )
    pizza = MenuCategory.objects.filter(slug='pizza').first() or MenuCategory.objects.create(
        slug='pizza-test',
        name='Pizza',
    )
    burger_item = MenuItemFactory(restaurant=near_restaurant, name='Burger')
    burger_item.categories.add(burgers)
    pizza_item = MenuItemFactory(restaurant=near_restaurant, name='Pizza')
    pizza_item.categories.add(pizza)

    res = api_client.get('/api/explore/products/', {'category_ids': str(burgers.id)})
    assert res.status_code == 200
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    assert burger_item.id in ids
    assert pizza_item.id not in ids
    assert res.data['category_ids'] == [burgers.id]


@pytest.mark.django_db
def test_category_filter_deal_via_line_item(api_client, near_restaurant):
    from apps.restaurants.models import DealLine, MenuCategory

    burgers = MenuCategory.objects.filter(slug='burgers').first() or MenuCategory.objects.create(
        slug='burgers-deal',
        name='Burgers',
    )
    item = MenuItemFactory(restaurant=near_restaurant)
    item.categories.add(burgers)
    deal = DealFactory(restaurant=near_restaurant)
    DealLine.objects.create(
        deal=deal,
        menu_item=item,
        size_label='Regular',
        unit_price=Decimal('100.00'),
        quantity=1,
    )
    other_deal = DealFactory(restaurant=near_restaurant, label='NoCats')

    res = api_client.get('/api/explore/products/', {'category_ids': [burgers.id]})
    assert res.status_code == 200
    deal_ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'deal']
    assert deal.id in deal_ids
    assert other_deal.id not in deal_ids


@pytest.mark.django_db
def test_promoted_not_duplicated_as_organic(api_client, near_restaurant):
    now = timezone.now()
    promo = MenuItemFactory(
        restaurant=near_restaurant,
        is_promoted=True,
        promoted_starts_at=now - timedelta(hours=1),
        promoted_ends_at=now + timedelta(days=1),
        name='PromoOnly',
    )
    MenuItemFactory(restaurant=near_restaurant)
    MenuItemFactory(restaurant=near_restaurant)
    DealFactory(restaurant=near_restaurant)

    res = api_client.get('/api/explore/products/?page_size=4')
    assert res.status_code == 200
    matches = [
        r
        for r in res.data['results']
        if r['type'] == 'item' and r['data']['id'] == promo.id
    ]
    assert matches
    assert all(m['slot'] == 'promoted' for m in matches)
    assert not any(m['slot'] == 'organic' for m in matches)


@pytest.mark.django_db
def test_stale_promo_window_excluded_from_promoted(api_client, near_restaurant):
    now = timezone.now()
    future = MenuItemFactory(
        restaurant=near_restaurant,
        name='FuturePromo',
        is_promoted=True,
        promoted_starts_at=now + timedelta(days=1),
        promoted_ends_at=now + timedelta(days=3),
    )
    past = MenuItemFactory(
        restaurant=near_restaurant,
        name='PastPromo',
        is_promoted=True,
        promoted_starts_at=now - timedelta(days=5),
        promoted_ends_at=now - timedelta(hours=1),
    )
    organic = MenuItemFactory(restaurant=near_restaurant, name='Organic')
    DealFactory(restaurant=near_restaurant)

    res = api_client.get('/api/explore/products/?page_size=8')
    assert res.status_code == 200
    promoted_ids = [
        r['data']['id'] for r in res.data['results'] if r['slot'] == 'promoted'
    ]
    assert future.id not in promoted_ids
    assert past.id not in promoted_ids
    all_ids = [r['data']['id'] for r in res.data['results']]
    assert organic.id in all_ids
    # Stale flagged items still eligible as organic when currently not promoted.
    assert future.id in all_ids
    assert past.id in all_ids
    assert all(r['slot'] == 'organic' for r in res.data['results'] if r['data']['id'] in (future.id, past.id))


@pytest.mark.django_db
def test_mixed_unread_items_and_deals_next_page1(api_client, near_restaurant):
    items = [
        MenuItemFactory(restaurant=near_restaurant, name=f'MixItem{i}')
        for i in range(4)
    ]
    deals = [
        DealFactory(restaurant=near_restaurant, label=f'MixDeal{i}')
        for i in range(2)
    ]

    first = api_client.get(
        '/api/explore/products/',
        {'page': '1', 'page_size': '4'},
        REMOTE_ADDR='10.20.0.1',
    )
    assert first.status_code == 200
    assert len(first.data['results']) == 4
    served = {(r['type'], r['data']['id']) for r in first.data['results']}
    # Organic-only O-D-O-O: at least one deal and items on first block
    assert any(t == 'item' for t, _ in served)
    assert any(t == 'deal' for t, _ in served)

    all_keys = {('item', i.id) for i in items} | {('deal', d.id) for d in deals}
    remaining = all_keys - served
    assert remaining  # some unread left
    assert any(t == 'item' for t, _ in remaining)
    assert any(t == 'deal' for t, _ in remaining)

    second = api_client.get(
        '/api/explore/products/',
        {'page': '1', 'page_size': '4'},
        REMOTE_ADDR='10.20.0.1',
    )
    assert second.status_code == 200
    second_keys = [(r['type'], r['data']['id']) for r in second.data['results']]
    # Remaining unread of both types are served again and appear in this page
    assert remaining.issubset(set(second_keys))
    types = [t for t, _ in second_keys]
    assert types.count('item') >= 1
    assert types.count('deal') >= 1
    unread_positions = [
        i for i, key in enumerate(second_keys) if key in remaining
    ]
    assert min(unread_positions) == 0  # an unread leads


@pytest.mark.django_db
def test_city_plus_distance_excludes_nearer_other_city(
    api_client, near_restaurant
):
    # near_restaurant is city 10 at 31.52, 74.35
    nearer_other_city = RestaurantFactory()
    _place(nearer_other_city, 31.5201, 74.3501, city_id=99)
    other_item = MenuItemFactory(restaurant=nearer_other_city, name='WrongCityNear')
    same_city_item = MenuItemFactory(restaurant=near_restaurant, name='RightCity')

    res = api_client.get(
        '/api/explore/products/',
        {
            'lat': '31.52',
            'lng': '74.35',
            'distance_km': '5',
            'city_id': '10',
        },
    )
    assert res.status_code == 200
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    assert same_city_item.id in ids
    assert other_item.id not in ids
    assert res.data['city_id'] == 10
    assert res.data['applied_radius_km'] == 5.0


@pytest.mark.django_db
def test_radius_boundary_exactly_distance_km_included(api_client):
    # Lat/lng are Decimal(6dp). 74.402748 ≈ 4.9999 km east of 74.35 — within <= 5.
    boundary = RestaurantFactory()
    _place(boundary, 31.52, 74.402748, city_id=10)
    item = MenuItemFactory(restaurant=boundary, name='Boundary')

    beyond = RestaurantFactory()
    _place(beyond, 31.52, 74.403804, city_id=10)  # ~5.1 km
    beyond_item = MenuItemFactory(restaurant=beyond, name='Beyond')

    res = api_client.get(
        '/api/explore/products/',
        {'lat': '31.52', 'lng': '74.35', 'distance_km': '5'},
    )
    assert res.status_code == 200
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    assert item.id in ids
    assert beyond_item.id not in ids
    boundary_row = next(r for r in res.data['results'] if r['data']['id'] == item.id)
    assert boundary_row['distance_km'] is not None
    assert boundary_row['distance_km'] <= 5.0


@pytest.mark.django_db
def test_permanently_closed_excluded(api_client, near_restaurant):
    near_restaurant.is_permanently_closed = True
    near_restaurant.save()
    MenuItemFactory(restaurant=near_restaurant)
    DealFactory(restaurant=near_restaurant)
    res = api_client.get('/api/explore/products/')
    assert res.status_code == 200
    assert res.data['results'] == []


@pytest.mark.django_db
def test_pagination_past_end_empty(api_client, near_restaurant):
    for _ in range(3):
        MenuItemFactory(restaurant=near_restaurant)
    first = api_client.get('/api/explore/products/?page_size=4')
    assert first.status_code == 200
    assert first.data['has_more'] is False
    assert first.data['next_page'] is None

    past = api_client.get('/api/explore/products/?page_size=4&page=2')
    assert past.status_code == 200
    assert past.data['results'] == []
    assert past.data['has_more'] is False
    assert past.data['next_page'] is None


@pytest.mark.django_db
def test_auth_vs_guest_impression_isolation(
    api_client, auth_client, customer_user, near_restaurant
):
    items = [
        MenuItemFactory(restaurant=near_restaurant, name=f'Iso{i}')
        for i in range(6)
    ]
    sorted_ids = [i.id for i in sorted(items, key=lambda x: x.id)]

    guest = api_client.get(
        '/api/explore/products/',
        {'page': '1', 'page_size': '4'},
        REMOTE_ADDR='198.51.100.10',
    )
    assert guest.status_code == 200
    guest_ids = [r['data']['id'] for r in guest.data['results']]
    assert len(guest_ids) == 4

    client = auth_client(customer_user)
    authed = client.get(
        '/api/explore/products/',
        {'page': '1', 'page_size': '4'},
        REMOTE_ADDR='198.51.100.10',  # same IP must not pollute user feed
    )
    assert authed.status_code == 200
    # User still sees unread-first in stable id order (guest views ignored)
    assert [r['data']['id'] for r in authed.data['results']] == sorted_ids[:4]

    # Reverse: user views should not change a different guest's unread order
    other_guest = api_client.get(
        '/api/explore/products/',
        {'page': '1', 'page_size': '4'},
        REMOTE_ADDR='203.0.113.50',
    )
    assert [r['data']['id'] for r in other_guest.data['results']] == sorted_ids[:4]


@pytest.mark.django_db
def test_organic_unread_ignores_engagement_score(api_client, near_restaurant):
    """Unread band is stable by id — high engagement must not float past lower id."""
    low = MenuItemFactory(restaurant=near_restaurant, name='LowScoreFirst')
    high = MenuItemFactory(restaurant=near_restaurant, name='HighScoreSecond')
    assert low.id < high.id
    ResourceAnalyticsFactory(menu_item=high, deal=None, user=None, engagement_score=999.0)
    ResourceAnalyticsFactory(menu_item=low, deal=None, user=None, engagement_score=0.1)

    res = api_client.get(
        '/api/explore/products/',
        {'page': '1', 'page_size': '2'},
        REMOTE_ADDR='10.10.0.1',
    )
    assert res.status_code == 200
    ids = [r['data']['id'] for r in res.data['results'] if r['type'] == 'item']
    assert ids[:2] == [low.id, high.id]


@pytest.mark.django_db
def test_promoted_unread_leads_then_seen_by_score(api_client, near_restaurant):
    now = timezone.now()
    unread = MenuItemFactory(
        restaurant=near_restaurant,
        name='PromoUnread',
        is_promoted=True,
        promoted_starts_at=now - timedelta(hours=1),
        promoted_ends_at=now + timedelta(days=1),
    )
    seen_low = MenuItemFactory(
        restaurant=near_restaurant,
        name='PromoSeenLow',
        is_promoted=True,
        promoted_starts_at=now - timedelta(hours=1),
        promoted_ends_at=now + timedelta(days=1),
    )
    seen_high = MenuItemFactory(
        restaurant=near_restaurant,
        name='PromoSeenHigh',
        is_promoted=True,
        promoted_starts_at=now - timedelta(hours=1),
        promoted_ends_at=now + timedelta(days=1),
    )
    from apps.discovery.services.viewer import hash_ip

    ip = '10.10.0.2'
    ip_hash = hash_ip(ip)
    for item, score in ((seen_low, 2.0), (seen_high, 50.0)):
        ExploreImpression.objects.create(
            user=None,
            ip_hash=ip_hash,
            menu_item=item,
            deal=None,
            serve_count=1,
        )
        ResourceAnalyticsFactory(
            menu_item=item, deal=None, user=None, engagement_score=score
        )
    # Filler so first page is 1 promo + 3 organic
    DealFactory(restaurant=near_restaurant)
    MenuItemFactory(restaurant=near_restaurant)
    MenuItemFactory(restaurant=near_restaurant)

    res = api_client.get('/api/explore/products/?page_size=4', REMOTE_ADDR=ip)
    assert res.status_code == 200
    assert res.data['results'][0]['slot'] == 'promoted'
    assert res.data['results'][0]['data']['id'] == unread.id

    # After unread is served, next page=1 leads with highest-score seen promo
    res2 = api_client.get('/api/explore/products/?page_size=4', REMOTE_ADDR=ip)
    assert res2.data['results'][0]['slot'] == 'promoted'
    assert res2.data['results'][0]['data']['id'] == seen_high.id


@pytest.mark.django_db
def test_promoted_cycles_podO_pattern(api_client, near_restaurant):
    """2 promos cycle: P1,O,D,O,P2,O,D,O,P1,…"""
    now = timezone.now()
    p1 = MenuItemFactory(
        restaurant=near_restaurant,
        name='CycleP1',
        is_promoted=True,
        promoted_starts_at=now - timedelta(hours=1),
        promoted_ends_at=now + timedelta(days=1),
    )
    p2 = MenuItemFactory(
        restaurant=near_restaurant,
        name='CycleP2',
        is_promoted=True,
        promoted_starts_at=now - timedelta(hours=1),
        promoted_ends_at=now + timedelta(days=1),
    )
    assert p1.id < p2.id
    for i in range(6):
        MenuItemFactory(restaurant=near_restaurant, name=f'OrgI{i}')
    for i in range(3):
        DealFactory(restaurant=near_restaurant, label=f'OrgD{i}')

    res = api_client.get(
        '/api/explore/products/',
        {'page': '1', 'page_size': '12'},
        REMOTE_ADDR='10.0.0.80',
    )
    assert res.status_code == 200
    rows = res.data['results']
    assert len(rows) >= 12
    # P O D O × 3
    assert rows[0]['slot'] == 'promoted' and rows[0]['data']['id'] == p1.id
    assert rows[1]['type'] == 'item' and rows[1]['slot'] == 'organic'
    assert rows[2]['type'] == 'deal' and rows[2]['slot'] == 'organic'
    assert rows[3]['type'] == 'item' and rows[3]['slot'] == 'organic'
    assert rows[4]['slot'] == 'promoted' and rows[4]['data']['id'] == p2.id
    assert rows[8]['slot'] == 'promoted' and rows[8]['data']['id'] == p1.id  # cycle


@pytest.mark.django_db
def test_promoted_repeat_bumps_impression(api_client, near_restaurant):
    now = timezone.now()
    promo = MenuItemFactory(
        restaurant=near_restaurant,
        name='RepeatPromo',
        is_promoted=True,
        promoted_starts_at=now - timedelta(hours=1),
        promoted_ends_at=now + timedelta(days=1),
    )
    for i in range(4):
        MenuItemFactory(restaurant=near_restaurant, name=f'RI{i}')
    for i in range(2):
        DealFactory(restaurant=near_restaurant, label=f'RD{i}')

    res = api_client.get(
        '/api/explore/products/',
        {'page': '1', 'page_size': '8'},
        REMOTE_ADDR='10.0.0.81',
    )
    assert res.status_code == 200
    promo_slots = [
        r for r in res.data['results'] if r['slot'] == 'promoted' and r['data']['id'] == promo.id
    ]
    assert len(promo_slots) >= 2
    from apps.discovery.services.viewer import hash_ip

    imp = ExploreImpression.objects.get(
        ip_hash=hash_ip('10.0.0.81'),
        menu_item=promo,
        deal=None,
    )
    assert imp.serve_count >= 2


@pytest.mark.django_db
def test_compose_cross_fill_when_no_deals(api_client, near_restaurant):
    now = timezone.now()
    promo = MenuItemFactory(
        restaurant=near_restaurant,
        name='CFPromo',
        is_promoted=True,
        promoted_starts_at=now - timedelta(hours=1),
        promoted_ends_at=now + timedelta(days=1),
    )
    for i in range(6):
        MenuItemFactory(restaurant=near_restaurant, name=f'CFI{i}')

    res = api_client.get(
        '/api/explore/products/',
        {'page': '1', 'page_size': '4'},
        REMOTE_ADDR='10.0.0.82',
    )
    assert res.status_code == 200
    rows = res.data['results']
    assert len(rows) == 4
    assert rows[0]['slot'] == 'promoted' and rows[0]['data']['id'] == promo.id
    assert all(r['slot'] == 'organic' and r['type'] == 'item' for r in rows[1:])
