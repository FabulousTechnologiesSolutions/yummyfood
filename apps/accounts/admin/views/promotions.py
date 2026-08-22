from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.admin.serializers.promotions import (
    AdminPromotionApproveSerializer,
    AdminPromotionRejectSerializer,
)
from apps.accounts.permissions import IsAuthenticatedAndActive
from apps.promotions.serializers import PromotionApproveSerializer, PromotionRejectSerializer
from apps.promotions.services import PromotionService, serialize_promotion_request
from core.pagination import StandardResultsSetPagination
from core.permissions import IsAdminRole


def serialize_admin_promotion(req) -> dict:
    data = serialize_promotion_request(req)
    data['restaurant_name'] = req.restaurant.name if getattr(req, 'restaurant_id', None) else None
    if req.menu_item_id and req.menu_item:
        data['title'] = req.menu_item.name
    elif req.deal_id and req.deal:
        data['title'] = req.deal.label
    else:
        data['title'] = None
    return data


class AdminPromotionRequestListView(GenericAPIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdminRole]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        status_filter = request.query_params.get('status') or None
        qs = PromotionService().list_admin(status_filter=status_filter)
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(
            [serialize_admin_promotion(item) for item in page]
        )


class AdminPromotionApproveView(APIView):
    """New /api/admin/ path — requires starts_at (or goes_live_at) and ends_at."""

    permission_classes = [IsAuthenticatedAndActive, IsAdminRole]

    def post(self, request, request_id: int):
        ser = AdminPromotionApproveSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        req = PromotionService().approve(
            request_id=request_id,
            admin_user=request.user,
            goes_live_at=ser.validated_data.get('goes_live_at'),
            ends_at=ser.validated_data.get('ends_at'),
        )
        return Response(serialize_admin_promotion(req))


class AdminPromotionRejectView(APIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdminRole]

    def post(self, request, request_id: int):
        ser = AdminPromotionRejectSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        req = PromotionService().reject(
            request_id=request_id,
            admin_user=request.user,
            admin_note=ser.validated_data['admin_note'],
        )
        return Response(serialize_admin_promotion(req))


class LegacyAdminPromotionApproveView(APIView):
    """Backward-compatible /api/admin-api/ approve — window optional (falls back to requested_*)."""

    permission_classes = [IsAuthenticatedAndActive, IsAdminRole]

    def post(self, request, request_id: int):
        ser = PromotionApproveSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        req = PromotionService().approve(
            request_id=request_id,
            admin_user=request.user,
            goes_live_at=ser.validated_data.get('goes_live_at'),
            ends_at=ser.validated_data.get('ends_at'),
        )
        return Response(serialize_admin_promotion(req))


class LegacyAdminPromotionRejectView(APIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdminRole]

    def post(self, request, request_id: int):
        ser = PromotionRejectSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        req = PromotionService().reject(
            request_id=request_id,
            admin_user=request.user,
            admin_note=ser.validated_data.get('admin_note', ''),
        )
        return Response(serialize_admin_promotion(req))
