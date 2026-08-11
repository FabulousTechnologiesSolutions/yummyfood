"""Save / unsave menu items and deals for customers."""

from django.db import transaction
from django.utils import timezone

from apps.analytics.models import ResourceAnalytics
from apps.analytics.services.scoring import score_from_analytics_obj
from apps.engagement.models import SavedItem, SavedTargetType
from apps.restaurants.models import Deal, DealStatus, MenuItem, MenuItemStatus
from apps.restaurants.services.deal_service import serialize_deal
from apps.restaurants.services.menu_item_service import serialize_menu_item
from apps.restaurants.services.restaurant_service import _media_url
from core.exceptions import AppAPIException


def _restaurant_visible(restaurant) -> bool:
    return not restaurant.is_paused and not restaurant.is_permanently_closed


def _resolve_menu_item(menu_item_id: int) -> MenuItem:
    try:
        item = (
            MenuItem.objects.select_related('restaurant', 'restaurant__city')
            .prefetch_related('sizes', 'categories', 'media')
            .get(pk=menu_item_id)
        )
    except MenuItem.DoesNotExist:
        raise AppAPIException(
            code='MENU_ITEM_NOT_FOUND',
            message='Menu item not found.',
            status_code=404,
        )
    if (
        item.status != MenuItemStatus.PUBLISHED
        or not item.is_available
        or not _restaurant_visible(item.restaurant)
    ):
        raise AppAPIException(
            code='MENU_ITEM_NOT_FOUND',
            message='Menu item not found.',
            status_code=404,
        )
    return item


def _resolve_deal(deal_id: int) -> Deal:
    try:
        deal = (
            Deal.objects.select_related('restaurant', 'restaurant__city')
            .prefetch_related('lines__menu_item', 'media')
            .get(pk=deal_id)
        )
    except Deal.DoesNotExist:
        raise AppAPIException(
            code='DEAL_NOT_FOUND',
            message='Deal not found.',
            status_code=404,
        )
    now = timezone.now()
    if (
        deal.status != DealStatus.ACTIVE
        or not _restaurant_visible(deal.restaurant)
        or deal.starts_at > now
        or deal.ends_at < now
    ):
        raise AppAPIException(
            code='DEAL_NOT_FOUND',
            message='Deal not found.',
            status_code=404,
        )
    return deal


def _bump_user_save_count(*, user, menu_item=None, deal=None, delta: int) -> None:
    lookup = {
        'user': user,
        'menu_item': menu_item,
        'deal': deal,
    }
    row, _ = ResourceAnalytics.objects.get_or_create(
        **lookup,
        defaults={'save_count': 0},
    )
    row.save_count = max(0, row.save_count + delta)
    row.engagement_score = score_from_analytics_obj(row)
    row.save(update_fields=['save_count', 'engagement_score', 'updated_at'])


def _serialize_restaurant_compact(restaurant, request=None) -> dict:
    return {
        'id': restaurant.id,
        'name': restaurant.name,
        'slug': restaurant.slug,
        'logo': _media_url(restaurant.logo, request=request),
        'city_id': restaurant.city_id,
        'city': restaurant.city.name if restaurant.city_id else None,
    }


class SavedService:
    def serialize_saved(self, saved: SavedItem, request=None) -> dict:
        restaurant = (
            saved.menu_item.restaurant if saved.menu_item_id else saved.deal.restaurant
        )
        return {
            'id': saved.id,
            'target_type': saved.target_type,
            'created_at': saved.created_at.isoformat() if saved.created_at else None,
            'menu_item': (
                serialize_menu_item(saved.menu_item) if saved.menu_item_id else None
            ),
            'deal': serialize_deal(saved.deal) if saved.deal_id else None,
            'restaurant': _serialize_restaurant_compact(restaurant, request=request),
        }

    @transaction.atomic
    def save(
        self,
        *,
        user,
        target_type: str,
        menu_item_id=None,
        deal_id=None,
    ) -> tuple[SavedItem, bool]:
        if target_type == SavedTargetType.ITEM:
            if not menu_item_id:
                raise AppAPIException(
                    code='INVALID_TARGET_TYPE',
                    message='menu_item_id is required for target_type=item.',
                    status_code=400,
                )
            item = _resolve_menu_item(int(menu_item_id))
            saved, created = SavedItem.objects.get_or_create(
                user=user,
                menu_item=item,
                defaults={
                    'target_type': SavedTargetType.ITEM,
                    'deal': None,
                },
            )
            if created:
                _bump_user_save_count(user=user, menu_item=item, deal=None, delta=1)
            return saved, created

        if target_type == SavedTargetType.DEAL:
            if not deal_id:
                raise AppAPIException(
                    code='INVALID_TARGET_TYPE',
                    message='deal_id is required for target_type=deal.',
                    status_code=400,
                )
            deal = _resolve_deal(int(deal_id))
            saved, created = SavedItem.objects.get_or_create(
                user=user,
                deal=deal,
                defaults={
                    'target_type': SavedTargetType.DEAL,
                    'menu_item': None,
                },
            )
            if created:
                _bump_user_save_count(user=user, menu_item=None, deal=deal, delta=1)
            return saved, created

        raise AppAPIException(
            code='INVALID_TARGET_TYPE',
            message='target_type must be item or deal.',
            status_code=400,
        )

    def list_for_user(self, *, user, type_filter: str | None = None):
        qs = (
            SavedItem.objects.filter(user=user)
            .select_related(
                'menu_item',
                'menu_item__restaurant',
                'menu_item__restaurant__city',
                'deal',
                'deal__restaurant',
                'deal__restaurant__city',
            )
            .prefetch_related(
                'menu_item__sizes',
                'menu_item__categories',
                'menu_item__media',
                'deal__lines__menu_item',
                'deal__media',
            )
            .order_by('-created_at')
        )
        if type_filter in ('items', 'item'):
            qs = qs.filter(target_type=SavedTargetType.ITEM)
        elif type_filter in ('deals', 'deal'):
            qs = qs.filter(target_type=SavedTargetType.DEAL)
        elif type_filter not in (None, ''):
            raise AppAPIException(
                code='INVALID_TARGET_TYPE',
                message='type must be items or deals.',
                status_code=400,
            )
        return qs

    def get_for_user(self, *, user, saved_id: int) -> SavedItem:
        try:
            return (
                SavedItem.objects.filter(user=user)
                .select_related(
                    'menu_item',
                    'menu_item__restaurant',
                    'menu_item__restaurant__city',
                    'deal',
                    'deal__restaurant',
                    'deal__restaurant__city',
                )
                .prefetch_related(
                    'menu_item__sizes',
                    'menu_item__categories',
                    'menu_item__media',
                    'deal__lines__menu_item',
                    'deal__media',
                )
                .get(pk=saved_id)
            )
        except SavedItem.DoesNotExist:
            raise AppAPIException(
                code='SAVED_NOT_FOUND',
                message='Saved item not found.',
                status_code=404,
            )

    @transaction.atomic
    def unsave(self, *, user, saved_id: int) -> None:
        saved = self.get_for_user(user=user, saved_id=saved_id)
        menu_item = saved.menu_item
        deal = saved.deal
        saved.delete()
        _bump_user_save_count(user=user, menu_item=menu_item, deal=deal, delta=-1)
