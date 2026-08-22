from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef, Q

from apps.accounts.models import CustomerProfile
from apps.restaurants.models import Restaurant
from core.exceptions import AppAPIException

User = get_user_model()


def derive_user_role(user) -> str:
    if user.is_staff or user.is_superuser:
        return 'staff'
    if hasattr(user, 'has_restaurant'):
        if user.has_restaurant:
            return 'owner'
        return 'customer'
    if user.has_restaurant_profile:
        return 'owner'
    if user.has_customer_profile:
        return 'customer'
    return 'customer'


class UserAdminService:
    VALID_ROLES = {'customer', 'owner', 'staff'}

    def _base_qs(self):
        return (
            User.objects.filter(deleted_at__isnull=True)
            .annotate(
                has_restaurant=Exists(Restaurant.objects.filter(owner_id=OuterRef('pk'))),
                has_customer=Exists(CustomerProfile.objects.filter(user_id=OuterRef('pk'))),
            )
            .order_by('-date_joined')
        )

    def list(self, *, role_filter: str | None = None, q: str | None = None):
        if role_filter and role_filter not in self.VALID_ROLES:
            raise AppAPIException(
                code='INVALID_USER_ROLE',
                message='role must be customer, owner, or staff.',
                status_code=400,
            )
        qs = self._base_qs()
        if q:
            qs = qs.filter(Q(phone_number__icontains=q) | Q(display_name__icontains=q))
        if role_filter == 'staff':
            qs = qs.filter(Q(is_staff=True) | Q(is_superuser=True))
        elif role_filter == 'owner':
            qs = qs.filter(has_restaurant=True).exclude(Q(is_staff=True) | Q(is_superuser=True))
        elif role_filter == 'customer':
            qs = qs.filter(has_customer=True).exclude(
                Q(is_staff=True) | Q(is_superuser=True) | Q(has_restaurant=True)
            )
        return qs

    def get(self, *, user_id: int) -> dict:
        try:
            user = self._base_qs().get(pk=user_id)
        except User.DoesNotExist:
            raise AppAPIException(
                code='USER_NOT_FOUND',
                message='User not found.',
                status_code=404,
            )
        return self.serialize(user)

    def serialize(self, user) -> dict:
        last_active = user.last_login or user.date_joined
        return {
            'id': user.id,
            'display_name': user.display_name or None,
            'phone_number': user.phone_number,
            'role': derive_user_role(user),
            'last_active_at': last_active.isoformat() if last_active else None,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'active_mode': user.active_mode,
            'date_joined': user.date_joined.isoformat() if user.date_joined else None,
        }
