from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAuthenticatedAndActive
from apps.promotions.serializers import (
    PromotionApproveSerializer,
    PromotionRejectSerializer,
    PromotionRequestCreateSerializer,
)
from apps.promotions.services import PromotionService, serialize_promotion_request
from core.exceptions import AppAPIException
from core.permissions import IsRestaurantMode, IsRestaurantOwner


class RestaurantOwnerMixin:
    permission_classes = [IsAuthenticatedAndActive, IsRestaurantOwner, IsRestaurantMode]

    def get_restaurant(self, request):
        restaurant = getattr(request.user, 'restaurant', None)
        if restaurant is None:
            raise AppAPIException(
                code='RESTAURANT_REQUIRED',
                message='Restaurant profile required.',
                status_code=403,
            )
        return restaurant


class PromotionRequestListCreateView(RestaurantOwnerMixin, APIView):
    @extend_schema(responses={200: list})
    def get(self, request):
        restaurant = self.get_restaurant(request)
        items = PromotionService().list_for_restaurant(restaurant=restaurant)
        return Response([serialize_promotion_request(r) for r in items])

    @extend_schema(request=PromotionRequestCreateSerializer, responses={201: dict})
    def post(self, request):
        restaurant = self.get_restaurant(request)
        ser = PromotionRequestCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = PromotionService().create(
            restaurant=restaurant,
            **ser.validated_data,
        )
        return Response(
            serialize_promotion_request(req),
            status=status.HTTP_201_CREATED,
        )


class PromotionRequestDetailView(RestaurantOwnerMixin, APIView):
    def get(self, request, request_id: int):
        restaurant = self.get_restaurant(request)
        req = PromotionService().get_for_restaurant(
            restaurant=restaurant,
            request_id=request_id,
        )
        return Response(serialize_promotion_request(req))


class AdminPromotionRequestListView(APIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdminUser]

    def get(self, request):
        status_filter = request.query_params.get('status') or None
        items = PromotionService().list_admin(status_filter=status_filter)
        return Response([serialize_promotion_request(r) for r in items])


class AdminPromotionApproveView(APIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdminUser]

    def post(self, request, request_id: int):
        ser = PromotionApproveSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        req = PromotionService().approve(
            request_id=request_id,
            admin_user=request.user,
            goes_live_at=ser.validated_data.get('goes_live_at'),
            ends_at=ser.validated_data.get('ends_at'),
        )
        return Response(serialize_promotion_request(req))


class AdminPromotionRejectView(APIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdminUser]

    def post(self, request, request_id: int):
        ser = PromotionRejectSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        req = PromotionService().reject(
            request_id=request_id,
            admin_user=request.user,
            admin_note=ser.validated_data.get('admin_note', ''),
        )
        return Response(serialize_promotion_request(req))
