from django.utils import timezone

from apps.promotions.models import FeaturedCampaign, PromotionRequest, PromotionRequestStatus
from apps.restaurants.models import Deal, MenuItem
from core.exceptions import AppAPIException


def serialize_promotion_request(req: PromotionRequest) -> dict:
    return {
        'id': req.id,
        'restaurant_id': req.restaurant_id,
        'event_model': 'item' if req.menu_item_id else 'deal',
        'resource_id': req.menu_item_id or req.deal_id,
        'menu_item_id': req.menu_item_id,
        'deal_id': req.deal_id,
        'status': req.status,
        'requested_start': req.requested_start.isoformat() if req.requested_start else None,
        'requested_end': req.requested_end.isoformat() if req.requested_end else None,
        'goes_live_at': req.goes_live_at.isoformat() if req.goes_live_at else None,
        'ends_at': req.ends_at.isoformat() if req.ends_at else None,
        'admin_note': req.admin_note,
        'reviewed_at': req.reviewed_at.isoformat() if req.reviewed_at else None,
        'created_at': req.created_at.isoformat() if req.created_at else None,
        'updated_at': req.updated_at.isoformat() if req.updated_at else None,
    }


def clear_resource_promotion(*, menu_item=None, deal=None):
    if menu_item is not None:
        MenuItem.objects.filter(pk=menu_item.pk).update(
            is_promoted=False,
            promoted_starts_at=None,
            promoted_ends_at=None,
        )
    if deal is not None:
        Deal.objects.filter(pk=deal.pk).update(
            is_promoted=False,
            promoted_starts_at=None,
            promoted_ends_at=None,
        )


def expire_promotion_resources(now=None) -> int:
    """Clear expired promos. Returns count of resources cleared."""
    now = now or timezone.now()
    cleared = 0
    items = list(
        MenuItem.objects.filter(is_promoted=True, promoted_ends_at__lte=now).only('id')
    )
    deals = list(Deal.objects.filter(is_promoted=True, promoted_ends_at__lte=now).only('id'))
    if items:
        MenuItem.objects.filter(id__in=[i.id for i in items]).update(
            is_promoted=False,
            promoted_starts_at=None,
            promoted_ends_at=None,
        )
        cleared += len(items)
    if deals:
        Deal.objects.filter(id__in=[d.id for d in deals]).update(
            is_promoted=False,
            promoted_starts_at=None,
            promoted_ends_at=None,
        )
        cleared += len(deals)
    PromotionRequest.objects.filter(
        status=PromotionRequestStatus.LIVE,
        ends_at__lte=now,
    ).update(status=PromotionRequestStatus.ENDED)
    return cleared


class PromotionService:
    def list_for_restaurant(self, *, restaurant):
        return list(
            PromotionRequest.objects.filter(restaurant=restaurant).order_by('-created_at')
        )

    def get_for_restaurant(self, *, restaurant, request_id: int) -> PromotionRequest:
        try:
            return PromotionRequest.objects.get(pk=request_id, restaurant=restaurant)
        except PromotionRequest.DoesNotExist:
            raise AppAPIException(
                code='PROMOTION_REQUEST_NOT_FOUND',
                message='Promotion request not found.',
                status_code=404,
            )

    def create(
        self,
        *,
        restaurant,
        event_model: str,
        resource_id: int,
        requested_start,
        requested_end,
    ) -> PromotionRequest:
        if requested_end <= requested_start:
            raise AppAPIException(
                code='INVALID_PROMO_WINDOW',
                message='requested_end must be after requested_start.',
                status_code=400,
            )
        menu_item = None
        deal = None
        if event_model == 'item':
            try:
                menu_item = MenuItem.objects.get(pk=resource_id, restaurant=restaurant)
            except MenuItem.DoesNotExist:
                raise AppAPIException(
                    code='MENU_ITEM_NOT_FOUND',
                    message='Menu item not found.',
                    status_code=404,
                )
        elif event_model == 'deal':
            try:
                deal = Deal.objects.get(pk=resource_id, restaurant=restaurant)
            except Deal.DoesNotExist:
                raise AppAPIException(
                    code='DEAL_NOT_FOUND',
                    message='Deal not found.',
                    status_code=404,
                )
        else:
            raise AppAPIException(
                code='INVALID_EVENT_MODEL',
                message='event_model must be item or deal.',
                status_code=400,
            )
        return PromotionRequest.objects.create(
            restaurant=restaurant,
            menu_item=menu_item,
            deal=deal,
            requested_start=requested_start,
            requested_end=requested_end,
            status=PromotionRequestStatus.PENDING,
        )

    def list_admin(self, *, status_filter=None):
        qs = PromotionRequest.objects.select_related(
            'restaurant',
            'menu_item',
            'deal',
        ).order_by('-created_at')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return list(qs)

    def approve(
        self,
        *,
        request_id: int,
        admin_user,
        goes_live_at=None,
        ends_at=None,
    ) -> PromotionRequest:
        try:
            req = PromotionRequest.objects.select_related('menu_item', 'deal').get(
                pk=request_id
            )
        except PromotionRequest.DoesNotExist:
            raise AppAPIException(
                code='PROMOTION_REQUEST_NOT_FOUND',
                message='Promotion request not found.',
                status_code=404,
            )
        if req.status == PromotionRequestStatus.LIVE:
            raise AppAPIException(
                code='ALREADY_LIVE',
                message='Promotion request is already live.',
                status_code=400,
            )
        if req.status == PromotionRequestStatus.ENDED:
            raise AppAPIException(
                code='ALREADY_ENDED',
                message='Promotion request has ended.',
                status_code=400,
            )

        live_at = goes_live_at or req.requested_start
        end_at = ends_at or req.requested_end
        if end_at <= live_at:
            raise AppAPIException(
                code='INVALID_PROMO_WINDOW',
                message='ends_at must be after goes_live_at.',
                status_code=400,
            )

        now = timezone.now()
        req.status = PromotionRequestStatus.LIVE
        req.goes_live_at = live_at
        req.ends_at = end_at
        req.reviewed_by = admin_user
        req.reviewed_at = now
        req.admin_note = ''
        req.save(
            update_fields=[
                'status',
                'goes_live_at',
                'ends_at',
                'reviewed_by',
                'reviewed_at',
                'admin_note',
                'updated_at',
            ]
        )

        if end_at <= now:
            req.status = PromotionRequestStatus.ENDED
            req.save(update_fields=['status', 'updated_at'])
            expire_promotion_resources(now=now)
            return req

        resource = req.menu_item or req.deal
        resource.is_promoted = True
        resource.promoted_starts_at = live_at
        resource.promoted_ends_at = end_at
        resource.save(
            update_fields=[
                'is_promoted',
                'promoted_starts_at',
                'promoted_ends_at',
                'updated_at',
            ]
        )

        FeaturedCampaign.objects.create(
            menu_item=req.menu_item,
            deal=req.deal,
            promotion_request=req,
            started_at=live_at,
            ends_at=end_at,
        )
        return req

    def reject(self, *, request_id: int, admin_user, admin_note: str) -> PromotionRequest:
        try:
            req = PromotionRequest.objects.get(pk=request_id)
        except PromotionRequest.DoesNotExist:
            raise AppAPIException(
                code='PROMOTION_REQUEST_NOT_FOUND',
                message='Promotion request not found.',
                status_code=404,
            )
        if req.status == PromotionRequestStatus.CHANGES:
            raise AppAPIException(
                code='ALREADY_REJECTED',
                message='Promotion request was already rejected.',
                status_code=400,
            )
        if req.status == PromotionRequestStatus.LIVE:
            raise AppAPIException(
                code='ALREADY_LIVE',
                message='Cannot reject a live promotion; expire it instead.',
                status_code=400,
            )
        req.status = PromotionRequestStatus.CHANGES
        req.admin_note = admin_note or ''
        req.reviewed_by = admin_user
        req.reviewed_at = timezone.now()
        req.save(
            update_fields=[
                'status',
                'admin_note',
                'reviewed_by',
                'reviewed_at',
                'updated_at',
            ]
        )
        return req
