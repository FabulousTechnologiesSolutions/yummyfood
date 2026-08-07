from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.serializers import AnalyticsEventSerializer
from apps.analytics.services.event_service import EventService


class AnalyticsEventView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=AnalyticsEventSerializer, responses={200: dict})
    def post(self, request):
        ser = AnalyticsEventSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = request.user if request.user.is_authenticated else None
        result = EventService().record(
            event_model=ser.validated_data['event_model'],
            resource_id=ser.validated_data['resource_id'],
            event_type=ser.validated_data['event_type'],
            user=user,
            allow_impression=False,
        )
        return Response(result)
