from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.admin.pagination import paginated_admin_response
from apps.accounts.admin.services.restaurant_admin_service import RestaurantAdminService
from apps.accounts.permissions import IsAuthenticatedAndActive
from core.permissions import IsAdminRole


class AdminRestaurantListView(APIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdminRole]

    def get(self, request):
        status_filter = request.query_params.get('status') or None
        q = request.query_params.get('q') or None
        service = RestaurantAdminService()
        qs = service.list(status_filter=status_filter, q=q)
        return paginated_admin_response(
            request,
            qs,
            lambda restaurant: service.serialize(restaurant, request=request),
        )


class AdminRestaurantDetailView(APIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdminRole]

    def get(self, request, restaurant_id: int):
        return Response(
            RestaurantAdminService().get(restaurant_id=restaurant_id, request=request)
        )
