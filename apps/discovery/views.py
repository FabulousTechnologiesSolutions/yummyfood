from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.discovery.services.explore_feed import ExploreFeedService
from core.exceptions import AppAPIException


class ExploreProductsView(APIView):
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
        data = ExploreFeedService().get_feed(
            request,
            page=page,
            page_size=page_size,
        )
        return Response(data)
