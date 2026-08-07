from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.mediahub.services import MediaAttachService, serialize_media
from apps.restaurants.models import Deal, DealLine, DealStatus, MenuItem
from core.exceptions import AppAPIException


def serialize_deal_line(line: DealLine) -> dict:
    return {
        'id': line.id,
        'menu_item_id': line.menu_item_id,
        'menu_item_name': line.menu_item.name if line.menu_item_id else None,
        'size_label': line.size_label,
        'unit_price': str(line.unit_price),
        'quantity': line.quantity,
        'position': line.position,
    }


def serialize_deal(deal: Deal, *, include_media: bool = True) -> dict:
    data = {
        'id': deal.id,
        'restaurant_id': deal.restaurant_id,
        'label': deal.label,
        'description': deal.description,
        'deal_price': str(deal.deal_price),
        'items_total': str(deal.items_total),
        'savings_amount': str(deal.savings_amount),
        'savings_percent': str(deal.savings_percent),
        'starts_at': deal.starts_at.isoformat() if deal.starts_at else None,
        'ends_at': deal.ends_at.isoformat() if deal.ends_at else None,
        'days_of_week': deal.days_of_week or [],
        'terms': deal.terms,
        'status': deal.status,
        'is_promoted': deal.is_promoted,
        'promoted_starts_at': (
            deal.promoted_starts_at.isoformat() if deal.promoted_starts_at else None
        ),
        'promoted_ends_at': (
            deal.promoted_ends_at.isoformat() if deal.promoted_ends_at else None
        ),
        'lines': [serialize_deal_line(l) for l in deal.lines.select_related('menu_item').all()],
        'created_at': deal.created_at.isoformat() if deal.created_at else None,
        'updated_at': deal.updated_at.isoformat() if deal.updated_at else None,
    }
    if include_media:
        data['media'] = [serialize_media(m) for m in deal.media.all()]
    return data


class DealService:
    def _get(self, *, restaurant, deal_id) -> Deal:
        try:
            return (
                Deal.objects.select_related('restaurant')
                .prefetch_related('lines__menu_item', 'media')
                .get(id=deal_id, restaurant=restaurant)
            )
        except Deal.DoesNotExist:
            raise AppAPIException(
                code='DEAL_NOT_FOUND',
                message='Deal not found.',
                status_code=404,
            )

    def _compute_totals(self, lines: list, deal_price: Decimal) -> tuple[Decimal, Decimal, Decimal]:
        items_total = sum(
            (Decimal(str(l['unit_price'])) * int(l.get('quantity') or 1) for l in lines),
            Decimal('0'),
        )
        if deal_price >= items_total:
            raise AppAPIException(
                code='INVALID_DEAL_PRICE',
                message='deal_price must be less than items_total.',
                status_code=400,
                details={'items_total': str(items_total)},
            )
        savings_amount = items_total - deal_price
        savings_percent = (
            (savings_amount / items_total * Decimal('100')).quantize(Decimal('0.01'))
            if items_total
            else Decimal('0')
        )
        return items_total, savings_amount, savings_percent

    def _validate_lines(self, *, restaurant, lines: list) -> None:
        if not lines:
            raise AppAPIException(
                code='LINES_REQUIRED',
                message='At least one deal line is required.',
                status_code=400,
            )
        item_ids = [l['menu_item_id'] for l in lines]
        found = set(
            MenuItem.objects.filter(restaurant=restaurant, id__in=item_ids).values_list('id', flat=True)
        )
        missing = set(item_ids) - found
        if missing:
            raise AppAPIException(
                code='MENU_ITEM_NOT_FOUND',
                message='One or more menu items were not found on this restaurant.',
                status_code=404,
                details={'missing_ids': list(missing)},
            )

    def _replace_lines(self, deal: Deal, lines: list) -> None:
        deal.lines.all().delete()
        for position, line in enumerate(lines):
            DealLine.objects.create(
                deal=deal,
                menu_item_id=line['menu_item_id'],
                size_label=str(line['size_label']).strip(),
                unit_price=Decimal(str(line['unit_price'])),
                quantity=int(line.get('quantity') or 1),
                position=line.get('position', position),
            )

    def list(self, *, restaurant, segment: str = 'active'):
        now = timezone.now()
        qs = (
            Deal.objects.filter(restaurant=restaurant)
            .prefetch_related('lines__menu_item', 'media')
            .order_by('-created_at')
        )
        if segment == 'active':
            qs = qs.filter(status=DealStatus.ACTIVE, starts_at__lte=now, ends_at__gte=now)
        elif segment == 'pending':
            # Reserved for promotions — empty until promotions app
            qs = qs.none()
        elif segment == 'ended':
            qs = qs.filter(Q(status=DealStatus.ENDED) | Q(ends_at__lt=now))
        elif segment:
            raise AppAPIException(
                code='INVALID_SEGMENT',
                message='segment must be active, pending, or ended.',
                status_code=400,
            )
        return list(qs)

    def get(self, *, restaurant, deal_id) -> Deal:
        return self._get(restaurant=restaurant, deal_id=deal_id)

    def preview(self, *, restaurant, deal_id) -> dict:
        deal = self._get(restaurant=restaurant, deal_id=deal_id)
        payload = serialize_deal(deal)
        payload['preview'] = True
        return payload

    @transaction.atomic
    def create(self, *, restaurant, data: dict) -> Deal:
        lines = data.get('lines') or []
        media_list = data.get('media') or []
        self._validate_lines(restaurant=restaurant, lines=lines)
        MediaAttachService().validate_payload(media_list)

        starts_at = data['starts_at']
        ends_at = data['ends_at']
        if ends_at <= starts_at:
            raise AppAPIException(
                code='INVALID_SCHEDULE',
                message='ends_at must be after starts_at.',
                status_code=400,
            )

        deal_price = Decimal(str(data['deal_price']))
        items_total, savings_amount, savings_percent = self._compute_totals(lines, deal_price)

        deal = Deal.objects.create(
            restaurant=restaurant,
            label=data['label'].strip(),
            description=(data.get('description') or '').strip(),
            deal_price=deal_price,
            items_total=items_total,
            savings_amount=savings_amount,
            savings_percent=savings_percent,
            starts_at=starts_at,
            ends_at=ends_at,
            days_of_week=data.get('days_of_week') or [],
            terms=(data.get('terms') or '').strip(),
            status=data.get('status') or DealStatus.ACTIVE,
        )
        self._replace_lines(deal, lines)
        MediaAttachService().sync_for_deal(
            restaurant=restaurant,
            deal=deal,
            media_list=media_list,
        )
        return self.get(restaurant=restaurant, deal_id=deal.id)

    @transaction.atomic
    def update(self, *, restaurant, deal_id, data: dict) -> Deal:
        deal = self._get(restaurant=restaurant, deal_id=deal_id)

        for field in ('label', 'description', 'terms'):
            if field in data and data[field] is not None:
                setattr(deal, field, str(data[field]).strip())
        if 'status' in data and data['status']:
            deal.status = data['status']
        if 'days_of_week' in data and data['days_of_week'] is not None:
            deal.days_of_week = data['days_of_week']
        if 'starts_at' in data and data['starts_at'] is not None:
            deal.starts_at = data['starts_at']
        if 'ends_at' in data and data['ends_at'] is not None:
            deal.ends_at = data['ends_at']
        if deal.ends_at <= deal.starts_at:
            raise AppAPIException(
                code='INVALID_SCHEDULE',
                message='ends_at must be after starts_at.',
                status_code=400,
            )

        lines = data.get('lines')
        if lines is not None:
            self._validate_lines(restaurant=restaurant, lines=lines)
            self._replace_lines(deal, lines)

        deal_price = (
            Decimal(str(data['deal_price']))
            if 'deal_price' in data and data['deal_price'] is not None
            else deal.deal_price
        )
        current_lines = lines if lines is not None else [
            {
                'menu_item_id': l.menu_item_id,
                'size_label': l.size_label,
                'unit_price': l.unit_price,
                'quantity': l.quantity,
            }
            for l in deal.lines.all()
        ]
        items_total, savings_amount, savings_percent = self._compute_totals(
            current_lines, deal_price
        )
        deal.deal_price = deal_price
        deal.items_total = items_total
        deal.savings_amount = savings_amount
        deal.savings_percent = savings_percent
        deal.save()

        if 'media' in data and data['media'] is not None:
            MediaAttachService().sync_for_deal(
                restaurant=restaurant,
                deal=deal,
                media_list=data['media'],
            )

        return self.get(restaurant=restaurant, deal_id=deal.id)

    @transaction.atomic
    def delete(self, *, restaurant, deal_id) -> None:
        deal = self._get(restaurant=restaurant, deal_id=deal_id)
        for media in list(deal.media.all()):
            from apps.mediahub.services import UploadService

            UploadService().delete_media(restaurant=restaurant, media_id=media.id)
        deal.delete()

    def get_public(self, deal_id) -> Deal:
        try:
            return (
                Deal.objects.select_related('restaurant')
                .prefetch_related('lines__menu_item', 'media')
                .get(id=deal_id, status=DealStatus.ACTIVE)
            )
        except Deal.DoesNotExist:
            raise AppAPIException(
                code='DEAL_NOT_FOUND',
                message='Deal not found.',
                status_code=404,
            )
