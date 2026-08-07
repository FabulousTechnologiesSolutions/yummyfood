import pytest
from django.db import IntegrityError

from apps.analytics.models import ResourceAnalytics
from apps.analytics.services.scoring import recalculate_score
from apps.discovery.models import ExploreViewerState
from core.utils import haversine_km
from tests.discovery.factories import (
    DealFactory,
    MenuItemFactory,
    ResourceAnalyticsFactory,
)


@pytest.mark.django_db
def test_analytics_exactly_one_resource():
    item = MenuItemFactory()
    deal = DealFactory(restaurant=item.restaurant)
    with pytest.raises(IntegrityError):
        ResourceAnalytics.objects.create(menu_item=item, deal=deal, user=None)


@pytest.mark.django_db
def test_analytics_anon_unique_item():
    item = MenuItemFactory()
    ResourceAnalyticsFactory(menu_item=item, deal=None, user=None)
    with pytest.raises(IntegrityError):
        ResourceAnalyticsFactory(menu_item=item, deal=None, user=None)


@pytest.mark.django_db
def test_score_weights(settings):
    settings.EXPLORE_ENGAGEMENT_WEIGHTS = {
        'impression': 0.2,
        'detail_view': 1,
        'call': 8,
        'whatsapp': 10,
        'share': 6,
        'save': 5,
        'follow': 4,
        'direction': 3,
    }
    score = recalculate_score(
        {
            'impression_count': 2,
            'detail_views': 1,
            'call_clicks': 1,
            'whatsapp_clicks': 0,
            'share_count': 0,
            'save_count': 0,
            'follow_count': 0,
            'direction_clicks': 0,
        }
    )
    assert score == pytest.approx(0.4 + 1 + 8)


def test_haversine_same_point():
    assert haversine_km(31.52, 74.35, 31.52, 74.35) == pytest.approx(0.0, abs=1e-6)


def test_haversine_symmetry():
    a = haversine_km(31.52, 74.35, 31.55, 74.40)
    b = haversine_km(31.55, 74.40, 31.52, 74.35)
    assert a == pytest.approx(b)


@pytest.mark.django_db
def test_viewer_xor_constraint():
    with pytest.raises(IntegrityError):
        ExploreViewerState.objects.create(user=None, ip_hash=None)
