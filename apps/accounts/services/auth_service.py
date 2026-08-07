from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import (
    AppMode,
    CustomerProfile,
    GuestSession,
    SignupIntent,
    User,
)
from apps.accounts.services.seeding import seed_customer_side, seed_restaurant_side
from apps.restaurants.services import RestaurantService
from core.auth import issue_tokens_for_user
from core.exceptions import AppAPIException
from core.utils import normalize_phone


class AuthService:
    def __init__(self):
        self.restaurant_service = RestaurantService()

    def _me_payload(self, user: User) -> dict:
        restaurant_data = None
        if user.has_restaurant_profile:
            restaurant = user.restaurant
            restaurant_data = {
                'id': restaurant.id,
                'name': restaurant.name,
                'setup_completeness_pct': restaurant.setup_completeness_pct,
            }
        return {
            'id': user.id,
            'phone_number': user.phone_number,
            'display_name': user.display_name or None,
            'active_mode': user.active_mode,
            'profiles': {
                'customer': user.has_customer_profile,
                'restaurant': user.has_restaurant_profile,
                'platform_admin': bool(user.is_staff),
            },
            'restaurant': restaurant_data,
        }

    def auth_response(self, user: User) -> dict:
        payload = self._me_payload(user)
        payload['tokens'] = issue_tokens_for_user(user)
        return payload

    def me(self, user: User) -> dict:
        return self._me_payload(user)

    @transaction.atomic
    def register(
        self,
        *,
        phone_number: str,
        password: str,
        signup_intent: str,
        restaurant_name: str | None = None,
        session_key: str | None = None,
    ) -> dict:
        phone = normalize_phone(phone_number)
        if User.objects.filter(phone_number=phone).exists():
            raise AppAPIException(
                code='PHONE_EXISTS',
                message='An account with this phone number already exists.',
                status_code=409,
            )
        if len(password) < 8:
            raise AppAPIException(
                code='INVALID_PASSWORD',
                message='Password must be at least 8 characters.',
                status_code=400,
            )
        if signup_intent not in (SignupIntent.CUSTOMER, SignupIntent.RESTAURANT):
            raise AppAPIException(
                code='INVALID_SIGNUP_INTENT',
                message='signup_intent must be customer or restaurant.',
                status_code=400,
            )
        if signup_intent == SignupIntent.RESTAURANT and not (restaurant_name or '').strip():
            raise AppAPIException(
                code='RESTAURANT_NAME_REQUIRED',
                message='restaurant_name is required for restaurant signup.',
                status_code=400,
            )

        mode = (
            AppMode.RESTAURANT
            if signup_intent == SignupIntent.RESTAURANT
            else AppMode.CUSTOMER
        )
        user = User.objects.create_user(
            phone_number=phone,
            password=password,
            signup_intent=signup_intent,
            active_mode=mode,
            last_active_mode=mode,
            terms_accepted_at=timezone.now(),
        )

        if signup_intent == SignupIntent.CUSTOMER:
            profile = CustomerProfile.objects.create(user=user)
            seed_customer_side(profile)
        else:
            restaurant = self.restaurant_service.create_shell(
                owner=user,
                name=restaurant_name.strip(),
            )
            seed_restaurant_side(restaurant)

        if session_key:
            self.migrate_guest(user=user, session_key=session_key)

        return self.auth_response(user)

    def login(
        self,
        *,
        phone_number: str,
        password: str,
        session_key: str | None = None,
    ) -> dict:
        phone = normalize_phone(phone_number)
        user = authenticate(username=phone, password=password)
        if user is None:
            # Try direct lookup for clearer soft-delete handling
            try:
                existing = User.objects.get(phone_number=phone)
            except User.DoesNotExist:
                existing = None
            if existing and existing.deleted_at is not None:
                raise AppAPIException(
                    code='ACCOUNT_DELETED',
                    message='Invalid credentials.',
                    status_code=401,
                )
            raise AppAPIException(
                code='INVALID_CREDENTIALS',
                message='Invalid credentials.',
                status_code=401,
            )
        if user.deleted_at is not None or not user.is_active:
            raise AppAPIException(
                code='ACCOUNT_DELETED',
                message='Invalid credentials.',
                status_code=401,
            )

        # Restore last active mode on login
        user.active_mode = user.last_active_mode or AppMode.CUSTOMER
        if user.active_mode == AppMode.RESTAURANT and not user.has_restaurant_profile:
            user.active_mode = AppMode.CUSTOMER
        if user.active_mode == AppMode.CUSTOMER and not user.has_customer_profile:
            if user.has_restaurant_profile:
                user.active_mode = AppMode.RESTAURANT
        user.save(update_fields=['active_mode', 'last_login'])

        if session_key:
            self.migrate_guest(user=user, session_key=session_key)

        return self.auth_response(user)

    def logout(self, *, user: User, refresh_token: str) -> None:
        user.last_active_mode = user.active_mode
        user.save(update_fields=['last_active_mode'])
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception as exc:
            raise AppAPIException(
                code='INVALID_TOKEN',
                message='Invalid or expired refresh token.',
                status_code=400,
            ) from exc

    def soft_delete(self, user: User) -> None:
        user.deleted_at = timezone.now()
        user.is_active = False
        user.save(update_fields=['deleted_at', 'is_active'])

    @transaction.atomic
    def migrate_guest(self, *, user: User, session_key: str) -> dict:
        if not session_key:
            raise AppAPIException(
                code='SESSION_REQUIRED',
                message='session_key is required.',
                status_code=400,
            )
        try:
            guest = GuestSession.objects.get(session_key=session_key)
        except GuestSession.DoesNotExist:
            raise AppAPIException(
                code='SESSION_NOT_FOUND',
                message='Guest session not found.',
                status_code=404,
            )
        if guest.merged_into_user_id:
            return {'merged': True, 'idempotent': True}

        # Pending save / history stored for later engagement app consumption.
        guest.merged_into_user = user
        guest.save(update_fields=['merged_into_user', 'updated_at'])

        # Ensure customer profile exists if there is a pending save intent
        if guest.pending_save and not user.has_customer_profile:
            profile = CustomerProfile.objects.create(user=user)
            seed_customer_side(profile)

        return {'merged': True, 'idempotent': False}

    def update_me(self, *, user: User, display_name=None, avatar=None) -> dict:
        fields = []
        if display_name is not None:
            user.display_name = display_name
            fields.append('display_name')
        if avatar is not None:
            user.avatar = avatar
            fields.append('avatar')
        if fields:
            user.save(update_fields=fields)
        return self.me(user)
