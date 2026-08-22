import pytest

from apps.restaurants.models import ClaimStatus, MenuCategory
from tests.accounts.factories import (
    AdminUserFactory,
    CustomerOnlyUserFactory,
    RestaurantOnlyUserFactory,
)
from tests.discovery.factories import MenuItemFactory


@pytest.fixture
def admin_client(auth_client):
    admin = AdminUserFactory()
    return admin, auth_client(admin)


@pytest.mark.django_db
def test_admin_restaurants_list_and_detail(admin_client):
    _admin, client = admin_client
    item = MenuItemFactory()
    restaurant = item.restaurant
    restaurant.is_paused = True
    restaurant.save(update_fields=['is_paused'])

    listed = client.get('/api/admin/restaurants/?status=paused')
    assert listed.status_code == 200, listed.data
    ids = [r['id'] for r in listed.data['results']]
    assert restaurant.id in ids
    row = next(r for r in listed.data['results'] if r['id'] == restaurant.id)
    assert row['status'] == 'paused'
    assert row['products_count'] >= 1
    assert 'promotions_count' in row
    assert 'pending_promotions_count' in row

    detail = client.get(f'/api/admin/restaurants/{restaurant.id}/')
    assert detail.status_code == 200
    assert detail.data['id'] == restaurant.id
    assert detail.data['name'] == restaurant.name

    claimed = MenuItemFactory().restaurant
    claimed.claim_status = ClaimStatus.UNCLAIMED
    claimed.is_paused = False
    claimed.save(update_fields=['claim_status', 'is_paused'])
    claim_list = client.get('/api/admin/restaurants/?status=claim')
    assert claimed.id in [r['id'] for r in claim_list.data['results']]


@pytest.mark.django_db
def test_admin_users_list_and_detail(admin_client):
    admin, client = admin_client
    customer = CustomerOnlyUserFactory(display_name='Cust One')
    owner = RestaurantOnlyUserFactory(display_name='Owner One')

    listed = client.get('/api/admin/users/')
    assert listed.status_code == 200
    by_id = {u['id']: u for u in listed.data['results']}
    assert by_id[admin.id]['role'] == 'staff'
    assert by_id[customer.id]['role'] == 'customer'
    assert by_id[owner.id]['role'] == 'owner'
    assert by_id[customer.id]['phone_number'] == customer.phone_number
    assert 'last_active_at' in by_id[customer.id]

    staff_only = client.get('/api/admin/users/?role=staff')
    assert all(u['role'] == 'staff' for u in staff_only.data['results'])

    search = client.get('/api/admin/users/?q=Cust')
    assert customer.id in [u['id'] for u in search.data['results']]

    detail = client.get(f'/api/admin/users/{owner.id}/')
    assert detail.status_code == 200
    assert detail.data['role'] == 'owner'


@pytest.mark.django_db
def test_admin_categories_crud(admin_client):
    _admin, client = admin_client
    RestaurantOnlyUserFactory()
    listed = client.get('/api/admin/categories/')
    assert listed.status_code == 200
    assert isinstance(listed.data.get('results'), list)
    if listed.data['results']:
        assert 'used_by' in listed.data['results'][0]

    created = client.post(
        '/api/admin/categories/',
        {'name': 'Admin Only Cat'},
        format='json',
    )
    assert created.status_code == 201, created.data
    assert created.data['name'] == 'Admin Only Cat'
    assert created.data['slug']
    assert created.data['used_by'] == 0
    cat_id = created.data['id']

    patched = client.patch(
        f'/api/admin/categories/{cat_id}/',
        {'name': 'Renamed Cat', 'is_visible': False},
        format='json',
    )
    assert patched.status_code == 200
    assert patched.data['name'] == 'Renamed Cat'
    assert patched.data['is_visible'] is False

    deleted = client.delete(f'/api/admin/categories/{cat_id}/')
    assert deleted.status_code == 204
    assert not MenuCategory.objects.filter(pk=cat_id).exists()


@pytest.mark.django_db
def test_admin_list_pagination(admin_client):
    _admin, client = admin_client
    users = [CustomerOnlyUserFactory() for _ in range(12)]
    page1 = client.get('/api/admin/users/?page_size=10&page=1')
    assert page1.status_code == 200
    assert page1.data['count'] >= 13
    assert len(page1.data['results']) == 10
    assert page1.data['next']
    assert page1.data['previous'] is None

    page2 = client.get('/api/admin/users/?page_size=10&page=2')
    assert page2.status_code == 200
    assert len(page2.data['results']) >= 3
    assert page2.data['previous']
    page1_ids = {u['id'] for u in page1.data['results']}
    page2_ids = {u['id'] for u in page2.data['results']}
    assert not page1_ids.intersection(page2_ids)
    assert users[-1].id in page1_ids.union(page2_ids)


@pytest.mark.django_db
def test_admin_category_in_use(admin_client):
    _admin, client = admin_client
    item = MenuItemFactory()
    category = MenuCategory.objects.create(slug='in-use-cat', name='In Use')
    item.categories.add(category)
    res = client.delete(f'/api/admin/categories/{category.id}/')
    assert res.status_code == 400
    assert res.data['error']['code'] == 'CATEGORY_IN_USE'
