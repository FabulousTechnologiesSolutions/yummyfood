"""Customer reports for menu items, deals, and restaurants."""

from django.utils import timezone

from apps.engagement.models import ContentReport, ReportReason, ReportStatus, ReportTargetType
from apps.engagement.services.saved_service import _resolve_deal, _resolve_menu_item
from apps.restaurants.models import Restaurant
from core.exceptions import AppAPIException


def _resolve_restaurant(restaurant_id: int) -> Restaurant:
    try:
        restaurant = Restaurant.objects.get(pk=restaurant_id)
    except Restaurant.DoesNotExist:
        raise AppAPIException(
            code='RESTAURANT_NOT_FOUND',
            message='Restaurant not found.',
            status_code=404,
        )
    if restaurant.is_paused or restaurant.is_permanently_closed:
        raise AppAPIException(
            code='RESTAURANT_NOT_FOUND',
            message='Restaurant not found.',
            status_code=404,
        )
    return restaurant


def serialize_report(report: ContentReport) -> dict:
    restaurant = report.restaurant
    title = None
    if report.target_type == ReportTargetType.ITEM and report.menu_item_id:
        title = report.menu_item.name
    elif report.target_type == ReportTargetType.DEAL and report.deal_id:
        title = report.deal.label
    elif restaurant is not None:
        title = restaurant.name
    return {
        'id': report.id,
        'target_type': report.target_type,
        'menu_item_id': report.menu_item_id,
        'deal_id': report.deal_id,
        'restaurant_id': report.restaurant_id,
        'restaurant_name': restaurant.name if restaurant else None,
        'reason': report.reason,
        'description': report.description,
        'status': report.status,
        'created_by': report.created_by_id,
        'created_at': report.created_at.isoformat() if report.created_at else None,
        'title': title,
    }


_REPORT_RELATIONS = (
    'created_by',
    'restaurant',
    'menu_item',
    'menu_item__restaurant',
    'deal',
    'deal__restaurant',
    'reviewed_by',
)


class ReportService:
    def create(self, *, user, target_type: str, resource_id: int, reason: str, description: str = ''):
        if reason not in ReportReason.values:
            raise AppAPIException(
                code='INVALID_REPORT_REASON',
                message='Invalid report reason.',
                status_code=400,
            )
        description = (description or '').strip()
        if target_type == ReportTargetType.ITEM:
            item = _resolve_menu_item(int(resource_id))
            if ContentReport.objects.filter(created_by=user, menu_item=item).exists():
                raise AppAPIException(
                    code='REPORT_EXISTS',
                    message='You have already reported this item.',
                    status_code=409,
                )
            report = ContentReport.objects.create(
                created_by=user,
                target_type=ReportTargetType.ITEM,
                restaurant=item.restaurant,
                menu_item=item,
                deal=None,
                reason=reason,
                description=description,
            )
            return self.get_admin(report_id=report.id)

        if target_type == ReportTargetType.DEAL:
            deal = _resolve_deal(int(resource_id))
            if ContentReport.objects.filter(created_by=user, deal=deal).exists():
                raise AppAPIException(
                    code='REPORT_EXISTS',
                    message='You have already reported this deal.',
                    status_code=409,
                )
            report = ContentReport.objects.create(
                created_by=user,
                target_type=ReportTargetType.DEAL,
                restaurant=deal.restaurant,
                menu_item=None,
                deal=deal,
                reason=reason,
                description=description,
            )
            return self.get_admin(report_id=report.id)

        if target_type == ReportTargetType.RESTAURANT:
            restaurant = _resolve_restaurant(int(resource_id))
            if ContentReport.objects.filter(
                created_by=user,
                restaurant=restaurant,
                target_type=ReportTargetType.RESTAURANT,
            ).exists():
                raise AppAPIException(
                    code='REPORT_EXISTS',
                    message='You have already reported this restaurant.',
                    status_code=409,
                )
            report = ContentReport.objects.create(
                created_by=user,
                target_type=ReportTargetType.RESTAURANT,
                restaurant=restaurant,
                menu_item=None,
                deal=None,
                reason=reason,
                description=description,
            )
            return self.get_admin(report_id=report.id)

        raise AppAPIException(
            code='INVALID_TARGET_TYPE',
            message='target_type must be item, deal, or restaurant.',
            status_code=400,
        )

    def list_admin(
        self,
        *,
        status_filter: str | None = None,
        target_type: str | None = None,
        restaurant_id: int | None = None,
    ):
        qs = ContentReport.objects.select_related(*_REPORT_RELATIONS).order_by('created_at')
        if status_filter:
            if status_filter not in ReportStatus.values:
                raise AppAPIException(
                    code='INVALID_REPORT_STATUS',
                    message='status must be open, actioned, or dismissed.',
                    status_code=400,
                )
            qs = qs.filter(status=status_filter)
        else:
            qs = qs.filter(status=ReportStatus.OPEN)
        if target_type:
            if target_type not in ReportTargetType.values:
                raise AppAPIException(
                    code='INVALID_TARGET_TYPE',
                    message='target_type must be item, deal, or restaurant.',
                    status_code=400,
                )
            qs = qs.filter(target_type=target_type)
        if restaurant_id is not None:
            try:
                qs = qs.filter(restaurant_id=int(restaurant_id))
            except (TypeError, ValueError):
                raise AppAPIException(
                    code='INVALID_RESTAURANT_ID',
                    message='restaurant_id must be an integer.',
                    status_code=400,
                )
        return qs

    def get_admin(self, *, report_id: int) -> ContentReport:
        try:
            return ContentReport.objects.select_related(*_REPORT_RELATIONS).get(pk=report_id)
        except ContentReport.DoesNotExist:
            raise AppAPIException(
                code='REPORT_NOT_FOUND',
                message='Report not found.',
                status_code=404,
            )

    def _target_count(self, report: ContentReport) -> int:
        if report.target_type == ReportTargetType.ITEM and report.menu_item_id:
            return ContentReport.objects.filter(menu_item_id=report.menu_item_id).count()
        if report.target_type == ReportTargetType.DEAL and report.deal_id:
            return ContentReport.objects.filter(deal_id=report.deal_id).count()
        return ContentReport.objects.filter(
            restaurant_id=report.restaurant_id,
            target_type=ReportTargetType.RESTAURANT,
        ).count()

    def serialize_admin(self, report: ContentReport) -> dict:
        data = serialize_report(report)
        data['report_count'] = self._target_count(report)
        data['created_by_phone'] = (
            report.created_by.phone_number if report.created_by_id else None
        )
        data['reviewed_by'] = report.reviewed_by_id
        data['reviewed_at'] = report.reviewed_at.isoformat() if report.reviewed_at else None
        data['admin_note'] = report.admin_note
        if report.created_at:
            age_seconds = (timezone.now() - report.created_at).total_seconds()
            data['age_minutes'] = int(age_seconds // 60)
        else:
            data['age_minutes'] = None
        return data

    def action(self, *, report_id: int, admin_user, admin_note: str = '') -> ContentReport:
        report = self.get_admin(report_id=report_id)
        report.status = ReportStatus.ACTIONED
        report.reviewed_by = admin_user
        report.reviewed_at = timezone.now()
        if admin_note:
            report.admin_note = admin_note
        report.save(
            update_fields=['status', 'reviewed_by', 'reviewed_at', 'admin_note']
        )
        return report

    def dismiss(self, *, report_id: int, admin_user, admin_note: str = '') -> ContentReport:
        report = self.get_admin(report_id=report_id)
        report.status = ReportStatus.DISMISSED
        report.reviewed_by = admin_user
        report.reviewed_at = timezone.now()
        if admin_note:
            report.admin_note = admin_note
        report.save(
            update_fields=['status', 'reviewed_by', 'reviewed_at', 'admin_note']
        )
        return report
