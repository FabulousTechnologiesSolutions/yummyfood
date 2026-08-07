from django.urls import path

from apps.promotions.views import (
    AdminPromotionApproveView,
    AdminPromotionRejectView,
    AdminPromotionRequestListView,
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
        AdminPromotionApproveView.as_view(),
        name='admin-promotion-approve',
    ),
    path(
        'admin-api/promotion-requests/<int:request_id>/reject/',
        AdminPromotionRejectView.as_view(),
        name='admin-promotion-reject',
    ),
]
