from django.db import transaction

from apps.accounts.models import AppMode, CustomerProfile, User
from apps.accounts.services.auth_service import AuthService
from apps.accounts.services.preference_service import ALLOWED_PRICE
from apps.accounts.services.seeding import seed_customer_side, seed_restaurant_side
from apps.restaurants.services import RestaurantService
from core.auth import issue_tokens_for_user
from core.exceptions import AppAPIException
from core.utils import normalize_phone


class ProfileService:
    def __init__(self):
        self.auth_service = AuthService()
        self.restaurant_service = RestaurantService()

    def _require_restaurant(self, user: User):
        if not user.has_restaurant_profile:
            raise AppAPIException(
                code='RESTAURANT_REQUIRED',
                message='Restaurant profile required.',
                status_code=403,
            )
        return user.restaurant

    def serialize_owner_restaurant(self, restaurant, request=None) -> dict:
        return {
            'id': restaurant.id,
            'name': restaurant.name,
            'slug': restaurant.slug,
            'short_description': restaurant.short_description,
            'cuisines': restaurant.cuisines or [],
            'price_range': restaurant.price_range,
            'logo': self.restaurant_service.media_url(restaurant.logo, request=request),
            'cover': self.restaurant_service.media_url(restaurant.cover, request=request),
            'primary_phone': restaurant.primary_phone,
            'whatsapp_number': restaurant.whatsapp_number,
            'use_different_whatsapp': restaurant.use_different_whatsapp,
            'secondary_phone': restaurant.secondary_phone,
            'street_address': restaurant.street_address,
            'area': restaurant.area,
            'city_id': restaurant.city_id,
            'lat': str(restaurant.lat) if restaurant.lat is not None else None,
            'lng': str(restaurant.lng) if restaurant.lng is not None else None,
            'is_paused': restaurant.is_paused,
            'is_permanently_closed': restaurant.is_permanently_closed,
            'promo_default_radius_km': restaurant.promo_default_radius_km,
            'promo_default_duration_days': restaurant.promo_default_duration_days,
            'notify_on_promo_approval': restaurant.notify_on_promo_approval,
            'auto_request_promo_on_deal': restaurant.auto_request_promo_on_deal,
            'rating_avg': str(restaurant.rating_avg),
            'rating_count': restaurant.rating_count,
            'setup_completeness_pct': restaurant.setup_completeness_pct,
        }

    def get_restaurant_profile(self, *, user: User, request=None) -> dict:
        restaurant = self._require_restaurant(user)
        return self.serialize_owner_restaurant(restaurant, request=request)

    def update_restaurant_profile(self, *, user: User, data: dict, request=None) -> dict:
        restaurant = self._require_restaurant(user)
        update_fields = ['updated_at']

        if 'name' in data:
            name = (data['name'] or '').strip()
            if not name:
                raise AppAPIException(
                    code='RESTAURANT_NAME_REQUIRED',
                    message='name is required.',
                    status_code=400,
                )
            restaurant.name = name
            update_fields.append('name')

        if 'short_description' in data:
            restaurant.short_description = data['short_description'] or ''
            update_fields.append('short_description')

        if 'cuisines' in data:
            cuisines = data['cuisines'] or []
            restaurant.cuisines = [c.strip() for c in cuisines if (c or '').strip()]
            update_fields.append('cuisines')

        if 'price_range' in data:
            price = data['price_range'] or ''
            if price and price not in ALLOWED_PRICE:
                raise AppAPIException(
                    code='INVALID_PRICE_RANGE',
                    message='Invalid price_range value.',
                    status_code=400,
                )
            restaurant.price_range = price
            update_fields.append('price_range')

        for phone_field in ('primary_phone', 'whatsapp_number', 'secondary_phone'):
            if phone_field in data:
                raw = data[phone_field]
                if raw in (None, ''):
                    setattr(restaurant, phone_field, '')
                else:
                    setattr(restaurant, phone_field, normalize_phone(raw))
                update_fields.append(phone_field)

        if 'use_different_whatsapp' in data:
            restaurant.use_different_whatsapp = bool(data['use_different_whatsapp'])
            update_fields.append('use_different_whatsapp')

        for text_field in ('street_address', 'area'):
            if text_field in data:
                setattr(restaurant, text_field, data[text_field] or '')
                update_fields.append(text_field)

        if 'city_id' in data:
            restaurant.city_id = data['city_id']
            update_fields.append('city_id')

        if 'lat' in data:
            restaurant.lat = data['lat']
            update_fields.append('lat')
        if 'lng' in data:
            restaurant.lng = data['lng']
            update_fields.append('lng')

        if ('lat' in data) ^ ('lng' in data):
            # Allow clearing both; if only one provided, require the other currently set
            if restaurant.lat is None or restaurant.lng is None:
                raise AppAPIException(
                    code='INVALID_COORDINATES',
                    message='Both lat and lng are required together.',
                    status_code=400,
                )

        if 'is_paused' in data:
            restaurant.is_paused = bool(data['is_paused'])
            update_fields.append('is_paused')

        if 'promo_default_radius_km' in data:
            restaurant.promo_default_radius_km = data['promo_default_radius_km']
            update_fields.append('promo_default_radius_km')
        if 'promo_default_duration_days' in data:
            restaurant.promo_default_duration_days = data['promo_default_duration_days']
            update_fields.append('promo_default_duration_days')
        if 'notify_on_promo_approval' in data:
            restaurant.notify_on_promo_approval = bool(data['notify_on_promo_approval'])
            update_fields.append('notify_on_promo_approval')
        if 'auto_request_promo_on_deal' in data:
            restaurant.auto_request_promo_on_deal = bool(data['auto_request_promo_on_deal'])
            update_fields.append('auto_request_promo_on_deal')

        restaurant.save(update_fields=list(dict.fromkeys(update_fields)))
        restaurant.refresh_from_db()
        return self.serialize_owner_restaurant(restaurant, request=request)

    def list_profiles(self, user: User) -> dict:
        data = {
            'customer': user.has_customer_profile,
            'restaurant': user.has_restaurant_profile,
        }
        if user.has_restaurant_profile:
            data['restaurant_id'] = user.restaurant.id
        return data

    def console_access(self, user: User) -> dict:
        if not user.has_restaurant_profile:
            return {'can_switch': False, 'restaurant': None}
        restaurant = user.restaurant
        return {
            'can_switch': True,
            'restaurant': {
                'id': restaurant.id,
                'name': restaurant.name,
                'setup_completeness_pct': restaurant.setup_completeness_pct,
            },
        }

    @transaction.atomic
    def add_customer_profile(self, user: User) -> dict:
        if user.has_customer_profile:
            raise AppAPIException(
                code='CUSTOMER_PROFILE_EXISTS',
                message='Customer profile already exists.',
                status_code=409,
            )
        profile = CustomerProfile.objects.create(user=user)
        seed_customer_side(profile)
        return self.auth_service.me(user)

    @transaction.atomic
    def add_restaurant(self, *, user: User, name: str) -> dict:
        if not (name or '').strip():
            raise AppAPIException(
                code='RESTAURANT_NAME_REQUIRED',
                message='name is required.',
                status_code=400,
            )
        restaurant = self.restaurant_service.create_shell(owner=user, name=name.strip())
        seed_restaurant_side(restaurant)
        user.active_mode = AppMode.RESTAURANT
        user.last_active_mode = AppMode.RESTAURANT
        user.save(update_fields=['active_mode', 'last_active_mode'])
        payload = self.auth_service.me(user)
        payload['tokens'] = issue_tokens_for_user(user)
        return payload

    def update_restaurant_branding(
        self, *, user: User, branding_type: str, image, request=None
    ) -> dict:
        if not user.has_restaurant_profile:
            raise AppAPIException(
                code='RESTAURANT_REQUIRED',
                message='Restaurant profile required.',
                status_code=403,
            )
        if branding_type not in ('cover', 'logo'):
            raise AppAPIException(
                code='INVALID_BRANDING_TYPE',
                message='type must be cover or logo.',
                status_code=400,
            )
        restaurant = user.restaurant
        field_name = branding_type
        previous = getattr(restaurant, field_name)
        setattr(restaurant, field_name, image)
        restaurant.save(update_fields=[field_name, 'updated_at'])
        if previous:
            previous.delete(save=False)
        restaurant.refresh_from_db()
        return {
            'type': branding_type,
            'restaurant': {
                'id': restaurant.id,
                'name': restaurant.name,
                'logo': self.restaurant_service.media_url(restaurant.logo, request=request),
                'cover': self.restaurant_service.media_url(restaurant.cover, request=request),
                'setup_completeness_pct': restaurant.setup_completeness_pct,
            },
        }

    @transaction.atomic
    def switch_to_customer(self, user: User) -> dict:
        if not user.has_customer_profile:
            profile = CustomerProfile.objects.create(user=user)
            seed_customer_side(profile)
        user.active_mode = AppMode.CUSTOMER
        user.last_active_mode = AppMode.CUSTOMER
        user.save(update_fields=['active_mode', 'last_active_mode'])
        payload = self.auth_service.me(user)
        payload['tokens'] = issue_tokens_for_user(user)
        return payload

    @transaction.atomic
    def switch_to_restaurant(self, *, user: User, restaurant_name: str | None = None) -> dict:
        needs_profile_update = False
        if not user.has_restaurant_profile:
            name = (restaurant_name or '').strip()
            if not name:
                name = (user.display_name or '').strip() or 'My Restaurant'
            restaurant = self.restaurant_service.create_shell(owner=user, name=name)
            seed_restaurant_side(restaurant)
            # True only on this first create so FE can open Restaurant Profile once.
            needs_profile_update = True

        user.active_mode = AppMode.RESTAURANT
        user.last_active_mode = AppMode.RESTAURANT
        user.save(update_fields=['active_mode', 'last_active_mode'])
        payload = self.auth_service.me(user)
        payload['tokens'] = issue_tokens_for_user(user)
        payload['needs_profile_update'] = needs_profile_update
        return payload
