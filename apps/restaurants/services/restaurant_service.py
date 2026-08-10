from django.db import transaction
from django.utils import timezone

from apps.restaurants.models import (
    ClaimStatus,
    Deal,
    DealStatus,
    MenuCategory,
    MenuItem,
    MenuItemStatus,
    Restaurant,
)
from apps.restaurants.services.category_service import serialize_category
from apps.restaurants.services.deal_service import serialize_deal
from apps.restaurants.services.menu_item_service import serialize_menu_item
from apps.restaurants.services.seeding import seed_default_categories
from core.exceptions import AppAPIException


def _media_url(field, request=None) -> str | None:
    if not field:
        return None
    try:
        url = field.url
    except Exception:
        return None
    if not url:
        return None
    if url.startswith(('http://', 'https://')):
        return url
    if request is not None:
        return request.build_absolute_uri(url)
    return url


def serialize_restaurant_public(restaurant: Restaurant, request=None) -> dict:
    return {
        'id': restaurant.id,
        'name': restaurant.name,
        'slug': restaurant.slug,
        'short_description': restaurant.short_description,
        'cuisines': restaurant.cuisines or [],
        'price_range': restaurant.price_range,
        'logo': _media_url(restaurant.logo, request=request),
        'cover': _media_url(restaurant.cover, request=request),
        'primary_phone': restaurant.primary_phone,
        'whatsapp_number': restaurant.whatsapp_number,
        'street_address': restaurant.street_address,
        'area': restaurant.area,
        'city_id': restaurant.city_id,
        'lat': str(restaurant.lat) if restaurant.lat is not None else None,
        'lng': str(restaurant.lng) if restaurant.lng is not None else None,
        'rating_avg': str(restaurant.rating_avg),
        'rating_count': restaurant.rating_count,
        'is_paused': restaurant.is_paused,
    }


class RestaurantService:
    media_url = staticmethod(_media_url)

    @transaction.atomic
    def create_shell(self, *, owner, name: str) -> Restaurant:
        if Restaurant.objects.filter(owner=owner).exists():
            raise AppAPIException(
                code='RESTAURANT_PROFILE_EXISTS',
                message='You already have a restaurant profile.',
                status_code=409,
            )
        restaurant = Restaurant.objects.create(
            owner=owner,
            name=name.strip(),
            slug=Restaurant.make_unique_slug(name),
            claim_status=ClaimStatus.OWNED,
            primary_phone=getattr(owner, 'phone_number', '') or '',
        )
        seed_default_categories()
        return restaurant

    def public_profile(self, restaurant_id, request=None) -> dict:
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id)
        except Restaurant.DoesNotExist:
            raise AppAPIException(
                code='RESTAURANT_NOT_FOUND',
                message='Restaurant not found.',
                status_code=404,
            )

        categories = MenuCategory.objects.filter(is_visible=True).order_by('position')

        items = (
            MenuItem.objects.filter(
                restaurant=restaurant,
                status=MenuItemStatus.PUBLISHED,
            )
            .select_related('restaurant')
            .prefetch_related('sizes', 'categories', 'media')
        )

        now = timezone.now()
        deals = (
            Deal.objects.filter(
                restaurant=restaurant,
                status=DealStatus.ACTIVE,
                starts_at__lte=now,
                ends_at__gte=now,
            )
            .prefetch_related('lines__menu_item', 'media')
            .order_by('-created_at')
        )

        return {
            'restaurant': serialize_restaurant_public(restaurant, request=request),
            'categories': [serialize_category(c) for c in categories],
            'menu_items': [serialize_menu_item(i) for i in items],
            'deals': [serialize_deal(d) for d in deals],
        }
