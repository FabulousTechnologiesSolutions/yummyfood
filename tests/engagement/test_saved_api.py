import pytest

from apps.analytics.models import ResourceAnalytics
from apps.engagement.models import SavedItem
from tests.accounts.factories import (
    BothProfilesUserFactory,
    CustomerOnlyUserFactory,
    RestaurantOnlyUserFactory,
)
from tests.discovery.factories import DealFactory, MenuItemFactory

SAVED_URL = '/api/saved/'


@pytest.fixture
def customer_client(auth_client):
    user = CustomerOnlyUserFactory()
    return user, auth_client(user)


@pytest.mark.django_db
def test_save_item_and_analytics(customer_client):
    user, client = customer_client
    item = MenuItemFactory()

    res = client.post(
        SAVED_URL,
        {'target_type': 'item', 'menu_item_id': item.id},
        format='json',
    )
    assert res.status_code == 201
    assert res.data['target_type'] == 'item'
    assert res.data['menu_item']['id'] == item.id
    assert res.data['deal'] is None
    assert res.data['restaurant']['id'] == item.restaurant_id

    analytics = ResourceAnalytics.objects.get(user=user, menu_item=item, deal=None)
    assert analytics.save_count == 1

    again = client.post(
        SAVED_URL,
        {'target_type': 'item', 'menu_item_id': item.id},
        format='json',
    )
    assert again.status_code == 200
    analytics.refresh_from_db()
    assert analytics.save_count == 1
    assert SavedItem.objects.filter(user=user, menu_item=item).count() == 1


@pytest.mark.django_db
def test_save_deal_and_unsave_decrements(customer_client):
    user, client = customer_client
    deal = DealFactory()

    res = client.post(
        SAVED_URL,
        {'target_type': 'deal', 'deal_id': deal.id},
        format='json',
    )
    assert res.status_code == 201
    saved_id = res.data['id']

    analytics = ResourceAnalytics.objects.get(user=user, deal=deal, menu_item=None)
    assert analytics.save_count == 1

    delete = client.delete(f'{SAVED_URL}{saved_id}/')
    assert delete.status_code == 204
    assert not SavedItem.objects.filter(id=saved_id).exists()
    analytics.refresh_from_db()
    assert analytics.save_count == 0


@pytest.mark.django_db
def test_list_filter_and_detail(customer_client):
    user, client = customer_client
    item = MenuItemFactory()
    deal = DealFactory()
    client.post(SAVED_URL, {'target_type': 'item', 'menu_item_id': item.id}, format='json')
    deal_res = client.post(
        SAVED_URL, {'target_type': 'deal', 'deal_id': deal.id}, format='json'
    )

    all_res = client.get(SAVED_URL)
    assert all_res.status_code == 200
    assert all_res.data['count'] == 2

    items = client.get(SAVED_URL, {'type': 'items'})
    assert items.data['count'] == 1
    assert items.data['results'][0]['target_type'] == 'item'

    deals = client.get(SAVED_URL, {'type': 'deals'})
    assert deals.data['count'] == 1
    assert deals.data['results'][0]['target_type'] == 'deal'

    detail = client.get(f'{SAVED_URL}{deal_res.data["id"]}/')
    assert detail.status_code == 200
    assert detail.data['deal']['id'] == deal.id
    assert detail.data['deal']['label'] == deal.label


@pytest.mark.django_db
def test_unsave_other_user_404(auth_client, customer_client):
    user, client = customer_client
    item = MenuItemFactory()
    saved = client.post(
        SAVED_URL, {'target_type': 'item', 'menu_item_id': item.id}, format='json'
    ).data

    other = CustomerOnlyUserFactory()
    other_client = auth_client(other)
    res = other_client.delete(f'{SAVED_URL}{saved["id"]}/')
    assert res.status_code == 404
    assert res.data['error']['code'] == 'SAVED_NOT_FOUND'


@pytest.mark.django_db
def test_restaurant_mode_forbidden(auth_client):
    user = BothProfilesUserFactory()
    client = auth_client(user, active_mode='restaurant')
    item = MenuItemFactory()
    res = client.post(
        SAVED_URL, {'target_type': 'item', 'menu_item_id': item.id}, format='json'
    )
    assert res.status_code == 403
    assert res.data['error']['code'] == 'CUSTOMER_MODE_REQUIRED'


@pytest.mark.django_db
def test_guest_unauthorized(api_client):
    item = MenuItemFactory()
    res = api_client.post(
        SAVED_URL, {'target_type': 'item', 'menu_item_id': item.id}, format='json'
    )
    assert res.status_code in (401, 403)


@pytest.mark.django_db
def test_no_customer_profile_forbidden(auth_client):
    user = RestaurantOnlyUserFactory()
    client = auth_client(user)
    item = MenuItemFactory()
    res = client.post(
        SAVED_URL, {'target_type': 'item', 'menu_item_id': item.id}, format='json'
    )
    assert res.status_code == 403
