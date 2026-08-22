from django.db.models import Count
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.admin.pagination import paginated_admin_response
from apps.accounts.admin.serializers.categories import AdminCategoryCreateSerializer
from apps.accounts.permissions import IsAuthenticatedAndActive
from apps.restaurants.models import MenuCategory
from apps.restaurants.serializers import CategoryUpdateSerializer
from apps.restaurants.services.category_service import CategoryService, serialize_category
from core.permissions import IsAdminRole


def _serialize_with_used_by(category: MenuCategory) -> dict:
    data = serialize_category(category)
    used_by = getattr(category, 'used_by', None)
    if used_by is None:
        used_by = category.menu_items.values('restaurant_id').distinct().count()
    data['used_by'] = used_by
    return data


class AdminCategoryListCreateView(APIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdminRole]

    def get(self, request):
        qs = MenuCategory.objects.annotate(
            used_by=Count('menu_items__restaurant', distinct=True)
        ).order_by('position', 'name', 'id')
        return paginated_admin_response(request, qs, _serialize_with_used_by)

    def post(self, request):
        ser = AdminCategoryCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        category = CategoryService().create(data=ser.validated_data)
        return Response(_serialize_with_used_by(category), status=status.HTTP_201_CREATED)


class AdminCategoryDetailView(APIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdminRole]

    def patch(self, request, category_id: int):
        ser = CategoryUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        category = CategoryService().update(
            category_id=category_id,
            data=ser.validated_data,
        )
        return Response(_serialize_with_used_by(category))

    def delete(self, request, category_id: int):
        CategoryService().delete(category_id=category_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
