from django.utils import timezone

from apps.engagement.models import ContentReport, ReportStatus
from apps.promotions.models import PromotionRequest, PromotionRequestStatus


class OverviewService:
    OLDEST_LIMIT = 10

    def get(self) -> dict:
        now = timezone.now()
        pending_qs = PromotionRequest.objects.filter(
            status=PromotionRequestStatus.PENDING
        ).select_related('restaurant', 'menu_item', 'deal')
        open_qs = ContentReport.objects.filter(status=ReportStatus.OPEN).select_related(
            'restaurant',
            'menu_item',
            'deal',
        )

        pending_count = pending_qs.count()
        open_count = open_qs.count()

        waiting = []
        for req in pending_qs.order_by('created_at')[: self.OLDEST_LIMIT]:
            title = ''
            if req.menu_item_id:
                title = req.menu_item.name
            elif req.deal_id:
                title = req.deal.label
            waiting.append(
                {
                    'id': req.id,
                    'type': 'promotion',
                    'title': title,
                    'restaurant_name': req.restaurant.name if req.restaurant_id else None,
                    'waiting_minutes': int((now - req.created_at).total_seconds() // 60),
                    'created_at': req.created_at,
                }
            )
        for report in open_qs.order_by('created_at')[: self.OLDEST_LIMIT]:
            restaurant = report.restaurant
            title = None
            if report.menu_item_id:
                title = report.menu_item.name
            elif report.deal_id:
                title = report.deal.label
            elif restaurant is not None:
                title = restaurant.name
            waiting.append(
                {
                    'id': report.id,
                    'type': 'report',
                    'title': title,
                    'restaurant_name': restaurant.name if restaurant else None,
                    'waiting_minutes': int((now - report.created_at).total_seconds() // 60),
                    'created_at': report.created_at,
                }
            )
        waiting.sort(key=lambda row: row['created_at'])
        oldest = []
        for row in waiting[: self.OLDEST_LIMIT]:
            oldest.append(
                {
                    'id': row['id'],
                    'type': row['type'],
                    'title': row['title'],
                    'restaurant_name': row['restaurant_name'],
                    'waiting_minutes': row['waiting_minutes'],
                }
            )
        return {
            'pending_promotion_requests': pending_count,
            'open_reports': open_count,
            'oldest_waiting': oldest,
        }
