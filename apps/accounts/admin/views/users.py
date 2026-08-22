from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.admin.pagination import paginated_admin_response
from apps.accounts.admin.services.user_admin_service import UserAdminService
from apps.accounts.permissions import IsAuthenticatedAndActive
from core.permissions import IsAdminRole


class AdminUserListView(APIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdminRole]

    def get(self, request):
        role_filter = request.query_params.get('role') or None
        q = request.query_params.get('q') or None
        service = UserAdminService()
        qs = service.list(role_filter=role_filter, q=q)
        return paginated_admin_response(request, qs, service.serialize)


class AdminUserDetailView(APIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdminRole]

    def get(self, request, user_id: int):
        return Response(UserAdminService().get(user_id=user_id))
