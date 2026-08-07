from rest_framework.permissions import BasePermission, IsAuthenticated


class IsAuthenticatedAndActive(IsAuthenticated):
    def has_permission(self, request, view):
        ok = super().has_permission(request, view)
        if not ok:
            return False
        user = request.user
        return getattr(user, 'deleted_at', None) is None and user.is_active
