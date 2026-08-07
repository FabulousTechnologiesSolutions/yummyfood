from django.db import transaction

from apps.accounts.models import AppMode, CustomerProfile, User
from apps.accounts.services.auth_service import AuthService
from apps.accounts.services.seeding import seed_customer_side, seed_restaurant_side
from apps.restaurants.services import RestaurantService
from core.auth import issue_tokens_for_user
from core.exceptions import AppAPIException


class ProfileService:
    def __init__(self):
        self.auth_service = AuthService()
        self.restaurant_service = RestaurantService()

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
