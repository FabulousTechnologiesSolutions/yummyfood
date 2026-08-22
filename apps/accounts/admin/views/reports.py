from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.admin.pagination import paginated_admin_response
from apps.accounts.admin.serializers.reports import ReportAdminNoteSerializer
from apps.accounts.permissions import IsAuthenticatedAndActive
from apps.engagement.services.report_service import ReportService
from core.permissions import IsAdminRole


class AdminReportListView(APIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdminRole]

    def get(self, request):
        status_filter = request.query_params.get('status') or None
        target_type = request.query_params.get('target_type') or None
        restaurant_id = request.query_params.get('restaurant_id') or None
        service = ReportService()
        qs = service.list_admin(
            status_filter=status_filter,
            target_type=target_type,
            restaurant_id=restaurant_id,
        )
        return paginated_admin_response(request, qs, service.serialize_admin)


class AdminReportDetailView(APIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdminRole]

    def get(self, request, report_id: int):
        service = ReportService()
        report = service.get_admin(report_id=report_id)
        return Response(service.serialize_admin(report))


class AdminReportActionView(APIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdminRole]

    def post(self, request, report_id: int):
        ser = ReportAdminNoteSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        service = ReportService()
        report = service.action(
            report_id=report_id,
            admin_user=request.user,
            admin_note=ser.validated_data.get('admin_note', ''),
        )
        return Response(service.serialize_admin(report))


class AdminReportDismissView(APIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdminRole]

    def post(self, request, report_id: int):
        ser = ReportAdminNoteSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        service = ReportService()
        report = service.dismiss(
            report_id=report_id,
            admin_user=request.user,
            admin_note=ser.validated_data.get('admin_note', ''),
        )
        return Response(service.serialize_admin(report))
