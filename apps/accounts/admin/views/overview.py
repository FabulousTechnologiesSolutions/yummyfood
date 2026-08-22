from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.admin.services.overview_service import OverviewService
from apps.accounts.permissions import IsAuthenticatedAndActive
from core.permissions import IsAdminRole


class AdminOverviewView(APIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdminRole]

    def get(self, request):
        return Response(OverviewService().get())
