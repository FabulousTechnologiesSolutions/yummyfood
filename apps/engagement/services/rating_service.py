"""Customer ratings for menu items, deals, and restaurants."""

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Avg, Count

from apps.engagement.models import Rating, RatingTargetType
from apps.engagement.services.saved_service import _resolve_deal, _resolve_menu_item
from apps.restaurants.models import Restaurant
from core.exceptions import AppAPIException

# Keep the old import path working
RestaurantRating = Rating


def serialize_rating(rating: Rating) -> dict:
    return {
        'id': rating.id,
        'target_type': rating.target_type,
        'restaurant_id': rating.restaurant_id,
        'menu_item_id': rating.menu_item_id,
        'deal_id': rating.deal_id,
        'stars': rating.stars,
        'description': rating.description,
        'rated_at': rating.rated_at.isoformat() if rating.rated_at else None,
        'updated_at': rating.updated_at.isoformat() if rating.updated_at else None,
        'created_by': rating.user_id,
    }


def _recompute_restaurant_aggregates(restaurant: Restaurant) -> None:
    """Recompute from restaurant-scope ratings only."""
    qs = restaurant.ratings.filter(target_type=RatingTargetType.RESTAURANT)
    stats = qs.aggregate(avg=Avg('stars'), count=Count('id'))
    count = stats['count'] or 0
    avg = stats['avg'] or 0
    histogram = {str(i): 0 for i in range(1, 6)}
    for stars in qs.values_list('stars', flat=True):
        key = str(int(stars))
        if key in histogram:
            histogram[key] += 1
    restaurant.rating_count = count
    restaurant.rating_avg = Decimal(str(avg)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
    restaurant.rating_histogram = histogram
    restaurant.save(update_fields=['rating_count', 'rating_avg', 'rating_histogram', 'updated_at'])


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


class RatingService:
    def _validate_stars(self, stars: int) -> None:
        if stars < 1 or stars > 5:
            raise AppAPIException(
                code='INVALID_STARS',
                message='stars must be between 1 and 5.',
                status_code=400,
            )

    # --- Restaurant ---

    def get_for_user(self, *, user, restaurant_id: int) -> Rating:
        restaurant = _resolve_restaurant(restaurant_id)
        try:
            return Rating.objects.get(
                user=user,
                restaurant=restaurant,
                target_type=RatingTargetType.RESTAURANT,
            )
        except Rating.DoesNotExist:
            raise AppAPIException(
                code='RATING_NOT_FOUND',
                message='You have not rated this restaurant.',
                status_code=404,
            )

    @transaction.atomic
    def upsert(self, *, user, restaurant_id: int, stars: int, description: str = '') -> tuple:
        self._validate_stars(stars)
        restaurant = _resolve_restaurant(restaurant_id)
        rating, created = Rating.objects.get_or_create(
            user=user,
            restaurant=restaurant,
            target_type=RatingTargetType.RESTAURANT,
            defaults={
                'stars': stars,
                'description': (description or '').strip(),
                'menu_item': None,
                'deal': None,
            },
        )
        if not created:
            rating.stars = stars
            rating.description = (description or '').strip()
            rating.save(update_fields=['stars', 'description', 'updated_at'])
        _recompute_restaurant_aggregates(restaurant)
        rating.refresh_from_db()
        return rating, created

    # --- Menu item ---

    def get_item_for_user(self, *, user, item_id: int) -> Rating:
        item = _resolve_menu_item(item_id)
        try:
            return Rating.objects.get(user=user, menu_item=item)
        except Rating.DoesNotExist:
            raise AppAPIException(
                code='RATING_NOT_FOUND',
                message='You have not rated this item.',
                status_code=404,
            )

    @transaction.atomic
    def upsert_item(self, *, user, item_id: int, stars: int, description: str = '') -> tuple:
        self._validate_stars(stars)
        item = _resolve_menu_item(item_id)
        rating, created = Rating.objects.get_or_create(
            user=user,
            menu_item=item,
            defaults={
                'target_type': RatingTargetType.ITEM,
                'restaurant': item.restaurant,
                'stars': stars,
                'description': (description or '').strip(),
                'deal': None,
            },
        )
        if not created:
            rating.stars = stars
            rating.description = (description or '').strip()
            rating.save(update_fields=['stars', 'description', 'updated_at'])
        rating.refresh_from_db()
        return rating, created

    # --- Deal ---

    def get_deal_for_user(self, *, user, deal_id: int) -> Rating:
        deal = _resolve_deal(deal_id)
        try:
            return Rating.objects.get(user=user, deal=deal)
        except Rating.DoesNotExist:
            raise AppAPIException(
                code='RATING_NOT_FOUND',
                message='You have not rated this deal.',
                status_code=404,
            )

    @transaction.atomic
    def upsert_deal(self, *, user, deal_id: int, stars: int, description: str = '') -> tuple:
        self._validate_stars(stars)
        deal = _resolve_deal(deal_id)
        rating, created = Rating.objects.get_or_create(
            user=user,
            deal=deal,
            defaults={
                'target_type': RatingTargetType.DEAL,
                'restaurant': deal.restaurant,
                'stars': stars,
                'description': (description or '').strip(),
                'menu_item': None,
            },
        )
        if not created:
            rating.stars = stars
            rating.description = (description or '').strip()
            rating.save(update_fields=['stars', 'description', 'updated_at'])
        rating.refresh_from_db()
        return rating, created
