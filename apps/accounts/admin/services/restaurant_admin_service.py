from django.db.models import Count, Q

from apps.promotions.models import PromotionRequestStatus
from apps.restaurants.models import ClaimStatus, MenuItemStatus, Restaurant
from apps.restaurants.services.restaurant_service import _media_url, serialize_restaurant_public
from core.exceptions import AppAPIException


def derive_restaurant_status(restaurant: Restaurant) -> str:
    if restaurant.is_paused:
        return 'paused'
    if restaurant.claim_status in (ClaimStatus.UNCLAIMED, ClaimStatus.PENDING_CLAIM):
        return 'claim'
    if restaurant.setup_completeness_pct < 100:
        return 'incomplete'
    return 'live'


class RestaurantAdminService:
    VALID_STATUSES = {'live', 'paused', 'claim', 'incomplete'}

    def list(self, *, status_filter: str | None = None, q: str | None = None):
        if status_filter and status_filter not in self.VALID_STATUSES:
            raise AppAPIException(
                code='INVALID_RESTAURANT_STATUS',
                message='status must be live, paused, claim, or incomplete.',
                status_code=400,
            )
        qs = Restaurant.objects.select_related('city', 'owner').annotate(
            products_count=Count(
                'menu_items',
                filter=Q(menu_items__status=MenuItemStatus.PUBLISHED),
                distinct=True,
            ),
            promotions_count=Count(
                'promotion_requests',
                filter=Q(promotion_requests__status=PromotionRequestStatus.LIVE),
                distinct=True,
            ),
            pending_promotions_count=Count(
                'promotion_requests',
                filter=Q(promotion_requests__status=PromotionRequestStatus.PENDING),
                distinct=True,
            ),
        )
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(area__icontains=q)
                | Q(city__name__icontains=q)
            )
        claim_statuses = (ClaimStatus.UNCLAIMED, ClaimStatus.PENDING_CLAIM)
        if status_filter == 'paused':
            qs = qs.filter(is_paused=True)
        elif status_filter == 'claim':
            qs = qs.filter(is_paused=False, claim_status__in=claim_statuses)
        elif status_filter == 'incomplete':
            qs = qs.filter(is_paused=False).exclude(
                claim_status__in=claim_statuses,
            ).filter(setup_completeness_pct__lt=100)
        elif status_filter == 'live':
            qs = qs.filter(is_paused=False).exclude(
                claim_status__in=claim_statuses,
            ).filter(setup_completeness_pct__gte=100)
        return qs.order_by('name')

    def get(self, *, restaurant_id: int, request=None) -> dict:
        qs = Restaurant.objects.select_related('city', 'owner').annotate(
            products_count=Count(
                'menu_items',
                filter=Q(menu_items__status=MenuItemStatus.PUBLISHED),
                distinct=True,
            ),
            promotions_count=Count(
                'promotion_requests',
                filter=Q(promotion_requests__status=PromotionRequestStatus.LIVE),
                distinct=True,
            ),
            pending_promotions_count=Count(
                'promotion_requests',
                filter=Q(promotion_requests__status=PromotionRequestStatus.PENDING),
                distinct=True,
            ),
        )
        try:
            restaurant = qs.get(pk=restaurant_id)
        except Restaurant.DoesNotExist:
            raise AppAPIException(
                code='RESTAURANT_NOT_FOUND',
                message='Restaurant not found.',
                status_code=404,
            )
        return self.serialize(restaurant, request=request)

    def serialize(self, restaurant: Restaurant, *, request=None, status: str | None = None) -> dict:
        status = status or derive_restaurant_status(restaurant)
        public = serialize_restaurant_public(restaurant, request=request)
        return {
            'id': restaurant.id,
            'name': restaurant.name,
            'area': restaurant.area,
            'city': public.get('city'),
            'city_id': restaurant.city_id,
            'logo': _media_url(restaurant.logo, request=request),
            'products_count': getattr(restaurant, 'products_count', 0),
            'promotions_count': getattr(restaurant, 'promotions_count', 0),
            'pending_promotions_count': getattr(restaurant, 'pending_promotions_count', 0),
            'status': status,
            'claim_status': restaurant.claim_status,
            'is_paused': restaurant.is_paused,
            'setup_completeness_pct': restaurant.setup_completeness_pct,
            'rating_avg': str(restaurant.rating_avg),
            'rating_count': restaurant.rating_count,
            'owner_id': restaurant.owner_id,
        }
