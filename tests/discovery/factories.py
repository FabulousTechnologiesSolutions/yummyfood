from datetime import timedelta
from decimal import Decimal

import factory
from django.utils import timezone

from apps.analytics.models import ResourceAnalytics
from apps.discovery.models import ExploreImpression, ExploreViewerState
from apps.promotions.models import FeaturedCampaign, PromotionRequest, PromotionRequestStatus
from apps.restaurants.models import Deal, DealStatus, MenuItem, MenuItemStatus
from tests.accounts.factories import RestaurantFactory, UserFactory


class MenuItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MenuItem

    restaurant = factory.SubFactory(RestaurantFactory)
    name = factory.Sequence(lambda n: f'Item {n}')
    base_price = Decimal('100.00')
    status = MenuItemStatus.PUBLISHED
    is_available = True
    published_at = factory.LazyFunction(timezone.now)


class DealFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Deal

    restaurant = factory.SubFactory(RestaurantFactory)
    label = factory.Sequence(lambda n: f'Deal {n}')
    deal_price = Decimal('500.00')
    starts_at = factory.LazyFunction(lambda: timezone.now() - timedelta(days=1))
    ends_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    status = DealStatus.ACTIVE


class ResourceAnalyticsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ResourceAnalytics

    menu_item = factory.SubFactory(MenuItemFactory)
    deal = None
    user = None


class PromoteRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PromotionRequest

    restaurant = factory.SubFactory(RestaurantFactory)
    menu_item = factory.SubFactory(
        MenuItemFactory,
        restaurant=factory.SelfAttribute('..restaurant'),
    )
    deal = None
    status = PromotionRequestStatus.PENDING
    requested_start = factory.LazyFunction(timezone.now)
    requested_end = factory.LazyFunction(lambda: timezone.now() + timedelta(days=3))


class FeaturedCampaignFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FeaturedCampaign

    menu_item = factory.SubFactory(MenuItemFactory)
    deal = None
    started_at = factory.LazyFunction(lambda: timezone.now() - timedelta(hours=1))
    ends_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=2))


class ExploreViewerStateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExploreViewerState

    user = None
    ip_hash = factory.Sequence(lambda n: f'hash{n:064d}'[:64])


class ExploreImpressionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExploreImpression

    user = None
    ip_hash = factory.Sequence(lambda n: f'imphash{n:061d}'[:64])
    menu_item = factory.SubFactory(MenuItemFactory)
    deal = None
    serve_count = 1
