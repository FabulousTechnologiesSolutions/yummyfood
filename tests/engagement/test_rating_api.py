import pytest

from apps.engagement.models import Rating, RatingTargetType
from tests.accounts.factories import CustomerOnlyUserFactory
from tests.discovery.factories import DealFactory, MenuItemFactory


@pytest.fixture
def customer_client(auth_client):
    user = CustomerOnlyUserFactory()
    return user, auth_client(user)


@pytest.mark.django_db
def test_rate_restaurant_upsert_and_aggregates(customer_client):
    user, client = customer_client
    restaurant = MenuItemFactory().restaurant
    url = f'/api/restaurants/{restaurant.id}/rating/'

    created = client.post(url, {'stars': 4, 'description': 'Great food'}, format='json')
    assert created.status_code == 201, created.data
    assert created.data['stars'] == 4
    assert created.data['description'] == 'Great food'
    assert created.data['rated_at']
    assert created.data['created_by'] == user.id
    assert created.data['target_type'] == 'restaurant'
    assert created.data['restaurant_id'] == restaurant.id
    assert created.data['menu_item_id'] is None
    assert created.data['deal_id'] is None

    restaurant.refresh_from_db()
    assert restaurant.rating_count == 1
    assert str(restaurant.rating_avg) == '4.0'
    assert restaurant.rating_histogram.get('4') == 1

    updated = client.post(url, {'stars': 5, 'description': 'Even better'}, format='json')
    assert updated.status_code == 200, updated.data
    assert updated.data['stars'] == 5
    assert Rating.objects.filter(
        user=user,
        restaurant=restaurant,
        target_type=RatingTargetType.RESTAURANT,
    ).count() == 1

    restaurant.refresh_from_db()
    assert restaurant.rating_count == 1
    assert str(restaurant.rating_avg) == '5.0'
    assert restaurant.rating_histogram.get('5') == 1
    assert restaurant.rating_histogram.get('4') == 0

    mine = client.get(url)
    assert mine.status_code == 200
    assert mine.data['stars'] == 5


@pytest.mark.django_db
def test_rate_invalid_stars(customer_client):
    _user, client = customer_client
    restaurant = MenuItemFactory().restaurant
    res = client.post(
        f'/api/restaurants/{restaurant.id}/rating/',
        {'stars': 6},
        format='json',
    )
    assert res.status_code == 400
    assert res.data['error']['code'] == 'INVALID_STARS'


@pytest.mark.django_db
def test_rate_missing_restaurant(customer_client):
    _user, client = customer_client
    res = client.post('/api/restaurants/999999/rating/', {'stars': 3}, format='json')
    assert res.status_code == 404
    assert res.data['error']['code'] == 'RESTAURANT_NOT_FOUND'


@pytest.mark.django_db
def test_get_rating_not_found(customer_client):
    _user, client = customer_client
    restaurant = MenuItemFactory().restaurant
    res = client.get(f'/api/restaurants/{restaurant.id}/rating/')
    assert res.status_code == 404
    assert res.data['error']['code'] == 'RATING_NOT_FOUND'


@pytest.mark.django_db
def test_rate_item_upsert(customer_client):
    user, client = customer_client
    item = MenuItemFactory()
    url = f'/api/menu-items/{item.id}/rating/'

    created = client.post(url, {'stars': 3, 'description': 'Okay'}, format='json')
    assert created.status_code == 201, created.data
    assert created.data['target_type'] == 'item'
    assert created.data['menu_item_id'] == item.id
    assert created.data['deal_id'] is None
    assert created.data['restaurant_id'] == item.restaurant_id
    assert created.data['stars'] == 3
    assert created.data['created_by'] == user.id

    item.restaurant.refresh_from_db()
    assert item.restaurant.rating_count == 0

    updated = client.post(url, {'stars': 5, 'description': 'Loved it'}, format='json')
    assert updated.status_code == 200, updated.data
    assert updated.data['stars'] == 5
    assert Rating.objects.filter(user=user, menu_item=item).count() == 1

    mine = client.get(url)
    assert mine.status_code == 200
    assert mine.data['stars'] == 5
    assert mine.data['description'] == 'Loved it'


@pytest.mark.django_db
def test_rate_deal_upsert(customer_client):
    user, client = customer_client
    deal = DealFactory()
    url = f'/api/deals/{deal.id}/rating/'

    created = client.post(url, {'stars': 2}, format='json')
    assert created.status_code == 201, created.data
    assert created.data['target_type'] == 'deal'
    assert created.data['deal_id'] == deal.id
    assert created.data['menu_item_id'] is None
    assert created.data['restaurant_id'] == deal.restaurant_id

    updated = client.post(url, {'stars': 4, 'description': 'Better than expected'}, format='json')
    assert updated.status_code == 200, updated.data
    assert Rating.objects.filter(user=user, deal=deal).count() == 1

    mine = client.get(url)
    assert mine.status_code == 200
    assert mine.data['stars'] == 4


@pytest.mark.django_db
def test_item_deal_and_restaurant_ratings_are_independent(customer_client):
    user, client = customer_client
    item = MenuItemFactory()
    deal = DealFactory(restaurant=item.restaurant)
    restaurant = item.restaurant

    item_res = client.post(
        f'/api/menu-items/{item.id}/rating/',
        {'stars': 5},
        format='json',
    )
    deal_res = client.post(
        f'/api/deals/{deal.id}/rating/',
        {'stars': 2},
        format='json',
    )
    resto_res = client.post(
        f'/api/restaurants/{restaurant.id}/rating/',
        {'stars': 4},
        format='json',
    )
    assert item_res.status_code == 201
    assert deal_res.status_code == 201
    assert resto_res.status_code == 201
    assert Rating.objects.filter(user=user).count() == 3

    restaurant.refresh_from_db()
    assert restaurant.rating_count == 1
    assert str(restaurant.rating_avg) == '4.0'


@pytest.mark.django_db
def test_rate_unpublished_item_404(customer_client):
    _user, client = customer_client
    from apps.restaurants.models import MenuItemStatus

    item = MenuItemFactory(status=MenuItemStatus.DRAFT)
    res = client.post(f'/api/menu-items/{item.id}/rating/', {'stars': 4}, format='json')
    assert res.status_code == 404
    assert res.data['error']['code'] == 'MENU_ITEM_NOT_FOUND'


@pytest.mark.django_db
def test_get_item_rating_not_found(customer_client):
    _user, client = customer_client
    item = MenuItemFactory()
    res = client.get(f'/api/menu-items/{item.id}/rating/')
    assert res.status_code == 404
    assert res.data['error']['code'] == 'RATING_NOT_FOUND'
