import pytest

from apps.engagement.models import ContentReport, ReportReason, ReportStatus, ReportTargetType
from tests.accounts.factories import AdminUserFactory, CustomerOnlyUserFactory
from tests.discovery.factories import DealFactory, MenuItemFactory


@pytest.fixture
def admin_client(auth_client):
    admin = AdminUserFactory()
    return admin, auth_client(admin)


def _make_report(*, item=None, deal=None, restaurant=None, user=None, status=ReportStatus.OPEN):
    user = user or CustomerOnlyUserFactory()
    kwargs = {
        'created_by': user,
        'reason': ReportReason.PHOTO_MISMATCH,
        'description': 'Looks different',
        'status': status,
    }
    if item is not None:
        kwargs.update(
            target_type=ReportTargetType.ITEM,
            restaurant=item.restaurant,
            menu_item=item,
            deal=None,
        )
    elif deal is not None:
        kwargs.update(
            target_type=ReportTargetType.DEAL,
            restaurant=deal.restaurant,
            menu_item=None,
            deal=deal,
        )
    else:
        kwargs.update(
            target_type=ReportTargetType.RESTAURANT,
            restaurant=restaurant,
            menu_item=None,
            deal=None,
        )
    return ContentReport.objects.create(**kwargs)


@pytest.mark.django_db
def test_admin_reports_list_detail_action_dismiss(admin_client):
    admin, client = admin_client
    item = MenuItemFactory()
    deal = DealFactory()
    open_report = _make_report(item=item)
    _make_report(deal=deal, status=ReportStatus.ACTIONED)

    listed = client.get('/api/admin/reports/')
    assert listed.status_code == 200
    assert listed.data['count'] >= 1
    ids = [r['id'] for r in listed.data['results']]
    assert open_report.id in ids
    row = next(r for r in listed.data['results'] if r['id'] == open_report.id)
    assert row['reason'] == ReportReason.PHOTO_MISMATCH
    assert row['report_count'] >= 1
    assert 'age_minutes' in row

    actioned_list = client.get('/api/admin/reports/?status=actioned')
    assert actioned_list.status_code == 200
    assert all(r['status'] == 'actioned' for r in actioned_list.data['results'])

    detail = client.get(f'/api/admin/reports/{open_report.id}/')
    assert detail.status_code == 200
    assert detail.data['id'] == open_report.id
    assert detail.data['title'] == item.name

    acted = client.post(
        f'/api/admin/reports/{open_report.id}/action/',
        {'admin_note': 'Took down photo'},
        format='json',
    )
    assert acted.status_code == 200, acted.data
    assert acted.data['status'] == ReportStatus.ACTIONED
    assert acted.data['reviewed_by'] == admin.id
    assert acted.data['admin_note'] == 'Took down photo'

    other = _make_report(item=MenuItemFactory())
    dismissed = client.post(
        f'/api/admin/reports/{other.id}/dismiss/',
        {},
        format='json',
    )
    assert dismissed.status_code == 200
    assert dismissed.data['status'] == ReportStatus.DISMISSED


@pytest.mark.django_db
def test_admin_report_not_found(admin_client):
    _admin, client = admin_client
    res = client.get('/api/admin/reports/999999/')
    assert res.status_code == 404
    assert res.data['error']['code'] == 'REPORT_NOT_FOUND'


@pytest.mark.django_db
def test_admin_reports_filter_restaurant_scope(admin_client):
    _admin, client = admin_client
    item = MenuItemFactory()
    restaurant = item.restaurant
    item_report = _make_report(item=item)
    resto_report = _make_report(restaurant=restaurant)

    by_type = client.get('/api/admin/reports/?target_type=restaurant')
    assert by_type.status_code == 200
    ids = [r['id'] for r in by_type.data['results']]
    assert resto_report.id in ids
    assert item_report.id not in ids
    row = next(r for r in by_type.data['results'] if r['id'] == resto_report.id)
    assert row['target_type'] == 'restaurant'
    assert row['menu_item_id'] is None
    assert row['deal_id'] is None
    assert row['restaurant_id'] == restaurant.id
    assert row['title'] == restaurant.name

    by_resto = client.get(f'/api/admin/reports/?restaurant_id={restaurant.id}')
    assert {r['id'] for r in by_resto.data['results']} >= {item_report.id, resto_report.id}
