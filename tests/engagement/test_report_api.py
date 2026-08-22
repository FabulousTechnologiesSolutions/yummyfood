import pytest

from apps.engagement.models import ContentReport, ReportStatus
from tests.accounts.factories import CustomerOnlyUserFactory, RestaurantOnlyUserFactory
from tests.discovery.factories import DealFactory, MenuItemFactory

REPORT_ITEM = '/api/reports/items/{}/'
REPORT_DEAL = '/api/reports/deals/{}/'


@pytest.fixture
def customer_client(auth_client):
    user = CustomerOnlyUserFactory()
    return user, auth_client(user)


@pytest.mark.django_db
def test_report_item(customer_client):
    user, client = customer_client
    item = MenuItemFactory()
    res = client.post(
        REPORT_ITEM.format(item.id),
        {'reason': 'misleading_price', 'description': 'Price is fake'},
        format='json',
    )
    assert res.status_code == 201, res.data
    assert res.data['reason'] == 'misleading_price'
    assert res.data['description'] == 'Price is fake'
    assert res.data['created_by'] == user.id
    assert res.data['created_at']
    assert res.data['menu_item_id'] == item.id
    assert res.data['deal_id'] is None
    assert res.data['target_type'] == 'item'
    assert res.data['restaurant_id'] == item.restaurant_id
    assert res.data['status'] == ReportStatus.OPEN
    assert ContentReport.objects.filter(created_by=user, menu_item=item).count() == 1


@pytest.mark.django_db
def test_report_item_duplicate_409(customer_client):
    _user, client = customer_client
    item = MenuItemFactory()
    payload = {'reason': 'other', 'description': 'x'}
    assert client.post(REPORT_ITEM.format(item.id), payload, format='json').status_code == 201
    again = client.post(REPORT_ITEM.format(item.id), payload, format='json')
    assert again.status_code == 409
    assert again.data['error']['code'] == 'REPORT_EXISTS'


@pytest.mark.django_db
def test_report_deal(customer_client):
    user, client = customer_client
    deal = DealFactory()
    res = client.post(
        REPORT_DEAL.format(deal.id),
        {'reason': 'unavailable', 'description': 'Sold out forever'},
        format='json',
    )
    assert res.status_code == 201, res.data
    assert res.data['deal_id'] == deal.id
    assert res.data['menu_item_id'] is None
    assert res.data['target_type'] == 'deal'
    assert res.data['restaurant_id'] == deal.restaurant_id
    assert res.data['created_by'] == user.id
    assert res.data['created_at']


@pytest.mark.django_db
def test_report_unpublished_item_404(customer_client):
    _user, client = customer_client
    item = MenuItemFactory(status='draft', is_available=False)
    res = client.post(
        REPORT_ITEM.format(item.id),
        {'reason': 'other'},
        format='json',
    )
    assert res.status_code == 404


@pytest.mark.django_db
def test_report_requires_customer_mode(auth_client):
    owner = RestaurantOnlyUserFactory()
    item = MenuItemFactory()
    client = auth_client(owner)
    res = client.post(
        REPORT_ITEM.format(item.id),
        {'reason': 'other'},
        format='json',
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_report_restaurant(customer_client):
    user, client = customer_client
    restaurant = MenuItemFactory().restaurant
    res = client.post(
        f'/api/reports/restaurants/{restaurant.id}/',
        {'reason': 'other', 'description': 'Whole place is misleading'},
        format='json',
    )
    assert res.status_code == 201, res.data
    assert res.data['target_type'] == 'restaurant'
    assert res.data['restaurant_id'] == restaurant.id
    assert res.data['menu_item_id'] is None
    assert res.data['deal_id'] is None
    assert res.data['title'] == restaurant.name
    assert res.data['created_by'] == user.id
    assert ContentReport.objects.filter(
        created_by=user,
        restaurant=restaurant,
        target_type='restaurant',
        menu_item__isnull=True,
        deal__isnull=True,
    ).count() == 1


@pytest.mark.django_db
def test_report_restaurant_duplicate_409(customer_client):
    _user, client = customer_client
    restaurant = MenuItemFactory().restaurant
    url = f'/api/reports/restaurants/{restaurant.id}/'
    payload = {'reason': 'other'}
    assert client.post(url, payload, format='json').status_code == 201
    again = client.post(url, payload, format='json')
    assert again.status_code == 409
    assert again.data['error']['code'] == 'REPORT_EXISTS'


@pytest.mark.django_db
def test_report_item_and_restaurant_are_independent(customer_client):
    _user, client = customer_client
    item = MenuItemFactory()
    assert (
        client.post(
            REPORT_ITEM.format(item.id),
            {'reason': 'misleading_price'},
            format='json',
        ).status_code
        == 201
    )
    resto = client.post(
        f'/api/reports/restaurants/{item.restaurant_id}/',
        {'reason': 'other'},
        format='json',
    )
    assert resto.status_code == 201, resto.data
    assert resto.data['target_type'] == 'restaurant'
    assert resto.data['menu_item_id'] is None


@pytest.mark.django_db
def test_report_paused_restaurant_404(customer_client):
    _user, client = customer_client
    restaurant = MenuItemFactory().restaurant
    restaurant.is_paused = True
    restaurant.save(update_fields=['is_paused'])
    res = client.post(
        f'/api/reports/restaurants/{restaurant.id}/',
        {'reason': 'other'},
        format='json',
    )
    assert res.status_code == 404
    assert res.data['error']['code'] == 'RESTAURANT_NOT_FOUND'
