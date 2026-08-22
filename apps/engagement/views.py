from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAuthenticatedAndActive
from apps.engagement.models import ReportTargetType
from apps.engagement.serializers import (
    RatingUpsertSerializer,
    ReportCreateSerializer,
    SaveCreateSerializer,
)
from apps.engagement.services.rating_service import RatingService, serialize_rating
from apps.engagement.services.report_service import ReportService, serialize_report
from apps.engagement.services.saved_service import SavedService
from core.permissions import HasCustomerProfile, IsCustomerMode


_CUSTOMER_PERMS = [IsAuthenticatedAndActive, HasCustomerProfile, IsCustomerMode]


class SavedListCreateView(APIView):
    permission_classes = _CUSTOMER_PERMS

    def get(self, request):
        type_filter = request.query_params.get('type')
        service = SavedService()
        rows = service.list_for_user(user=request.user, type_filter=type_filter)
        results = [service.serialize_saved(row, request=request) for row in rows]
        return Response({'count': len(results), 'results': results})

    def post(self, request):
        ser = SaveCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        service = SavedService()
        saved, created = service.save(
            user=request.user,
            target_type=data['target_type'],
            menu_item_id=data.get('menu_item_id'),
            deal_id=data.get('deal_id'),
        )
        # Reload with relations for serialize
        saved = service.get_for_user(user=request.user, saved_id=saved.id)
        payload = service.serialize_saved(saved, request=request)
        return Response(
            payload,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class SavedDetailView(APIView):
    permission_classes = _CUSTOMER_PERMS

    def get(self, request, saved_id: int):
        service = SavedService()
        saved = service.get_for_user(user=request.user, saved_id=saved_id)
        return Response(service.serialize_saved(saved, request=request))

    def delete(self, request, saved_id: int):
        SavedService().unsave(user=request.user, saved_id=saved_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReportItemView(APIView):
    permission_classes = _CUSTOMER_PERMS

    def post(self, request, item_id: int):
        ser = ReportCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        report = ReportService().create(
            user=request.user,
            target_type=ReportTargetType.ITEM,
            resource_id=item_id,
            reason=ser.validated_data['reason'],
            description=ser.validated_data.get('description', ''),
        )
        return Response(serialize_report(report), status=status.HTTP_201_CREATED)


class ReportDealView(APIView):
    permission_classes = _CUSTOMER_PERMS

    def post(self, request, deal_id: int):
        ser = ReportCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        report = ReportService().create(
            user=request.user,
            target_type=ReportTargetType.DEAL,
            resource_id=deal_id,
            reason=ser.validated_data['reason'],
            description=ser.validated_data.get('description', ''),
        )
        return Response(serialize_report(report), status=status.HTTP_201_CREATED)


class ReportRestaurantView(APIView):
    permission_classes = _CUSTOMER_PERMS

    def post(self, request, restaurant_id: int):
        ser = ReportCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        report = ReportService().create(
            user=request.user,
            target_type=ReportTargetType.RESTAURANT,
            resource_id=restaurant_id,
            reason=ser.validated_data['reason'],
            description=ser.validated_data.get('description', ''),
        )
        return Response(serialize_report(report), status=status.HTTP_201_CREATED)


class RestaurantRatingView(APIView):
    permission_classes = _CUSTOMER_PERMS

    def get(self, request, restaurant_id: int):
        rating = RatingService().get_for_user(user=request.user, restaurant_id=restaurant_id)
        return Response(serialize_rating(rating))

    def post(self, request, restaurant_id: int):
        ser = RatingUpsertSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        rating, created = RatingService().upsert(
            user=request.user,
            restaurant_id=restaurant_id,
            stars=ser.validated_data['stars'],
            description=ser.validated_data.get('description', ''),
        )
        return Response(
            serialize_rating(rating),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ItemRatingView(APIView):
    permission_classes = _CUSTOMER_PERMS

    def get(self, request, item_id: int):
        rating = RatingService().get_item_for_user(user=request.user, item_id=item_id)
        return Response(serialize_rating(rating))

    def post(self, request, item_id: int):
        ser = RatingUpsertSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        rating, created = RatingService().upsert_item(
            user=request.user,
            item_id=item_id,
            stars=ser.validated_data['stars'],
            description=ser.validated_data.get('description', ''),
        )
        return Response(
            serialize_rating(rating),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class DealRatingView(APIView):
    permission_classes = _CUSTOMER_PERMS

    def get(self, request, deal_id: int):
        rating = RatingService().get_deal_for_user(user=request.user, deal_id=deal_id)
        return Response(serialize_rating(rating))

    def post(self, request, deal_id: int):
        ser = RatingUpsertSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        rating, created = RatingService().upsert_deal(
            user=request.user,
            deal_id=deal_id,
            stars=ser.validated_data['stars'],
            description=ser.validated_data.get('description', ''),
        )
        return Response(
            serialize_rating(rating),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
