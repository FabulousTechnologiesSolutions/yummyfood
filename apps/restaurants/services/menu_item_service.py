from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.mediahub.services import MediaAttachService, serialize_media
from apps.restaurants.models import MenuCategory, MenuItem, MenuItemSize, MenuItemStatus
from apps.restaurants.services.category_service import serialize_category
from core.exceptions import AppAPIException


def _effective_size_price(size: MenuItemSize) -> Decimal:
    if size.offer_price is not None:
        return size.offer_price
    return size.price


def serialize_size(size: MenuItemSize) -> dict:
    return {
        'id': size.id,
        'label': size.label,
        'price': str(size.price),
        'offer_price': str(size.offer_price) if size.offer_price is not None else None,
        'position': size.position,
    }


def serialize_menu_item(item: MenuItem, *, include_media: bool = True) -> dict:
    cats = list(item.categories.all())
    data = {
        'id': item.id,
        'restaurant_id': item.restaurant_id,
        'category_ids': [c.id for c in cats],
        'categories': [serialize_category(c) for c in cats],
        'name': item.name,
        'description': item.description,
        'subcategory': item.subcategory,
        'item_type': item.item_type,
        'quantity_label': item.quantity_label,
        'sku': item.sku,
        'is_available': item.is_available,
        'is_popular': item.is_popular,
        'is_new': item.is_new,
        'is_promoted': item.is_promoted,
        'promoted_starts_at': (
            item.promoted_starts_at.isoformat() if item.promoted_starts_at else None
        ),
        'promoted_ends_at': (
            item.promoted_ends_at.isoformat() if item.promoted_ends_at else None
        ),
        'spicy_level': item.spicy_level,
        'prep_time_min': item.prep_time_min,
        'calories': item.calories,
        'emoji': item.emoji,
        'base_price': str(item.base_price),
        'status': item.status,
        'published_at': item.published_at.isoformat() if item.published_at else None,
        'sizes': [serialize_size(s) for s in item.sizes.all()],
        'created_at': item.created_at.isoformat() if item.created_at else None,
        'updated_at': item.updated_at.isoformat() if item.updated_at else None,
    }
    if include_media:
        data['media'] = [serialize_media(m) for m in item.media.all()]
    return data


class MenuItemService:
    def _get_restaurant_owned(self, restaurant, item_id) -> MenuItem:
        try:
            return (
                MenuItem.objects.select_related('restaurant')
                .prefetch_related('sizes', 'categories', 'media')
                .get(id=item_id, restaurant=restaurant)
            )
        except MenuItem.DoesNotExist:
            raise AppAPIException(
                code='MENU_ITEM_NOT_FOUND',
                message='Menu item not found.',
                status_code=404,
            )

    def list(self, *, restaurant):
        return list(
            MenuItem.objects.filter(restaurant=restaurant)
            .select_related('restaurant')
            .prefetch_related('sizes', 'categories', 'media')
        )

    def get(self, *, restaurant, item_id) -> MenuItem:
        return self._get_restaurant_owned(restaurant, item_id)

    def _check_quota(self, restaurant) -> None:
        limit = int(getattr(settings, 'FREE_TIER_PRODUCTS_PER_MONTH', 5))
        today = date.today()
        month_start = today.replace(day=1)
        if restaurant.products_quota_month != month_start:
            restaurant.products_created_this_month = 0
            restaurant.products_quota_month = month_start
            restaurant.save(update_fields=['products_created_this_month', 'products_quota_month'])
        if restaurant.products_created_this_month >= limit:
            raise AppAPIException(
                code='PRODUCT_QUOTA_EXCEEDED',
                message=f'Free plan allows {limit} products per month.',
                status_code=403,
                details={'limit': limit, 'used': restaurant.products_created_this_month},
            )

    def _validate_sizes(self, sizes: list) -> None:
        if not sizes:
            raise AppAPIException(
                code='SIZES_REQUIRED',
                message='At least one size is required.',
                status_code=400,
            )
        for s in sizes:
            price = Decimal(str(s['price']))
            offer = s.get('offer_price')
            if offer is not None and offer != '':
                offer_dec = Decimal(str(offer))
                if offer_dec >= price:
                    raise AppAPIException(
                        code='INVALID_OFFER_PRICE',
                        message='offer_price must be less than price.',
                        status_code=400,
                    )

    def _resolve_categories(self, category_ids: list) -> list:
        if not category_ids:
            raise AppAPIException(
                code='CATEGORIES_REQUIRED',
                message='At least one category is required.',
                status_code=400,
            )
        found = list(MenuCategory.objects.filter(id__in=category_ids))
        found_ids = {c.id for c in found}
        missing = set(category_ids) - found_ids
        if missing:
            raise AppAPIException(
                code='CATEGORY_NOT_FOUND',
                message='One or more categories were not found.',
                status_code=404,
                details={'missing_ids': list(missing)},
            )
        # Preserve request order
        by_id = {c.id: c for c in found}
        return [by_id[cid] for cid in category_ids]

    def _next_sku(self, restaurant) -> str:
        count = MenuItem.objects.filter(restaurant=restaurant).count() + 1
        return f'FA-{count:03d}'

    def _replace_sizes(self, item: MenuItem, sizes: list) -> None:
        item.sizes.all().delete()
        for position, s in enumerate(sizes):
            offer = s.get('offer_price')
            offer_price = Decimal(str(offer)) if offer not in (None, '') else None
            MenuItemSize.objects.create(
                menu_item=item,
                label=s['label'].strip(),
                price=Decimal(str(s['price'])),
                offer_price=offer_price,
                position=s.get('position', position),
            )
        prices = [_effective_size_price(sz) for sz in item.sizes.all()]
        item.base_price = min(prices) if prices else Decimal('0')
        item.save(update_fields=['base_price', 'updated_at'])

    @transaction.atomic
    def create(self, *, restaurant, data: dict) -> MenuItem:
        self._check_quota(restaurant)
        sizes = data.get('sizes') or []
        media_list = data.get('media') or []
        self._validate_sizes(sizes)
        MediaAttachService().validate_payload(media_list)

        categories = self._resolve_categories(data.get('category_ids') or [])
        sku = (data.get('sku') or '').strip() or self._next_sku(restaurant)

        spicy = data.get('spicy_level')
        if spicy is not None and spicy != '':
            spicy = int(spicy)
            if spicy < 0 or spicy > 3:
                raise AppAPIException(
                    code='INVALID_SPICY_LEVEL',
                    message='spicy_level must be 0–3.',
                    status_code=400,
                )
        else:
            spicy = None

        item = MenuItem.objects.create(
            restaurant=restaurant,
            name=data['name'].strip(),
            description=(data.get('description') or '').strip(),
            subcategory=(data.get('subcategory') or '').strip(),
            item_type=(data.get('item_type') or '').strip(),
            quantity_label=(data.get('quantity_label') or '').strip(),
            sku=sku,
            is_available=data.get('is_available', True),
            is_popular=data.get('is_popular', False),
            is_new=data.get('is_new', False),
            spicy_level=spicy,
            prep_time_min=data.get('prep_time_min'),
            calories=data.get('calories'),
            emoji=(data.get('emoji') or '').strip(),
            status=MenuItemStatus.PUBLISHED,
            published_at=timezone.now(),
        )
        item.categories.set(categories)

        self._replace_sizes(item, sizes)
        MediaAttachService().sync_for_menu_item(
            restaurant=restaurant,
            menu_item=item,
            media_list=media_list,
        )

        restaurant.products_created_this_month += 1
        restaurant.save(update_fields=['products_created_this_month', 'updated_at'])

        return self.get(restaurant=restaurant, item_id=item.id)

    @transaction.atomic
    def update(self, *, restaurant, item_id, data: dict) -> MenuItem:
        item = self._get_restaurant_owned(restaurant, item_id)

        for field in (
            'name', 'description', 'subcategory', 'item_type', 'quantity_label',
            'sku', 'emoji',
        ):
            if field in data and data[field] is not None:
                setattr(item, field, str(data[field]).strip())
        for field in ('is_available', 'is_popular', 'is_new'):
            if field in data and data[field] is not None:
                setattr(item, field, data[field])
        if 'spicy_level' in data:
            spicy = data['spicy_level']
            item.spicy_level = None if spicy in (None, '') else int(spicy)
        if 'prep_time_min' in data:
            item.prep_time_min = data['prep_time_min']
        if 'calories' in data:
            item.calories = data['calories']
        if 'status' in data and data['status']:
            item.status = data['status']
            if item.status == MenuItemStatus.PUBLISHED and not item.published_at:
                item.published_at = timezone.now()
        item.save()

        if 'category_ids' in data and data['category_ids'] is not None:
            categories = self._resolve_categories(data['category_ids'])
            item.categories.set(categories)

        if 'sizes' in data and data['sizes'] is not None:
            self._validate_sizes(data['sizes'])
            self._replace_sizes(item, data['sizes'])

        if 'media' in data and data['media'] is not None:
            MediaAttachService().sync_for_menu_item(
                restaurant=restaurant,
                menu_item=item,
                media_list=data['media'],
            )

        return self.get(restaurant=restaurant, item_id=item.id)

    @transaction.atomic
    def delete(self, *, restaurant, item_id) -> None:
        item = self._get_restaurant_owned(restaurant, item_id)
        for media in list(item.media.all()):
            from apps.mediahub.services import UploadService

            UploadService().delete_media(restaurant=restaurant, media_id=media.id)
        item.delete()

    @transaction.atomic
    def duplicate(self, *, restaurant, item_id) -> MenuItem:
        self._check_quota(restaurant)
        src = self._get_restaurant_owned(restaurant, item_id)
        sizes = [
            {
                'label': s.label,
                'price': s.price,
                'offer_price': s.offer_price,
                'position': s.position,
            }
            for s in src.sizes.all()
        ]
        media_list = [
            {
                'type': m.media_type,
                'url': m.file.name if m.file else '',
                'is_cover': m.is_cover,
            }
            for m in src.media.all()
        ]
        data = {
            'category_ids': list(src.categories.values_list('id', flat=True)),
            'name': f'{src.name} (copy)',
            'description': src.description,
            'subcategory': src.subcategory,
            'item_type': src.item_type,
            'quantity_label': src.quantity_label,
            'sku': '',
            'is_available': src.is_available,
            'is_popular': False,
            'is_new': True,
            'spicy_level': src.spicy_level,
            'prep_time_min': src.prep_time_min,
            'calories': src.calories,
            'emoji': src.emoji,
            'sizes': sizes,
            'media': media_list,
        }
        return self.create(restaurant=restaurant, data=data)

    @transaction.atomic
    def move(self, *, restaurant, item_id, category_id) -> MenuItem:
        item = self._get_restaurant_owned(restaurant, item_id)
        categories = self._resolve_categories([category_id])
        item.categories.set(categories)
        return self.get(restaurant=restaurant, item_id=item.id)

    @transaction.atomic
    def hide(self, *, restaurant, item_id) -> MenuItem:
        item = self._get_restaurant_owned(restaurant, item_id)
        item.status = MenuItemStatus.HIDDEN
        item.save(update_fields=['status', 'updated_at'])
        return self.get(restaurant=restaurant, item_id=item.id)

    @transaction.atomic
    def set_availability(self, *, restaurant, item_id, is_available: bool) -> MenuItem:
        item = self._get_restaurant_owned(restaurant, item_id)
        item.is_available = is_available
        item.save(update_fields=['is_available', 'updated_at'])
        return self.get(restaurant=restaurant, item_id=item.id)

    def get_public(self, item_id) -> MenuItem:
        try:
            return (
                MenuItem.objects.select_related('restaurant')
                .prefetch_related('sizes', 'categories', 'media')
                .get(id=item_id, status=MenuItemStatus.PUBLISHED)
            )
        except MenuItem.DoesNotExist:
            raise AppAPIException(
                code='MENU_ITEM_NOT_FOUND',
                message='Menu item not found.',
                status_code=404,
            )
