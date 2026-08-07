from django.db import transaction
from django.utils import timezone

from apps.analytics.models import ResourceAnalytics
from apps.analytics.services.scoring import score_from_analytics_obj
from apps.promotions.models import FeaturedCampaign, PromotionRequestStatus
from apps.restaurants.models import Deal, DealStatus, MenuItem, MenuItemStatus
from core.exceptions import AppAPIException

CLIENT_EVENT_TYPES = {
    'detail_view': 'detail_views',
    'call': 'call_clicks',
    'whatsapp': 'whatsapp_clicks',
    'share': 'share_count',
    'save': 'save_count',
    'follow': 'follow_count',
    'direction': 'direction_clicks',
}

ALL_EVENT_TYPES = {
    **CLIENT_EVENT_TYPES,
    'impression': 'impression_count',
}


def _public_menu_item(item_id: int) -> MenuItem:
    try:
        item = MenuItem.objects.select_related('restaurant').get(pk=item_id)
    except MenuItem.DoesNotExist:
        raise AppAPIException(
            code='MENU_ITEM_NOT_FOUND',
            message='Menu item not found.',
            status_code=404,
        )
    r = item.restaurant
    if (
        item.status != MenuItemStatus.PUBLISHED
        or not item.is_available
        or r.is_paused
        or r.is_permanently_closed
    ):
        raise AppAPIException(
            code='MENU_ITEM_NOT_FOUND',
            message='Menu item not found.',
            status_code=404,
        )
    return item


def _public_deal(deal_id: int) -> Deal:
    try:
        deal = Deal.objects.select_related('restaurant').get(pk=deal_id)
    except Deal.DoesNotExist:
        raise AppAPIException(
            code='DEAL_NOT_FOUND',
            message='Deal not found.',
            status_code=404,
        )
    r = deal.restaurant
    if deal.status != DealStatus.ACTIVE or r.is_paused or r.is_permanently_closed:
        raise AppAPIException(
            code='DEAL_NOT_FOUND',
            message='Deal not found.',
            status_code=404,
        )
    return deal


class EventService:
    @transaction.atomic
    def record(
        self,
        *,
        event_model: str,
        resource_id: int,
        event_type: str,
        user=None,
        allow_impression: bool = False,
    ) -> dict:
        if event_type == 'impression' and not allow_impression:
            raise AppAPIException(
                code='IMPRESSION_SERVER_ONLY',
                message='Impressions are recorded by the Explore API only.',
                status_code=400,
            )
        if event_type not in ALL_EVENT_TYPES:
            raise AppAPIException(
                code='INVALID_EVENT_TYPE',
                message='Invalid event_type.',
                status_code=400,
            )
        if event_model not in ('item', 'deal'):
            raise AppAPIException(
                code='INVALID_EVENT_MODEL',
                message='event_model must be item or deal.',
                status_code=400,
            )

        menu_item = None
        deal = None
        if event_model == 'item':
            menu_item = _public_menu_item(resource_id)
        else:
            deal = _public_deal(resource_id)

        field = ALL_EVENT_TYPES[event_type]
        anon = self._bump_row(menu_item=menu_item, deal=deal, user=None, field=field)
        if user is not None and getattr(user, 'is_authenticated', False):
            self._bump_row(menu_item=menu_item, deal=deal, user=user, field=field)

        self._bump_active_campaign(menu_item=menu_item, deal=deal, field=field)

        return {
            'ok': True,
            'engagement_score': anon.engagement_score,
        }

    def _bump_row(self, *, menu_item, deal, user, field: str) -> ResourceAnalytics:
        defaults = {field: 0}
        lookup = {'user': user}
        if menu_item is not None:
            lookup['menu_item'] = menu_item
            lookup['deal'] = None
        else:
            lookup['deal'] = deal
            lookup['menu_item'] = None

        row, _created = ResourceAnalytics.objects.get_or_create(
            **lookup,
            defaults=defaults,
        )
        setattr(row, field, getattr(row, field) + 1)
        row.engagement_score = score_from_analytics_obj(row)
        row.save(update_fields=[field, 'engagement_score', 'updated_at'])
        return row

    def _bump_active_campaign(self, *, menu_item, deal, field: str):
        now = timezone.now()
        qs = FeaturedCampaign.objects.filter(
            started_at__lte=now,
            ends_at__gte=now,
        )
        if menu_item is not None:
            qs = qs.filter(menu_item=menu_item)
        else:
            qs = qs.filter(deal=deal)
        campaign = (
            qs.filter(
                promotion_request__status=PromotionRequestStatus.LIVE,
            )
            .order_by('-started_at')
            .first()
        )
        if campaign is None:
            # Campaigns without linked request still count if window active
            campaign = qs.order_by('-started_at').first()
        if campaign is None:
            return
        setattr(campaign, field, getattr(campaign, field) + 1)
        campaign.engagement_score = score_from_analytics_obj(campaign)
        campaign.save(update_fields=[field, 'engagement_score', 'updated_at'])
