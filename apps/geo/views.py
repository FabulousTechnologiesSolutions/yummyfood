from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.geo.models import City
from apps.geo.serializers import CityPickerItemSerializer, CitySerializer
from core.permissions import IsAdminRole


class CityViewSet(viewsets.ModelViewSet):
    """
    Public list/retrieve/picker/search for active cities.
    Admin role (is_staff or is_superuser) required for create/update/destroy.
    """

    serializer_class = CitySerializer
    queryset = City.objects.all().order_by('id')

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminRole()]
        return [AllowAny()]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action in ('list', 'retrieve', 'picker', 'search'):
            return qs.filter(is_active=True)
        return qs

    @action(detail=False, methods=['get'], url_path='picker')
    def picker(self, request):
        qs = (
            City.objects.filter(is_active=True)
            .annotate(
                restaurant_count=Count(
                    'restaurants',
                    filter=Q(
                        restaurants__is_paused=False,
                        restaurants__is_permanently_closed=False,
                    ),
                )
            )
            .order_by('id')
        )
        data = CityPickerItemSerializer(qs, many=True).data
        return Response({'popular': data})

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        q = (request.query_params.get('q') or '').strip()
        qs = City.objects.filter(is_active=True).order_by('id')
        if q:
            qs = qs.filter(name__icontains=q)
        return Response(CitySerializer(qs, many=True).data)
