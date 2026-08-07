from rest_framework.permissions import BasePermission

from core.exceptions import AppAPIException


class HasCustomerProfile(BasePermission):
    """User must have a CustomerProfile."""

    message = 'Customer profile required.'

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, 'has_customer_profile', False)
        )


class IsRestaurantOwner(BasePermission):
    """User must own a restaurant profile."""

    message = 'Restaurant profile required.'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if not getattr(user, 'has_restaurant_profile', False):
            raise AppAPIException(
                code='RESTAURANT_REQUIRED',
                message='Restaurant profile required.',
                status_code=403,
            )
        return True


class IsCustomerMode(BasePermission):
    message = 'Customer mode required.'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if getattr(user, 'active_mode', None) != 'customer':
            raise AppAPIException(
                code='CUSTOMER_MODE_REQUIRED',
                message='Switch to customer mode to access this resource.',
                status_code=403,
            )
        return True


class IsRestaurantMode(BasePermission):
    message = 'Restaurant mode required.'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if getattr(user, 'active_mode', None) != 'restaurant':
            raise AppAPIException(
                code='RESTAURANT_MODE_REQUIRED',
                message='Switch to restaurant mode to access this resource.',
                status_code=403,
            )
        return True
