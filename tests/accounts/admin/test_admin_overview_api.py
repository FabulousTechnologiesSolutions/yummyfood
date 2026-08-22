import pytest

from apps.engagement.models import ContentReport, ReportReason, ReportStatus, ReportTargetType
from tests.accounts.factories import AdminUserFactory, CustomerOnlyUserFactory
from tests.discovery.factories import MenuItemFactory, PromoteRequestFactory


@pytest.fixture
def admin_client(auth_client):
    admin = AdminUserFactory()
    return admin, auth_client(admin)


@pytest.mark.django_db
def test_admin_overview(admin_client):
    _admin, client = admin_client
    item = MenuItemFactory()
    PromoteRequestFactory(restaurant=item.restaurant, menu_item=item)
    customer = CustomerOnlyUserFactory()
    ContentReport.objects.create(
        created_by=customer,
        target_type=ReportTargetType.ITEM,
        restaurant=item.restaurant,
        menu_item=item,
        reason=ReportReason.OTHER,
        description='spam',
        status=ReportStatus.OPEN,
    )

    res = client.get('/api/admin/overview/')
    assert res.status_code == 200, res.data
    assert res.data['pending_promotion_requests'] >= 1
    assert res.data['open_reports'] >= 1
    types = {row['type'] for row in res.data['oldest_waiting']}
    assert 'promotion' in types
    assert 'report' in types
    for row in res.data['oldest_waiting']:
        assert 'waiting_minutes' in row
        assert 'title' in row
        assert 'restaurant_name' in row


@pytest.mark.django_db
def test_overview_requires_admin(auth_client):
    user = CustomerOnlyUserFactory()
    res = auth_client(user).get('/api/admin/overview/')
    assert res.status_code == 403
    assert res.data['error']['code'] == 'ADMIN_REQUIRED'
