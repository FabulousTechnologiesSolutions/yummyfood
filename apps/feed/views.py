from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.feed.serializers import FeedSeenBatchSerializer
from apps.feed.services.feed_service import FeedService
from apps.feed.services.seen_service import record_seen_batch
from apps.feed.services.viewer import resolve_viewer
from core.exceptions import AppAPIException


class FeedProductsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: dict})
    def get(self, request):
        try:
            page = int(request.query_params.get('page', 1))
        except (TypeError, ValueError):
            raise AppAPIException(
                code='INVALID_PAGE',
                message='Invalid page.',
                status_code=400,
            )
        default_size = getattr(settings, 'EXPLORE_DEFAULT_PAGE_SIZE', 20)
        raw_size = request.query_params.get('page_size', default_size)
        try:
            page_size = int(raw_size)
        except (TypeError, ValueError):
            raise AppAPIException(
                code='INVALID_PAGE_SIZE',
                message='Invalid page_size.',
                status_code=400,
            )
        data = FeedService().get_feed(request, page=page, page_size=page_size)
        return Response(data)


class FeedSeenBatchView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=FeedSeenBatchSerializer, responses={200: dict})
    def post(self, request):
        ser = FeedSeenBatchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        viewer = resolve_viewer(request)
        user = request.user if getattr(request.user, 'is_authenticated', False) else None
        data = record_seen_batch(
            viewer=viewer,
            items=ser.validated_data['items'],
            user=user,
        )
        return Response(data)
