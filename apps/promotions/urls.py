from django.urls import path

from apps.accounts.admin.views.promotions import (
    AdminPromotionRequestListView,
    LegacyAdminPromotionApproveView,
    LegacyAdminPromotionRejectView,
)
from apps.promotions.views import (
    PromotionRequestDetailView,
    PromotionRequestListCreateView,
)

urlpatterns = [
    path(
        'restaurant/promotion-requests/',
        PromotionRequestListCreateView.as_view(),
        name='restaurant-promotion-requests',
    ),
    path(
        'restaurant/promotion-requests/<int:request_id>/',
        PromotionRequestDetailView.as_view(),
        name='restaurant-promotion-request-detail',
    ),
    path(
        'admin-api/promotion-requests/',
        AdminPromotionRequestListView.as_view(),
        name='admin-promotion-requests',
    ),
    path(
        'admin-api/promotion-requests/<int:request_id>/approve/',
        LegacyAdminPromotionApproveView.as_view(),
        name='admin-promotion-approve',
    ),
    path(
        'admin-api/promotion-requests/<int:request_id>/reject/',
        LegacyAdminPromotionRejectView.as_view(),
        name='admin-promotion-reject',
    ),
]
